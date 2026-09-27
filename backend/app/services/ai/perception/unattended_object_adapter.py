import time
import math
import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger("arc_vision.perception.unattended_object")

class UnattendedObjectDetector:
    """
    Forensic Unattended & Abandoned Object Intelligence.
    Detects dropped luggage, unattended backpacks, suspicious boxes, and tactical packages
    isolated from any owner for longer than the safety threshold.
    """
    ITEM_CLASSES = {"backpack", "suitcase", "handbag", "package", "box", "bag"}

    def __init__(self, alert_dwell_sec: float = 10.0, owner_proximity_dist: float = 0.20):
        self.alert_dwell_sec = alert_dwell_sec
        self.owner_proximity_dist = owner_proximity_dist

    def evaluate_unattended_objects(
        self,
        camera_id: int,
        tracked_objects: List[Any]
    ) -> List[Dict[str, Any]]:
        events = []
        persons = [o for o in tracked_objects if getattr(o, "class_name", "") == "person"]
        items = [o for o in tracked_objects if getattr(o, "class_name", "").lower() in self.ITEM_CLASSES]

        for item in items:
            track_id = getattr(item, "track_id", -1)
            dwell = item.attributes.get("dwell_sec", 0.0)
            is_stationary = item.attributes.get("is_stationary", True)
            item_box = getattr(item, "box", [0, 0, 0, 0])
            item_cx = (item_box[0] + item_box[2]) / 2.0
            item_cy = (item_box[1] + item_box[3]) / 2.0

            # Check if any person is in proximity
            has_nearby_owner = False
            for p in persons:
                p_box = getattr(p, "box", [0, 0, 0, 0])
                p_cx = (p_box[0] + p_box[2]) / 2.0
                p_cy = (p_box[1] + p_box[3]) / 2.0
                dist = math.hypot(p_cx - item_cx, p_cy - item_cy)
                if dist <= self.owner_proximity_dist:
                    has_nearby_owner = True
                    break

            if not has_nearby_owner and dwell >= self.alert_dwell_sec:
                events.append({
                    "event_type": "SUSPICIOUS_UNATTENDED_PACKAGE",
                    "severity": "CRITICAL",
                    "track_id": track_id,
                    "camera_id": camera_id,
                    "class_name": item.class_name.upper(),
                    "box": item_box,
                    "confidence": 0.92,
                    "dwell_sec": dwell,
                    "explanation": f"Suspicious unattended {item.class_name} abandoned without owner for {dwell:.1f}s"
                })
                item.attributes["is_unattended"] = True
                item.attributes["unattended_dwell_sec"] = dwell

        return events

unattended_object_detector = UnattendedObjectDetector()
