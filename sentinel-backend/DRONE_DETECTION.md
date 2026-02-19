# Drone Detection Mode - VisDrone Model Setup

## Overview

The Sentinel system now supports two detection modes:

| Mode | Use Case | Model | Optimized For |
|------|----------|-------|---------------|
| **CCTV** | Ground-level cameras | yolov8n.pt (COCO) | Standard surveillance |
| **Drone** | Aerial/drone footage | yolov8n-visdrone.pt | Small objects from altitude |

## Current Status

The drone mode will work with the current CCTV model (yolov8n.pt) as a fallback, but for optimal drone footage detection, you should use a VisDrone-trained model.

### Fallback Behavior

If `yolov8n-visdrone.pt` is not found:
- System will use `yolov8n.pt` with drone-optimized parameters
- Lower confidence threshold (0.25 vs 0.30)
- Adjusted risk calculations for larger coverage areas
- Warning will be logged: `"VisDrone model not found, using CCTV model with drone params"`

## Getting a VisDrone-Trained Model

### Option 1: Train Your Own (Recommended for production)

1. **Download VisDrone Dataset:**
   ```bash
   # VisDrone 2019 Detection dataset
   # https://github.com/VisDrone/VisDrone-Dataset
   ```

2. **Train YOLOv8 on VisDrone:**
   ```python
   from ultralytics import YOLO
   
   # Load base model
   model = YOLO('yolov8n.pt')
   
   # Train on VisDrone dataset
   model.train(
       data='VisDrone.yaml',  # VisDrone dataset config
       epochs=100,
       imgsz=640,
       batch=16,
       name='yolov8n-visdrone'
   )
   
   # Export trained model
   model.export(format='pt')
   ```

3. **Copy trained model:**
   ```bash
   cp runs/detect/yolov8n-visdrone/weights/best.pt sentinel-backend/yolov8n-visdrone.pt
   ```

### Option 2: Download Pre-trained (Community)

Several pre-trained VisDrone YOLOv8 models are available:

1. **Ultralytics Hub:**
   - Visit: https://hub.ultralytics.com/
   - Search for "VisDrone" models
   - Download a compatible YOLOv8n checkpoint

2. **GitHub Community Models:**
   ```bash
   # Search GitHub for "yolov8 visdrone weights"
   # Look for models with good benchmarks on VisDrone val set
   ```

### Option 3: Use with Current Model

The system works without a specialized drone model:

1. Upload drone footage in the Detection page
2. Select "Drone" mode in the UI
3. System applies drone-optimized parameters to CCTV model

This provides reasonable results for:
- Lower altitude footage (< 100m)
- Larger crowd gatherings
- Clear weather conditions

## VisDrone Class Mapping

The VisDrone dataset includes 10 classes:

| ID | Class | Mapped To |
|----|-------|-----------|
| 0 | pedestrian | person |
| 1 | people | person |
| 2 | bicycle | bicycle |
| 3 | car | car |
| 4 | van | van |
| 5 | truck | truck |
| 6 | tricycle | tricycle |
| 7 | awning-tricycle | awning-tricycle |
| 8 | bus | bus |
| 9 | motor | motor |

For crowd detection, classes 0 (pedestrian) and 1 (people) are mapped to "person" for counting.

## API Usage

### Upload with Mode Selection

```bash
# Auto-detect mode
curl -X POST "http://localhost:8000/api/v1/detect/upload" \
  -F "file=@drone_video.mp4"

# Force CCTV mode
curl -X POST "http://localhost:8000/api/v1/detect/upload?mode=cctv" \
  -F "file=@video.mp4"

# Force Drone mode
curl -X POST "http://localhost:8000/api/v1/detect/upload?mode=drone" \
  -F "file=@drone_footage.mp4"
```

### Response includes detection_mode

```json
{
  "person_count": 45,
  "risk_level": "MEDIUM",
  "detection_mode": "drone",
  ...
}
```

## UI Usage

1. Go to **Detection → Upload Detection**
2. Click mode selector: **Auto | CCTV | Drone**
3. Upload your file
4. Mode badge appears in results showing which mode was used

## Performance Notes

| Aspect | CCTV Mode | Drone Mode |
|--------|-----------|------------|
| Confidence | 0.30 | 0.25 |
| IOU | 0.45 | 0.40 |
| Person threshold | 80 | 150 |
| Density scale | 640x480 | 1280x720 |
| Annotation color | Cyan | Orange |

## Testing

To verify drone mode is working:

1. Check backend logs:
   ```
   detect.yolo_drone_loaded model=yolov8n-visdrone.pt
   ```
   or fallback:
   ```
   detect.visdrone_model_not_found message="VisDrone model not found..."
   detect.yolo_drone_fallback model=yolov8n.pt
   ```

2. Check result `detection_mode` field in API response
3. Check UI badge showing "DRONE" or "CCTV"
