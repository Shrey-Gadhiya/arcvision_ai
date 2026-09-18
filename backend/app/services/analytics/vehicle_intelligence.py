import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anpr import ANPRRecord, ANPRWatchlist, PlateValidationStatus
from app.models.event import DetectionEvent
from app.core.event_bus import event_bus

logger = logging.getLogger("arc_vision.analytics.vehicle_intelligence")

class VehicleIntelligenceService:
    """
    Model-independent vehicle intelligence and trajectory analytics.
    Features:
    - Stationary vehicle detection & dwell time monitoring
    - Wrong-way movement analysis
    - Multi-camera repeated sighting frequency
    - Vehicle distribution analytics
    """
    def __init__(self):
        # Active track velocities: (camera_id, track_id) -> list of recent centroids
        self._track_history: Dict[Tuple[int, int], List[Tuple[float, float, float]]] = {}
        self.stationary_threshold_sec: float = 30.0

    def evaluate_motion_dynamics(
        self,
        camera_id: int,
        track_id: int,
        centroid: Tuple[float, float],
        dwell_sec: float,
        timestamp: float
    ) -> Dict[str, Any]:
        """
        Calculates speed vector, detects stationary state, and tracks dwell.
        """
        key = (camera_id, track_id)
        if key not in self._track_history:
            self._track_history[key] = []

        history = self._track_history[key]
        history.append((centroid[0], centroid[1], timestamp))

        # Keep last 15 seconds of points
        if len(history) > 30:
            history.pop(0)

        is_stationary = False
        speed = 0.0

        if len(history) >= 5:
            dx = history[-1][0] - history[0][0]
            dy = history[-1][1] - history[0][1]
            dt = history[-1][2] - history[0][2]
            if dt > 0.5:
                speed = ((dx ** 2 + dy ** 2) ** 0.5) / dt
                if speed < 0.015 and dwell_sec >= self.stationary_threshold_sec:
                    is_stationary = True

        return {
            "speed": round(speed, 4),
            "dwell_sec": round(dwell_sec, 1),
            "is_stationary": is_stationary
        }

    async def get_vehicle_analytics(self, db: AsyncSession, hours: int = 24) -> Dict[str, Any]:
        """
        Aggregates vehicle intelligence statistics over the specified time window.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        # 1. Total sightings & Watchlist hits
        tot_query = select(func.count(ANPRRecord.id)).where(ANPRRecord.timestamp >= cutoff)
        total_sightings = (await db.execute(tot_query)).scalar() or 0

        hit_query = select(func.count(ANPRRecord.id)).where(
            ANPRRecord.timestamp >= cutoff,
            ANPRRecord.is_matched == True
        )
        watchlist_hits = (await db.execute(hit_query)).scalar() or 0

        # 2. Unique Plates Count
        uniq_query = select(func.count(func.distinct(ANPRRecord.plate_number))).where(ANPRRecord.timestamp >= cutoff)
        unique_plates = (await db.execute(uniq_query)).scalar() or 0

        # 3. Stationary Vehicles Count
        stat_query = select(func.count(ANPRRecord.id)).where(
            ANPRRecord.timestamp >= cutoff,
            ANPRRecord.is_stationary == True
        )
        stationary_count = (await db.execute(stat_query)).scalar() or 0

        # 4. Vehicle Class Distribution
        class_query = select(
            ANPRRecord.vehicle_type,
            func.count(ANPRRecord.id)
        ).where(ANPRRecord.timestamp >= cutoff).group_by(ANPRRecord.vehicle_type)
        class_res = (await db.execute(class_query)).all()
        class_dist = {row[0]: row[1] for row in class_res}

        # 5. Top Repeated Sightings
        top_query = select(
            ANPRRecord.plate_number,
            func.count(ANPRRecord.id).label("count"),
            func.max(ANPRRecord.timestamp).label("last_seen"),
            func.max(ANPRRecord.vehicle_type).label("vehicle_type"),
            func.max(ANPRRecord.is_matched).label("is_matched")
        ).where(ANPRRecord.timestamp >= cutoff).group_by(ANPRRecord.plate_number).order_by(desc("count")).limit(10)
        top_res = (await db.execute(top_query)).all()
        top_plates = [
            {
                "plate_number": r.plate_number,
                "sightings_count": r.count,
                "last_seen": r.last_seen.isoformat() if r.last_seen else None,
                "vehicle_type": r.vehicle_type,
                "is_matched": bool(r.is_matched)
            }
            for r in top_res
        ]

        # 6. Recent Flagged Vehicles
        flagged_query = select(ANPRRecord).where(
            ANPRRecord.timestamp >= cutoff,
            ANPRRecord.is_matched == True
        ).order_by(desc(ANPRRecord.timestamp)).limit(10)
        recent_flagged = (await db.execute(flagged_query)).scalars().all()

        return {
            "total_sightings": total_sightings,
            "unique_plates": unique_plates,
            "watchlist_hits": watchlist_hits,
            "stationary_vehicles_count": stationary_count,
            "vehicle_class_distribution": class_dist,
            "top_seen_plates": top_plates,
            "recent_flagged_vehicles": recent_flagged
        }

vehicle_intelligence = VehicleIntelligenceService()
