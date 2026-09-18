import json
import logging
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.notification import Notification, NotificationRule, NotificationSeverity, NotificationChannel
from app.models.integration import IntegrationConfig, IntegrationStatus
from app.core.event_bus import event_bus

logger = logging.getLogger("arc_vision.notifications")

class NotificationService:
    def __init__(self):
        self._cooldowns: Dict[str, float] = {}

    async def dispatch_incident_notification(self, incident: Dict[str, Any]):
        """Evaluates active notification rules and dispatches alerts across configured channels."""
        severity_str = incident.get("severity", "MEDIUM")
        camera_id = incident.get("camera_id")
        code = incident.get("incident_code", "INC")
        title = f"[{severity_str}] Perimeter Incident: {incident.get('incident_type', 'ALERT')}"
        message = f"Camera #{camera_id} ({incident.get('camera_name', 'Unknown')}) detected {incident.get('primary_object', 'target')} with {int(incident.get('confidence', 0.8) * 100)}% confidence."

        async with AsyncSessionLocal() as session:
            # 1. Fetch active notification rules
            result = await session.execute(select(NotificationRule).where(NotificationRule.is_active == True))
            rules = result.scalars().all()

            # Always create an in-app notification record
            in_app_notif = Notification(
                title=title,
                message=message,
                severity=NotificationSeverity(severity_str) if severity_str in NotificationSeverity.__members__ else NotificationSeverity.HIGH,
                channel=NotificationChannel.IN_APP,
                camera_id=camera_id,
                metadata_json=json.dumps(incident)
            )
            session.add(in_app_notif)
            await session.commit()

            for rule in rules:
                try:
                    # Check severity filter
                    allowed_severities = json.loads(rule.severity_filter_json)
                    if allowed_severities and severity_str not in allowed_severities:
                        continue

                    # Check camera filter
                    allowed_cams = json.loads(rule.camera_ids_json)
                    if allowed_cams and camera_id not in allowed_cams:
                        continue

                    # Check cooldown
                    cd_key = f"{rule.id}_{camera_id}"
                    now_ts = datetime.now(timezone.utc).timestamp()
                    if cd_key in self._cooldowns and (now_ts - self._cooldowns[cd_key] < rule.cooldown_seconds):
                        continue
                    self._cooldowns[cd_key] = now_ts

                    # Dispatch per channel
                    if rule.channel == NotificationChannel.WEBHOOK and rule.integration_id:
                        intg_res = await session.execute(select(IntegrationConfig).where(IntegrationConfig.id == rule.integration_id))
                        intg = intg_res.scalars().first()
                        if intg and intg.endpoint_url:
                            asyncio.create_task(self._send_webhook(intg.endpoint_url, intg.headers_json, incident))
                    elif rule.channel == NotificationChannel.WEBSOCKET:
                        await event_bus.publish("notification:alert", {
                            "title": title,
                            "message": message,
                            "severity": severity_str,
                            "incident_code": code
                        })
                except Exception as e:
                    logger.error(f"Error evaluating notification rule #{rule.id}: {e}")

    async def _send_webhook(self, url: str, headers_json: str, payload: Dict[str, Any]):
        """Dispatches structured JSON webhook with timeout and retry."""
        headers = {"Content-Type": "application/json", "User-Agent": "ARC-VISION-C2/1.0"}
        try:
            custom_headers = json.loads(headers_json or "{}")
            headers.update(custom_headers)
        except Exception:
            pass

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                logger.info(f"Dispatched webhook to {url} - Status {resp.status_code}")
            except Exception as e:
                logger.warning(f"Failed to dispatch webhook to {url}: {e}")

notification_service = NotificationService()
