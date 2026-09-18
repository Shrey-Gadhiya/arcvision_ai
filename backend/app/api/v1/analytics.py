from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.schemas.all_schemas import AnalyticsStatusResponse
from app.services.analytics.behavior import behavior_engine
from app.services.ai.base import Detection
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["Behavior Analytics"])

class DryRunRequest(BaseModel):
    camera_id: int = 1
    class_name: str = "person"
    confidence: float = 0.90
    dwell_sec: float = 18.0
    is_stationary: bool = False
    pacing_count: int = 0
    speed: float = 0.10
    active_zones: List[Dict[str, Any]] = []
    tripwire_breaches: List[Dict[str, Any]] = []
    is_night_mode: bool = False

@router.get("/status", response_model=AnalyticsStatusResponse)
async def get_analytics_status(
    current_user = Depends(get_current_user)
):
    """
    Returns live health telemetry for all 11 behavior analyzers,
    total evaluations, and ML action model readiness.
    """
    return behavior_engine.get_status()

@router.post("/dry-run")
async def dry_run_behavior_evaluation(
    data: DryRunRequest,
    current_user = Depends(get_current_user)
):
    """
    Dry-run simulation endpoint to test behavior analysis output against simulated kinematics.
    """
    det = Detection(
        class_name=data.class_name,
        confidence=data.confidence,
        box=[0.2, 0.2, 0.4, 0.6],
        track_id=1,
        attributes={
            "dwell_sec": data.dwell_sec,
            "is_stationary": data.is_stationary,
            "pacing_count": data.pacing_count,
            "velocity": (data.speed, 0.0),
            "trajectory": [(0.2, 0.2, 0.0), (0.25, 0.25, 1.0)]
        }
    )

    events = behavior_engine.evaluate_all(
        camera_id=data.camera_id,
        detections=[det],
        active_zones_by_track={1: data.active_zones},
        tripwire_breaches_by_track={1: data.tripwire_breaches},
        context={"is_night_mode": data.is_night_mode}
    )

    return {
        "status": "SUCCESS",
        "evaluated_track_id": 1,
        "events_count": len(events),
        "events": [e.to_dict() for e in events]
    }
