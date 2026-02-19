# 🚀 PRAVAHA - Perception Layer Setup & Run Guide

**Layers Complete:** Phases 1-4 (Sensing + Perception)

---

## 📋 Prerequisites

### System Requirements
- **OS:** Windows 10/11
- **GPU:** NVIDIA RTX 3050 6GB (or better)
- **RAM:** 8GB minimum, 16GB recommended
- **Storage:** 5GB free space
- **Python:** 3.10 or higher

### Check CUDA Installation
```powershell
# Check if NVIDIA GPU is available
nvidia-smi

# Check CUDA version (should be 11.8 or compatible)
nvcc --version
```

If CUDA is not installed, download from: https://developer.nvidia.com/cuda-11-8-0-download-archive

---

## 🔧 Installation Steps

### Step 1: Navigate to Project Directory
```powershell
cd D:\project\Crowd
```

### Step 2: Create Virtual Environment (Recommended)
```powershell
# Create venv
python -m venv venv

# Activate venv
.\venv\Scripts\Activate

# Verify activation (should show (venv) in prompt)
```

### Step 3: Install Dependencies
```powershell
# Install PyTorch with CUDA support first
pip install torch==2.1.0+cu118 torchvision==0.16.0+cu118 --index-url https://download.pytorch.org/whl/cu118

# Install remaining dependencies
pip install -r requirements.txt

# Verify installation
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
# Should print: CUDA available: True
```

**Note:** If CUDA shows False, check GPU drivers and CUDA installation.

### Step 4: Verify YOLOv8 Installation
```powershell
# Test YOLOv8 (will auto-download model ~6MB)
python -c "from ultralytics import YOLO; model = YOLO('yolov8n.pt'); print('YOLOv8 ready!')"
```

---

## 🎥 Prepare Test Video

### Option A: Download Sample Video
```powershell
# Create input directory
New-Item -ItemType Directory -Force -Path "data\input"

# Download sample crowd video (use browser or yt-dlp)
# Recommended sources:
# - Pexels: https://www.pexels.com/search/videos/crowd/
# - Pixabay: https://pixabay.com/videos/search/crowd/

# Place video in: data\input\crowd_video.mp4
```

### Option B: Use Your Own Video
- Resolution: 720p-1080p (optimal)
- Duration: 5-10 minutes (for testing)
- Scene: Crowded area (market, festival, station)
- Format: MP4, AVI, or MOV

---

## 🧪 Test Individual Phases

### Test Phase 1: Data Acquisition
```powershell
# Test with webcam
python tests\test_webcam_phase1.py

# Test with video file
python src\phase1_data_acquisition.py data\input\crowd_video.mp4
```

**Expected Output:**
```
✅ Phase 1 test complete!
   Total frames: 30
   Duration: X seconds
   FPS: ~50 (frame extraction speed)
```

### Test Phase 2: Preprocessing
```powershell
python src\phase2_preprocessing.py data\input\crowd_video.mp4
```

**Expected Output:**
```
📊 Preprocessing Statistics
   Frames processed: 30
   Average time/frame: ~10-15 ms
   Processing FPS: ~70-100
✅ Ready for Phase 3
```

### Test Phase 3: YOLO Detection
```powershell
python src\phase3_yolo_detection.py data\input\crowd_video.mp4
```

**Expected Output:**
```
🎯 Phase 3 (Detection):
   Total detections: X
   Avg persons/frame: Y
   Detection FPS: ~15-20
   Sample frames saved to: data/output/phase3_samples/
✅ Ready for Phase 4
```

### Test Phase 4: DeepSORT Tracking
```powershell
python src\phase4_deepsort_tracking.py data\input\crowd_video.mp4
```

**Expected Output:**
```
🔍 Phase 4 (Tracking):
   Total tracks created: X
   Peak active tracks: Y
   Sample frames saved to: data/output/phase4_samples/
✅ Perception Layer fully functional!
```

---

## 🌊 Run Complete Perception Layer

### Basic Usage
```powershell
# Run complete pipeline (Phases 1-4)
python src\run_perception_layer.py data\input\crowd_video.mp4
```

**Output:**
- Tracked video: `data\output\crowd_video_tracked.mp4`
- Statistics: `data\output\crowd_video_tracked_stats.txt`

### Advanced Usage
```powershell
# Specify output path
python src\run_perception_layer.py data\input\video.mp4 -o data\output\result.mp4

# Adjust confidence threshold (lower = more detections)
python src\run_perception_layer.py data\input\video.mp4 -c 0.3

# Limit max tracks (for memory optimization)
python src\run_perception_layer.py data\input\video.mp4 -m 50

# Show live preview (press 'q' to quit)
python src\run_perception_layer.py data\input\video.mp4 -p

# Combine options
python src\run_perception_layer.py data\input\video.mp4 -o output.mp4 -c 0.5 -m 100 -p
```

### Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output` | Output video path | Auto-generated |
| `-c, --confidence` | YOLO confidence (0.0-1.0) | 0.4 |
| `-m, --max-tracks` | Max simultaneous tracks | 100 |
| `-p, --preview` | Show live preview | False |
| `--no-stats` | Don't save statistics | False |

---

## 📊 Expected Performance (RTX 3050 6GB)

### Processing Speed
| Phase | Time/Frame | FPS |
|-------|------------|-----|
| Phase 1: Data Acquisition | ~20 ms | 50 |
| Phase 2: Preprocessing | ~10-15 ms | 70-100 |
| Phase 3: YOLO Detection | ~60-80 ms | 12-16 |
| Phase 4: DeepSORT Tracking | ~5-10 ms | 100-200 |
| **Combined (1-4)** | **~100-125 ms** | **~8-10 FPS** |

