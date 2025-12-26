from pydantic import BaseModel, Field, IPvAnyAddress, ValidationError, validator
from typing import Optional, Literal

class CameraConfig(BaseModel):
    """
    Validated Camera Configuration.
    Ensures that camera settings loaded from cameras.yml are valid.
    """
    id: str = Field(..., min_length=1, description="Unique camera identifier")
    name: str = Field(..., min_length=1, description="Human-readable camera name")
    location: str = Field("Unknown", description="Physical location")
    
    # Network settings (Optional, as data might come from filesystem without live feed)
    ip: Optional[str] = None # Using str to allow hostnames too, or IPvAnyAddress if strict IP
    port: int = Field(80, ge=1, le=65535)
    rtsp_url: Optional[str] = None
    
    # ML/Analytics Settings
    line_position: float = Field(0.5, ge=0.0, le=1.0, description="Position of counting line (0.0-1.0)")
    line_orientation: Literal["horizontal", "vertical"] = "horizontal"
    
    # Validation for IP/Hostname if present
    @validator('ip')
    def validate_ip_or_hostname(cls, v):
        if v and v.lower() == 'localhost':
            return v
        # Simple check, rely on pydantic's IPvAnyAddress if we want strict IP, 
        # but users might use hostnames like "camera-01.local".
        if v and len(v) < 2:
            raise ValueError("Invalid hostname/IP")
        return v
    
class CameraListConfig(BaseModel):
    """Wraps list of cameras from config file."""
    cameras: list[CameraConfig] = []
