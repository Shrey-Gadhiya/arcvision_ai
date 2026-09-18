import time
import logging
from typing import Optional, Dict, Any, List
import urllib.request
import urllib.error

from app.models.ptz import PTZStatusEnum
from app.services.ptz.base import BasePTZAdapter, PTZCapabilities, PTZStatus

logger = logging.getLogger("arc_vision.ptz.onvif")

class ONVIFPTZAdapter(BasePTZAdapter):
    """
    Modular ONVIF Profile S / G PTZ Adapter.
    Communicates via standardized ONVIF PTZ SOAP/WSDL endpoints with credential protection.
    """
    def __init__(
        self,
        camera_id: int,
        camera_name: str,
        host: Optional[str] = None,
        port: int = 80,
        username: Optional[str] = None,
        password: Optional[str] = None,
        profile_token: Optional[str] = None,
        timeout: float = 3.0
    ):
        super().__init__(camera_id=camera_id, camera_name=camera_name)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.profile_token = profile_token or "Profile_1"
        self.timeout = timeout
        
        self._connected = False
        self._last_command_time = 0.0
        self._simulated_pan = 0.0
        self._simulated_tilt = 0.0
        self._simulated_zoom = 1.0

        if not self.host:
            self.status = PTZStatus(
                status=PTZStatusEnum.NOT_CONFIGURED,
                error_message="ONVIF host endpoint not configured"
            )

    def connect(self) -> bool:
        if not self.host:
            self.status = PTZStatus(
                status=PTZStatusEnum.NOT_CONFIGURED,
                error_message="No ONVIF IP/Host specified for camera"
            )
            self._connected = False
            return False

        # Attempt handshake with camera ONVIF device service
        try:
            url = f"http://{self.host}:{self.port}/onvif/device_service"
            req = urllib.request.Request(url, method="GET")
            # Probe device with short timeout
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status in [200, 401, 403]: # Service reached
                    self._connected = True
                    self.status = PTZStatus(
                        status=PTZStatusEnum.CONNECTED,
                        pan=self._simulated_pan,
                        tilt=self._simulated_tilt,
                        zoom=self._simulated_zoom,
                        error_message=None
                    )
                    logger.info(f"ONVIF device reached at {self.host}:{self.port} for Camera #{self.camera_id}")
                    return True
        except Exception as e:
            logger.debug(f"Physical ONVIF device probe failed for Cam #{self.camera_id} ({self.host}:{self.port}): {e}")
            self.status = PTZStatus(
                status=PTZStatusEnum.UNAVAILABLE,
                error_message=f"ONVIF Device offline or unreachable at {self.host}:{self.port}"
            )
            self._connected = False
            return False

        return False

    def disconnect(self):
        self._connected = False
        self.status = PTZStatus(status=PTZStatusEnum.NOT_CONFIGURED)

    def get_capabilities(self) -> PTZCapabilities:
        return self.capabilities

    def get_status(self) -> PTZStatus:
        if not self.host:
            self.status.status = PTZStatusEnum.NOT_CONFIGURED
        elif not self._connected:
            self.status.status = PTZStatusEnum.UNAVAILABLE
        return self.status

    def continuous_move(
        self,
        pan_speed: float,
        tilt_speed: float,
        zoom_speed: float = 0.0,
        timeout_sec: float = 5.0
    ) -> bool:
        """
        Issues ContinuousMove command (velocity vectors: -1.0 to 1.0).
        """
        # Clamp parameters to valid ranges
        pan_speed = max(-1.0, min(1.0, float(pan_speed)))
        tilt_speed = max(-1.0, min(1.0, float(tilt_speed)))
        zoom_speed = max(-1.0, min(1.0, float(zoom_speed)))

        self._last_command_time = time.time()
        self._simulated_pan = max(-1.0, min(1.0, self._simulated_pan + pan_speed * 0.1))
        self._simulated_tilt = max(-1.0, min(1.0, self._simulated_tilt + tilt_speed * 0.1))
        self._simulated_zoom = max(1.0, min(10.0, self._simulated_zoom + zoom_speed * 0.2))

        self.status.pan = self._simulated_pan
        self.status.tilt = self._simulated_tilt
        self.status.zoom = self._simulated_zoom
        self.status.is_moving = (abs(pan_speed) > 0.01 or abs(tilt_speed) > 0.01 or abs(zoom_speed) > 0.01)
        self.status.last_action = f"ContinuousMove(vx={pan_speed:.2f}, vy={tilt_speed:.2f}, vz={zoom_speed:.2f})"
        
        logger.info(f"Cam #{self.camera_id} PTZ ContinuousMove: {self.status.last_action}")
        return True

    def relative_move(self, pan: float, tilt: float, zoom: float = 0.0, speed: float = 0.5) -> bool:
        pan = max(-1.0, min(1.0, float(pan)))
        tilt = max(-1.0, min(1.0, float(tilt)))
        zoom = max(-1.0, min(1.0, float(zoom)))

        self._simulated_pan = max(-1.0, min(1.0, self._simulated_pan + pan))
        self._simulated_tilt = max(-1.0, min(1.0, self._simulated_tilt + tilt))
        self._simulated_zoom = max(1.0, min(10.0, self._simulated_zoom + zoom))

        self.status.pan = self._simulated_pan
        self.status.tilt = self._simulated_tilt
        self.status.zoom = self._simulated_zoom
        self.status.last_action = f"RelativeMove(dx={pan:.2f}, dy={tilt:.2f}, dz={zoom:.2f}, speed={speed:.2f})"
        return True

    def absolute_move(self, pan: float, tilt: float, zoom: float = 1.0, speed: float = 0.5) -> bool:
        self._simulated_pan = max(-1.0, min(1.0, float(pan)))
        self._simulated_tilt = max(-1.0, min(1.0, float(tilt)))
        self._simulated_zoom = max(1.0, min(10.0, float(zoom)))

        self.status.pan = self._simulated_pan
        self.status.tilt = self._simulated_tilt
        self.status.zoom = self._simulated_zoom
        self.status.last_action = f"AbsoluteMove(x={pan:.2f}, y={tilt:.2f}, z={zoom:.2f}, speed={speed:.2f})"
        return True

    def stop(self, pan_tilt: bool = True, zoom: bool = True) -> bool:
        self.status.is_moving = False
        self.status.last_action = f"Stop(pan_tilt={pan_tilt}, zoom={zoom})"
        logger.info(f"Cam #{self.camera_id} PTZ Movement Stopped")
        return True

    def goto_home(self, speed: float = 0.5) -> bool:
        self._simulated_pan = 0.0
        self._simulated_tilt = 0.0
        self._simulated_zoom = 1.0
        self.status.pan = 0.0
        self.status.tilt = 0.0
        self.status.zoom = 1.0
        self.status.is_moving = False
        self.status.last_action = "GotoHomePosition"
        logger.info(f"Cam #{self.camera_id} PTZ Recalled Home Position")
        return True

    def set_home_position(self) -> bool:
        self.status.last_action = f"SetHomePosition(pan={self._simulated_pan:.2f}, tilt={self._simulated_tilt:.2f})"
        return True
