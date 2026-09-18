import os
import json
import pytest
import numpy as np
from datetime import datetime, timezone

from app.models.face import (
    FaceIdentity,
    FaceRecord,
    FaceWatchlistCategory,
    FaceWatchlistPriority,
    FaceMatchStatus
)
from app.services.ai.face.base import (
    BaseFaceDetectorAdapter,
    BaseFaceEmbeddingAdapter,
    AdapterStatus,
    FaceDetectionResult,
    FaceEmbeddingResult,
    FaceQualityResult,
    FaceMatchResult
)
from app.services.ai.face.quality import FaceQualityChecker
from app.services.ai.face.adapters import (
    UnavailableFaceDetectorAdapter,
    UnavailableFaceEmbeddingAdapter,
    YuNetFaceDetectorAdapter,
    SFaceEmbeddingAdapter
)
from app.services.ai.face.service import FaceRecognitionService

class MockDetectorAdapter(BaseFaceDetectorAdapter):
    def __init__(self):
        super().__init__(name="MockDetector", device="cpu")
        self.status = AdapterStatus.LOADED

    def load(self) -> bool:
        self.status = AdapterStatus.LOADED
        return True

    def unload(self) -> bool:
        self.status = AdapterStatus.UNLOADED
        return True

    def detect_faces(self, image: np.ndarray, confidence_threshold: float = 0.50):
        # Return a single mock face crop with bounding box
        h, w = image.shape[:2]
        crop = image[10:90, 10:90].copy()
        return [
            FaceDetectionResult(
                box=[0.1, 0.1, 0.9, 0.9],
                confidence=0.95,
                face_crop=crop,
                quality_score=0.88,
                sharpness_score=120.0
            )
        ]

