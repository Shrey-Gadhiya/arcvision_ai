from app.services.ai.anpr.base import (
    BasePlateDetectorAdapter,
    BasePlateOCRAdapter,
    PlateDetectionResult,
    OCRResult,
    ValidationOutcome,
    AdapterStatus
)
from app.services.ai.anpr.normalizer import normalize_indian_plate, clean_raw_plate
from app.services.ai.anpr.validators import IndianPlateValidator
from app.services.ai.anpr.adapters import (
    HeuristicPlateDetectorAdapter,
    EasyOCRPlateAdapter,
    UnavailablePlateDetectorAdapter,
    UnavailableOCRAdapter
)

__all__ = [
    "BasePlateDetectorAdapter",
    "BasePlateOCRAdapter",
    "PlateDetectionResult",
    "OCRResult",
    "ValidationOutcome",
    "AdapterStatus",
    "normalize_indian_plate",
    "clean_raw_plate",
    "IndianPlateValidator",
    "HeuristicPlateDetectorAdapter",
    "EasyOCRPlateAdapter",
    "UnavailablePlateDetectorAdapter",
    "UnavailableOCRAdapter"
]
