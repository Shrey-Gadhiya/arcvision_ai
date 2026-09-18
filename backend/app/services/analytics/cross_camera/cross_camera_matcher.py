import time
import logging
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from app.models.cross_camera import IdentitySource, GlobalEntityType
from app.services.analytics.cross_camera.topology_manager import topology_manager
from app.services.analytics.cross_camera.base import compute_cosine_similarity

logger = logging.getLogger("arc_vision.cross_camera.matcher")

class MatchCandidateResult:
    def __init__(
        self,
        global_track_id: int,
        global_id: str,
        score: float,
        source: IdentitySource,
        explanation: str
    ):
        self.global_track_id = global_track_id
        self.global_id = global_id
        self.score = float(score)
        self.source = source
        self.explanation = explanation

    @property
    def confidence(self) -> float:
        return self.score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "global_track_id": self.global_track_id,
            "global_id": self.global_id,
            "score": round(self.score, 3),
            "source": self.source.value,
            "explanation": self.explanation
        }

class CrossCameraMatcher:
    """
    Multi-Factor Cross-Camera Identity Correlation Engine.
    Correlates local detections into global tracks with strict conflict resolution.
    """
    def __init__(self, min_transition_score: float = 0.70):
        self.min_transition_score = min_transition_score

    def find_best_match(
        self,
        active_global_tracks: List[Any],
        entity_type: GlobalEntityType,
        camera_id: int,
        observation_time: float,
        plate_number: Optional[str] = None,
        face_identity_id: Optional[int] = None,
        face_name: Optional[str] = None,
        embedding: Optional[np.ndarray] = None
    ) -> Optional[MatchCandidateResult]:
        """
        Evaluates candidate active global tracks and returns the highest-scoring identity match.
        """
        candidates: List[MatchCandidateResult] = []

        for gt in active_global_tracks:
            # 1. Hard Conflict Checks
            if gt.entity_type != entity_type:
                continue

            # License Plate Match or Conflict
            if plate_number and gt.plate_number:
                p1 = plate_number.replace("-", "").replace(" ", "").replace(".", "").upper()
                p2 = gt.plate_number.replace("-", "").replace(" ", "").replace(".", "").upper()
                if p1 == p2:
                    # Exact Plate Match
                    return MatchCandidateResult(
                        global_track_id=gt.id,
                        global_id=gt.global_id,
                        score=1.0,
                        source=IdentitySource.PLATE_MATCH,
                        explanation=f"Exact License Plate Match [{plate_number}] across cameras"
                    )
                else:
                    # Explicit conflicting license plate -> Skip this candidate
                    continue

            # Face Identity Match or Conflict
            if face_identity_id and gt.face_identity_id:
                if face_identity_id == gt.face_identity_id:
                    # Verified Face Identity Match
                    return MatchCandidateResult(
                        global_track_id=gt.id,
                        global_id=gt.global_id,
                        score=0.98,
                        source=IdentitySource.FACE_MATCH,
                        explanation=f"Verified Biometric Face Match [{face_name or gt.face_identity_name}] across cameras"
                    )
                else:
                    # Different identified individual -> Skip
                    continue

            # 2. Spatial-Temporal Transition Feasibility
            last_seen_ts = gt.last_seen.timestamp() if hasattr(gt.last_seen, 'timestamp') else float(gt.last_seen)
            delta_t = observation_time - last_seen_ts
            if delta_t < 0:
                continue

            last_cam = gt.current_camera_id or camera_id
            is_plausible, trans_conf, link = topology_manager.validate_transition(
                from_cam=last_cam,
                to_cam=camera_id,
                delta_seconds=delta_t
            )

            if not is_plausible:
                continue

            # 3. Visual Appearance ReID (if embeddings available)
            reid_score = 0.0
            if embedding is not None and getattr(gt, 'embedding', None) is not None:
                reid_score = compute_cosine_similarity(embedding, gt.embedding)

            # Composite Score Calculation
            if reid_score > 0.65 and is_plausible:
                composite_score = 0.60 * reid_score + 0.40 * trans_conf
                candidates.append(
                    MatchCandidateResult(
                        global_track_id=gt.id,
                        global_id=gt.global_id,
                        score=composite_score,
                        source=IdentitySource.REID_EMBEDDING,
                        explanation=f"Visual ReID (Cosine {reid_score:.2f}) + Topology Transition ({delta_t:.1f}s, Conf {trans_conf:.2f})"
                    )
                )
            elif is_plausible and trans_conf >= self.min_transition_score and delta_t <= 90.0:
                candidates.append(
                    MatchCandidateResult(
                        global_track_id=gt.id,
                        global_id=gt.global_id,
                        score=trans_conf,
                        source=IdentitySource.TOPOLOGY_TRANSITION,
                        explanation=f"Plausible camera transition Cam #{last_cam} -> Cam #{camera_id} in {delta_t:.1f}s ({link.get('sector', 'Perimeter') if link else 'Adjacent Area'})"
                    )
                )

        if not candidates:
            return None

        # Pick candidate with highest match score
        best_candidate = max(candidates, key=lambda c: c.score)
        if best_candidate.score >= self.min_transition_score:
            return best_candidate

        return None

cross_camera_matcher = CrossCameraMatcher()