class MockEmbeddingAdapter(BaseFaceEmbeddingAdapter):
    def __init__(self, fixed_vector=None):
        super().__init__(name="MockEmbedding", device="cpu", dimension=128)
        self.status = AdapterStatus.LOADED
        self.fixed_vector = fixed_vector or [1.0] + [0.0] * 127

    def load(self) -> bool:
        self.status = AdapterStatus.LOADED
        return True

    def unload(self) -> bool:
        self.status = AdapterStatus.UNLOADED
        return True

    def compute_embedding(self, face_crop: np.ndarray):
        vec = np.array(self.fixed_vector, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return FaceEmbeddingResult(
            embedding=vec.tolist(),
            dimension=len(vec),
            normalized=True,
            status="SUCCESS"
        )

# 1. Base Detector Contract & Unavailable Handling
def test_unavailable_detector_adapter():
    adapter = UnavailableFaceDetectorAdapter()
    assert adapter.status == AdapterStatus.NOT_CONFIGURED
    assert adapter.detect_faces(np.zeros((100, 100, 3), dtype=np.uint8)) == []
    health = adapter.health_check()
    assert health["status"] == "NOT_CONFIGURED"

def test_unavailable_embedding_adapter():
    adapter = UnavailableFaceEmbeddingAdapter()
    assert adapter.status == AdapterStatus.NOT_CONFIGURED
    res = adapter.compute_embedding(np.zeros((100, 100, 3), dtype=np.uint8))
    assert res.embedding is None
    assert res.status == "NOT_CONFIGURED"

# 2. Quality Gate & Laplacian Sharpness
def test_quality_checker_sharpness():
    checker = FaceQualityChecker()
    # Uniform blank image has 0 Laplacian variance
    blank = np.full((100, 100, 3), 128, dtype=np.uint8)
    sharpness_blank = checker.compute_sharpness(blank)
    assert sharpness_blank == 0.0

    # High texture image has positive Laplacian variance
    textured = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    sharpness_text = checker.compute_sharpness(textured)
    assert sharpness_text > 0.0

def test_quality_gate_enrollment_validation():
    checker = FaceQualityChecker(enroll_min_width=40, enroll_min_height=40, enroll_min_sharpness=10.0)
    img = np.random.randint(50, 200, (200, 200, 3), dtype=np.uint8)

    # 0 faces rejected
    res0 = checker.validate_for_enrollment(img, [])
    assert not res0.passed
    assert res0.rejected_reason == "NO_FACE_DETECTED"

    # Multiple faces rejected
    det1 = FaceDetectionResult(box=[0,0,1,1], confidence=0.9, face_crop=img[:50,:50])
    det2 = FaceDetectionResult(box=[0,0,1,1], confidence=0.8, face_crop=img[50:100,50:100])
    res_multi = checker.validate_for_enrollment(img, [det1, det2])
    assert not res_multi.passed
    assert res_multi.rejected_reason == "MULTIPLE_FACES_DETECTED"

# 3. Cosine Similarity & Gallery Matching
def test_cosine_similarity_calculation():
    service = FaceRecognitionService()
    # Identical vectors
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert pytest.approx(service.compute_cosine_similarity(v1, v2), 0.001) == 1.0

    # Orthogonal vectors
    v3 = [0.0, 1.0, 0.0]
    assert pytest.approx(service.compute_cosine_similarity(v1, v3), 0.001) == 0.0

def test_gallery_matching_status_distinction():
    service = FaceRecognitionService()
    # Inject Mock Embedding Adapter
    service.embedding_adapter = MockEmbeddingAdapter()
    service.recognition_threshold = 0.60
    service.uncertain_threshold = 0.40

    # Populate gallery
    target_vec = [1.0] + [0.0] * 127
    service._gallery_cache = {
        101: {
            "name": "Target Subject",
            "category": "WATCH",
            "priority": "HIGH",
            "embeddings": [target_vec],
            "is_active": True
        }
    }

    # 1. KNOWN MATCH (Identical vector -> similarity 1.0)
    match_known = service.match_embedding_against_gallery(target_vec)
    assert match_known.status == "KNOWN"
    assert match_known.identity_id == 101
    assert match_known.identity_name == "Target Subject"
    assert match_known.is_matched == True
    assert match_known.watchlist_category == "WATCH"

    # 2. UNCERTAIN MATCH (Similarity around 0.50)
    # create vector with dot product 0.50 with target_vec
    uncert_vec = [0.5] + [np.sqrt(0.75)] + [0.0] * 126
    match_uncert = service.match_embedding_against_gallery(uncert_vec)
    assert match_uncert.status == "UNCERTAIN"
    assert match_uncert.identity_id == 101
    assert match_uncert.is_matched == False

    # 3. UNKNOWN MATCH (Orthogonal vector -> similarity 0.0)
    unknown_vec = [0.0, 1.0] + [0.0] * 126
    match_unk = service.match_embedding_against_gallery(unknown_vec)
    assert match_unk.status == "UNKNOWN"
    assert match_unk.identity_id is None
    assert match_unk.is_matched == False

    # 4. UNAVAILABLE (when embedding engine is unavailable)
    service.embedding_adapter = UnavailableFaceEmbeddingAdapter()
    match_unavail = service.match_embedding_against_gallery(target_vec)
    assert match_unavail.status == "UNAVAILABLE"
    assert match_unavail.is_matched == False

# 4. Person Track Association
def test_person_track_association():
    service = FaceRecognitionService()
    face_box = [0.2, 0.15, 0.3, 0.25] # Center is at (0.25, 0.20)

    person_tracks = [
        {"track_id": 42, "box": [0.15, 0.10, 0.40, 0.70]}, # Face is inside upper portion of this person
        {"track_id": 99, "box": [0.60, 0.60, 0.80, 0.95]}  # Different location
    ]

    associated_id = service._associate_face_with_person_tracks(face_box, person_tracks)
    assert associated_id == 42

    # Face outside all tracks
    outside_box = [0.85, 0.05, 0.95, 0.15]
    assert service._associate_face_with_person_tracks(outside_box, person_tracks) is None
