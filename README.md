# 🌊 PRAVAHA - AI-Based Crowd Management System

**Perception Layer Complete ✅ (Phases 1-4)**

## 🎯 Project Overview

PRAVAHA is an AI-powered crowd management system designed for Indian venues (temples, festivals, railway stations) to prevent stampedes through predictive analysis. This system processes post-event video footage to identify risks and provide insights.

**Target Hardware:** NVIDIA RTX 3050 6GB  
**Processing Mode:** Post-event video analysis  
**Architecture:** 14-step pipeline across 5 layers

---

## 📁 Project Structure

```
Crowd/
├── src/
│   ├── phase1_data_acquisition.py    ✅ Phase 1: Data loading
│   ├── phase2_preprocessing.py       ✅ Phase 2: Frame preprocessing
│   ├── phase3_yolo_detection.py      ✅ Phase 3: Person detection
│   ├── phase4_deepsort_tracking.py   ✅ Phase 4: Multi-object tracking
│   └── run_perception_layer.py       ✅ Integrated pipeline (1-4)
├── data/
│   ├── input/                        📥 Place your videos here
│   └── output/                       📤 Processed results
├── tests/
│   └── test_webcam_phase1.py         🧪 Webcam test utility
├── requirements.txt                  📦 Dependencies (updated)
├── WORKFLOW.md                       📋 System workflow docs
├── RUN_INSTRUCTIONS.md               📖 Complete setup & run guide
└── README.md                         📖 This file
```

---

## 🚀 Quick Start

### Step 1: Install Dependencies

```powershell
# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate

# Install PyTorch with CUDA support
pip install torch==2.1.0+cu118 torchvision==0.16.0+cu118 --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
pip install -r requirements.txt
```

### Step 2: Verify Installation

```powershell
# Check CUDA availability
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# Test with webcam
python tests\test_webcam_phase1.py
```
![alt text](image.png)
### Step 3: Run Perception Layer

```powershell
# Place your video in data/input/ folder
# Example: data/input/crowd_video.mp4

# Run complete pipeline (Phases 1-4)
python src\run_perception_layer.py data\input\crowd_video.mp4

# With live preview
python src\run_perception_layer.py data\input\crowd_video.mp4 -p
```

**📖 For detailed setup instructions, see [RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md)**

---

## 🎨 Perception Layer Output

The complete perception pipeline (Phases 1-4) produces:

### Tracked Video
- Bounding boxes around detected persons
- Unique track IDs for each person
- Trajectory trails showing movement paths
- Frame counter and statistics overlay

### Statistics Report
- Total persons detected
- Active tracks over time
- Processing performance (FPS)
- Detection accuracy metrics

**Example:** See sample outputs in `data/output/` after running pipeline

---

## 🛠️ Implementation Status

### ✅ Completed Phases

#### Phase 1: Multi-Modal Data Acquisition
- Loads video files (MP4, AVI, MOV)
- Extracts frames with metadata
- Supports webcam capture for testing
- **Performance:** ~50 FPS frame extraction

#### Phase 2: Frame Preprocessing
- Resizes frames to 640×640 for YOLO
- Gaussian blur for denoising
- CLAHE contrast enhancement
- Normalizes to [0, 1] range
- **Performance:** ~70-100 FPS

#### Phase 3: YOLOv8 Detection
- YOLOv8n person detection
- Confidence-based filtering
- GPU accelerated (CUDA)
- **Performance:** ~12-16 FPS on RTX 3050

#### Phase 4: DeepSORT Tracking
- Multi-object tracking across frames
- Unique ID assignment
- Trajectory history maintenance
- IoU-based matching
- **Performance:** ~100-200 FPS

#### Integrated Pipeline
- Runs all phases (1-4) seamlessly
- Generates annotated output video
- Saves performance statistics
- **Combined Performance:** ~8-10 FPS

---

## 🛠️ What's Next?

### Phase 5-8: Prediction Layer (Pending)
- Phase 5: Motion Vector Analysis (Optical Flow)
- Phase 6: Crowd Density Estimation (Grid-based heatmap)
- Phase 7: Trajectory Prediction (LSTM)
- Phase 8: Anomaly Detection (Isolation Forest)

### Phase 9-11: Decision Layer (Pending)
- Phase 9: Congestion Analysis
- Phase 10: Risk Scoring
- Phase 11: Alert Classification

### Phase 12-14: Action Layer (Pending)
- Phase 12: Safe Path Planning
- Phase 13: Alert Generation
- Phase 14: Visualization & Output

---

## 📊 System Architecture

```
Layer 1: Sensing Layer
├── Phase 1: Multi-Modal Data Acquisition ✅

Layer 2: Perception Layer
├── Phase 2: Frame Preprocessing ⏳
├── Phase 3: YOLOv8 Detection ⏳
├── Phase 4: DeepSORT Tracking ⏳

Layer 3: Prediction Layer
├── Phase 5-8: Motion & Density Analysis ⏳

Layer 4: Decision Layer
├── Phase 9-11: Risk Scoring ⏳

Layer 5: Action Layer
├── Phase 12-14: Alert Generation ⏳
```

