import abc
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from app.models.ptz import PTZStatusEnum

@dataclass
class PTZCapabilities:
    supports_continuous_move: bool = True
    supports_relative_move: bool = True
    supports_absolute_move: bool = False
    supports_zoom: bool = True
    supports_presets: bool = True
    supports_home_position: bool = True
    supports_speed_control: bool = True
    max_presets: int = 128
    pan_range: tuple = (-1.0, 1.0)
    tilt_range: tuple = (-1.0, 1.0)
    zoom_range: tuple = (0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supports_continuous_move": self.supports_continuous_move,
            "supports_relative_move": self.supports_relative_move,
            "supports_absolute_move": self.supports_absolute_move,
            "supports_zoom": self.supports_zoom,
            "supports_presets": self.supports_presets,
            "supports_home_position": self.supports_home_position,
            "supports_speed_control": self.supports_speed_control,
            "max_presets": self.max_presets,
            "pan_range": list(self.pan_range),
            "tilt_range": list(self.tilt_range),
            "zoom_range": list(self.zoom_range)
        }

@dataclass
class PTZStatus:
    status: PTZStatusEnum = PTZStatusEnum.NOT_CONFIGURED
    pan: float = 0.0
    tilt: float = 0.0
    zoom: float = 1.0
    is_moving: bool = False
    last_action: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value if hasattr(self.status, 'value') else str(self.status),
            "pan": round(self.pan, 3),
            "tilt": round(self.tilt, 3),
            "zoom": round(self.zoom, 3),
            "is_moving": self.is_moving,
            "last_action": self.last_action,
            "error_message": self.error_message
        }

class BasePTZAdapter(abc.ABC):
    """
    Standard replaceable contract for Pan/Tilt/Zoom camera controllers.
    """
    def __init__(self, camera_id: int, camera_name: str):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.status = PTZStatus(status=PTZStatusEnum.NOT_CONFIGURED)
        self.capabilities = PTZCapabilities()

    @abc.abstractmethod
    def connect(self) -> bool:
        pass

    @abc.abstractmethod
    def disconnect(self):
        pass

    @abc.abstractmethod
    def get_capabilities(self) -> PTZCapabilities:
        pass

    @abc.abstractmethod
    def get_status(self) -> PTZStatus:
        pass

    @abc.abstractmethod
    def continuous_move(self, pan_speed: float, tilt_speed: float, zoom_speed: float = 0.0, timeout_sec: float = 5.0) -> bool:
        pass

    @abc.abstractmethod
    def relative_move(self, pan: float, tilt: float, zoom: float = 0.0, speed: float = 0.5) -> bool:
        pass

    @abc.abstractmethod
    def absolute_move(self, pan: float, tilt: float, zoom: float = 1.0, speed: float = 0.5) -> bool:
        pass

    @abc.abstractmethod
    def stop(self, pan_tilt: bool = True, zoom: bool = True) -> bool:
        pass

    @abc.abstractmethod
    def goto_home(self, speed: float = 0.5) -> bool:
        pass

    @abc.abstractmethod
    def set_home_position(self) -> bool:
        pass
