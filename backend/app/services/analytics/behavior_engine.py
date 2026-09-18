import math
import time
from typing import List, Dict, Any, Tuple
from app.services.ai.base import Detection
from app.services.analytics.behavior import behavior_engine, BehaviorAnalyticsEngine

# Backwards compatibility wrappers
evaluate_loitering = BehaviorAnalyticsEngine
evaluate_perimeter_pacing = BehaviorAnalyticsEngine
evaluate_stationary_vehicle = BehaviorAnalyticsEngine
evaluate_crowd_clustering = BehaviorAnalyticsEngine

__all__ = ["behavior_engine", "BehaviorAnalyticsEngine"]