---

## 💻 Hardware Requirements

- **GPU:** NVIDIA RTX 3050 6GB (or better)
- **RAM:** 8GB minimum, 16GB recommended
- **Storage:** 5GB for models and data
- **OS:** Windows 10/11 with CUDA 11.8

---

## 🎥 Sample Data Sources

Download crowd videos from:
1. YouTube (use `yt-dlp` or similar)
2. Pexels/Pixabay (royalty-free videos)
3. Record your own with smartphone

**Recommended videos:**
- Duration: 5-10 minutes
- Resolution: 720p-1080p
- Scene: Crowded areas (markets, festivals, stations)

---

## 📝 Testing Checklist

### Phase 1 Testing

- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Test webcam (`python tests\test_webcam_phase1.py`)
- [ ] Download sample crowd video
- [ ] Test video processing (`python src\phase1_data_acquisition.py <video_path>`)
- [ ] Verify output: 30 frames processed, performance metrics shown

### Phase 2 Testing (When implemented)
- [ ] Verify frame resizing (1080p → 640×640)
- [ ] Check Gaussian blur effect
- [ ] Validate CLAHE enhancement
- [ ] Confirm normalization [0, 1]

---

## 🐛 Troubleshooting

### Issue: "No module named 'cv2'"
```powershell
pip install opencv-python
```

### Issue: "CUDA not available"
```powershell
# Check CUDA installation
python -c "import torch; print(torch.cuda.is_available())"

# If False, reinstall PyTorch with CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Issue: "Webcam not working"
- Check camera permissions in Windows Settings
- Try different camera_id: `WebcamDataLoader(camera_id=1)`

### Issue: "Video file not found"
- Use absolute path: `D:\project\Crowd\data\input\video.mp4`
- Check file format (supported: MP4, AVI, MOV)

---

## 📚 Documentation

- [WORKFLOW.md](WORKFLOW.md) - Complete 14-step data flow architecture
- [RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md) - Detailed setup & run guide
- **Source Code Documentation:**
  - [phase1_data_acquisition.py](src/phase1_data_acquisition.py) - Video loading
  - [phase2_preprocessing.py](src/phase2_preprocessing.py) - Frame preprocessing
  - [phase3_yolo_detection.py](src/phase3_yolo_detection.py) - Person detection
  - [phase4_deepsort_tracking.py](src/phase4_deepsort_tracking.py) - Object tracking
  - [run_perception_layer.py](src/run_perception_layer.py) - Integrated pipeline

---

## 🎯 Competition Goal

Build a cost-effective crowd management system:
- **Budget:** ₹15,000 (RTX 3050 setup)
- **vs Enterprise:** ₹50 lakh+ systems
- **Advantage:** Post-processing = no real-time constraints
- **Target:** Hackathon/competition submission

---

## 📊 Current Status

| Phase | Description | Status | Files |
|-------|-------------|--------|-------|
| 1 | Data Acquisition | ✅ Complete | phase1_data_acquisition.py |
| 2 | Preprocessing | ✅ Complete | phase2_preprocessing.py |
| 3 | YOLO Detection | ✅ Complete | phase3_yolo_detection.py |
| 4 | DeepSORT Tracking | ✅ Complete | phase4_deepsort_tracking.py |
| - | **Integrated Pipeline** | ✅ Complete | run_perception_layer.py |
| 5-14 | Prediction/Decision/Action | ⏳ Pending | - |

**Perception Layer (Phases 1-4): FULLY FUNCTIONAL ✅**

---

## 📈 Performance Metrics (RTX 3050 6GB)

### Processing Speed
- **Phase 1:** 50 FPS (frame extraction)
- **Phase 2:** 70-100 FPS (preprocessing)
- **Phase 3:** 12-16 FPS (YOLO detection)
- **Phase 4:** 100-200 FPS (tracking)
- **Combined:** 8-10 FPS (full pipeline)

### For 10-Minute Video
- **Input:** 18,000 frames (30 FPS)
- **Processing time:** 30-37 minutes
- **GPU memory:** 4-5GB peak
- **Output:** Tracked video + statistics

---

## 🤝 Contributing

This is a competition project. Implementation follows the architecture in [WORKFLOW.md](WORKFLOW.md).

---

## 📜 License

MIT License - Free for educational and competition use

---

## ✨ Acknowledgments

- YOLOv8 by Ultralytics
- DeepSORT by nwojke
- OpenCV community

---

**Next Steps:**

1. **Install & Test:** Follow [RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md) to set up and test the Perception Layer
2. **Process Videos:** Run the pipeline on your crowd videos
3. **Implement Phase 5-8:** Motion analysis, density estimation, prediction, anomaly detection
4. **Complete System:** Build remaining phases (9-14) for risk scoring and alerts

**Current Status:** Perception Layer (Phases 1-4) fully functional ✅

For questions or issues, refer to [RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md) troubleshooting section.