### For 10-Minute Video (18,000 frames)
- Processing time: **30-37 minutes**
- GPU memory: **~4-5GB peak**
- Output size: Similar to input (~200-500MB)

---

## 📁 Output Files

After running the perception layer, you'll get:

### 1. Tracked Video
- **Location:** `data/output/<video_name>_tracked.mp4`
- **Content:** Original video with bounding boxes, track IDs, and trajectories
- **Visualization:**
  - Green boxes around detected persons
  - Track IDs displayed above each person
  - Trajectory trails showing movement paths
  - Frame counter and track count overlay

### 2. Statistics File
- **Location:** `data/output/<video_name>_tracked_stats.txt`
- **Content:**
  - Total frames processed
  - Processing time per phase
  - Average FPS
  - Detection counts
  - Track statistics

### 3. Sample Frames (from individual tests)
- **Phase 3 samples:** `data/output/phase3_samples/`
- **Phase 4 samples:** `data/output/phase4_samples/`

---

## 🐛 Troubleshooting

### Issue: "CUDA not available"
**Solution:**
```powershell
# Reinstall PyTorch with CUDA
pip uninstall torch torchvision
pip install torch==2.1.0+cu118 torchvision==0.16.0+cu118 --index-url https://download.pytorch.org/whl/cu118

# Update GPU driver from: https://www.nvidia.com/Download/index.aspx
```

### Issue: "Out of memory" error
**Solution:**
```powershell
# Reduce max tracks
python src\run_perception_layer.py video.mp4 -m 50

# Or process shorter video segment (first 5 min)
```

### Issue: YOLOv8 download fails
**Solution:**
```powershell
# Manually download yolov8n.pt from:
# https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
# Place in: models/yolov8n.pt

# Then run with:
python src\run_perception_layer.py video.mp4
```

### Issue: Low FPS (~2-3 FPS)
**Causes:**
- High resolution video (>1080p)
- Too many simultaneous tracks (>150)
- Running on CPU instead of GPU

**Solution:**
```powershell
# Verify GPU usage
python -c "import torch; print(torch.cuda.is_available())"

# Reduce confidence threshold to get fewer detections
python src\run_perception_layer.py video.mp4 -c 0.5

# Limit tracks
python src\run_perception_layer.py video.mp4 -m 50
```

### Issue: No persons detected
**Solution:**
```powershell
# Lower confidence threshold
python src\run_perception_layer.py video.mp4 -c 0.3

# Check if video has people visible
# Try with webcam test first
python tests\test_webcam_phase1.py
```

---

## ✅ Verification Checklist

Before running full pipeline:

- [ ] CUDA available (check with `nvidia-smi`)
- [ ] PyTorch with CUDA installed
- [ ] YOLOv8 model downloaded (auto-downloads on first run)
- [ ] Test video placed in `data/input/`
- [ ] Virtual environment activated
- [ ] All dependencies installed (`pip list`)

---

## 📚 File Reference

### Source Files
| File | Purpose | Test Command |
|------|---------|--------------|
| `phase1_data_acquisition.py` | Load video, extract frames | `python src\phase1_data_acquisition.py <video>` |
| `phase2_preprocessing.py` | Resize, denoise, enhance | `python src\phase2_preprocessing.py <video>` |
| `phase3_yolo_detection.py` | Detect persons with YOLO | `python src\phase3_yolo_detection.py <video>` |
| `phase4_deepsort_tracking.py` | Track persons across frames | `python src\phase4_deepsort_tracking.py <video>` |
| `run_perception_layer.py` | Run all phases together | `python src\run_perception_layer.py <video>` |

### Test Files
| File | Purpose | Command |
|------|---------|---------|
| `test_webcam_phase1.py` | Test with webcam | `python tests\test_webcam_phase1.py` |

---

## 🎯 Next Steps

After successfully running Perception Layer (Phases 1-4):

### Immediate Next: Phase 5-8 (Prediction Layer)
- Phase 5: Motion Vector Analysis (Optical Flow)
- Phase 6: Crowd Density Estimation (Grid-based heatmap)
- Phase 7: Trajectory Prediction (LSTM)
- Phase 8: Anomaly Detection (Isolation Forest)

### Then: Phase 9-11 (Decision Layer)
- Phase 9: Congestion Analysis (Bottleneck detection)
- Phase 10: Risk Scoring (Multi-factor 0-100 scale)
- Phase 11: Alert Classification (Low/Medium/High/Critical)

### Finally: Phase 12-14 (Action Layer)
- Phase 12: Safe Path Planning (A* algorithm)
- Phase 13: Alert Generation (Actionable alerts)
- Phase 14: Visualization & Output (Final report)

---

## 🆘 Support

### Check Logs
```powershell
# Enable verbose output
python src\run_perception_layer.py video.mp4 --verbose
```

### GPU Monitor
```powershell
# Monitor GPU usage in real-time
nvidia-smi -l 1
```

### System Info
```powershell
# Check Python version
python --version

# Check installed packages
pip list

# Check torch version
python -c "import torch; print(torch.__version__)"
```

---

## 📌 Quick Command Reference

```powershell
# Setup
cd D:\project\Crowd
.\venv\Scripts\Activate
pip install -r requirements.txt

# Test
python tests\test_webcam_phase1.py

# Run
python src\run_perception_layer.py data\input\crowd_video.mp4

# With options
python src\run_perception_layer.py data\input\video.mp4 -o output.mp4 -c 0.4 -p
```

---

**Ready to process crowd videos! 🌊**

For full system architecture, see [WORKFLOW.md](../WORKFLOW.md)
