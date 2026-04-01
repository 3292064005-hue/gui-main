from dataclasses import dataclass


@dataclass
class DeviceHealth:
    connected: bool = False
    health: str = "offline"
    detail: str = ""
    fresh: bool = False
    last_ts_ns: int = 0


DeviceStatus = DeviceHealth
