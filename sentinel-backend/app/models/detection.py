"""
MongoDB Models for Detection Results
Defines data structures for storing detection metadata
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class DetectionBoxDB(BaseModel):
    """Bounding box for detected objects"""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_name: str
    track_id: Optional[int] = None


class CongestionZoneDB(BaseModel):
    """Congestion zone information"""
    zone: str = ""
    x: int = 0
    y: int = 0
    count: int = 0
    congestion: float = 0.0


class DetectionResultDB(BaseModel):
    """Single frame detection result for MongoDB"""
    detection_type: str = "image"  # "image" or "video_frame"
    frame_idx: int = 0
    person_count: int = 0
    detections: List[DetectionBoxDB] = Field(default_factory=list)
    density_estimate: float = 0.0
    risk_score: float = 0.0
    risk_level: str = "LOW"
    anomaly_score: float = 0.0
    stampede_risk: float = 0.0
    flow_rate: float = 0.0
    congestion_zones: List[CongestionZoneDB] = Field(default_factory=list)
    
    # File references
    annotated_image_path: Optional[str] = None
    heatmap_path: Optional[str] = None
    original_filename: Optional[str] = None
    
    # Metadata
    inference_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    upload_source: Optional[str] = None


class VideoDetectionResultDB(BaseModel):
    """Multi-frame video detection result for MongoDB"""
    detection_type: str = "video"
    
    # Video summary
    total_frames: int = 0
    processed_frames: int = 0
    avg_person_count: float = 0.0
    max_person_count: int = 0
    avg_risk_score: float = 0.0
    peak_risk_score: float = 0.0
    peak_risk_level: str = "LOW"
    
    # File references
    original_filename: Optional[str] = None
    video_path: Optional[str] = None
    
    # Frame results (list of MongoDB ObjectId strings)
    frame_results: List[str] = Field(default_factory=list)
    
    # Metadata
    processing_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    upload_source: Optional[str] = None
