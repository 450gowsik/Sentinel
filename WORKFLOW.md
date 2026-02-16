# 🔄 PRAVAHA - System Workflow

## 📊 High-Level Data Flow

```
VIDEO FILE (.mp4) 
    ↓
[LAYER 1: SENSING]
    ↓
[LAYER 2: PERCEPTION]
    ↓
[LAYER 3: PREDICTION]
    ↓
[LAYER 4: DECISION]
    ↓
[LAYER 5: ACTION]
    ↓
ALERTS & REPORTS
```

---

## 🔷 DETAILED WORKFLOW

### **INPUT → LAYER 1: SENSING & GEO-SPATIAL ALIGNMENT**

```
┌─────────────────────────────────────────────────────────────┐
│ INPUT: Video File                                           │
│ Format: MP4/AVI (1080p drone or 720p CCTV)                │
│ Example: "temple_festival_2026.mp4"                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Multi-Modal Data Acquisition                       │
│                                                             │
│ Process:                                                    │
│ • Open video file                                          │
│ • Read frame by frame                                      │
│ • Extract metadata (FPS, timestamp, resolution)            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ OUTPUT:                    │
        │ Raw Frame + Metadata       │
        ├────────────────────────────┤
        │ • Frame: (1080, 1920, 3)   │
        │ • Frame ID: 0              │
        │ • Timestamp: 0.033s        │
        │ • FPS: 30.0                │
        └────────────┬───────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Geo-Referencing                                    │
│                                                             │
│ Process:                                                    │
│ • Camera calibration (one-time setup)                      │
│ • Transform pixel coordinates → real-world meters          │
│                                                             │
│ Output:                                                     │
│ • Pixel (500, 300) → Real-world (12.5m, 8.3m)             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ OUTPUT:                    │
        │ Geo-Referenced Frame       │
        ├────────────────────────────┤
        │ • Frame with real-world    │
        │   coordinate mapping       │
        │ • Scale: 0.05 m/pixel      │
        │ • Camera height: 10m       │
        └────────────┬───────────────┘
                     │
                     ↓
                     
┌═════════════════════════════════════════════════════════════┐
│        LAYER 2: PERCEPTION & FLOW INTELLIGENCE              │
└═════════════════════════════════════════════════════════════┘

┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Preprocessing                                       │
│                                                             │
│ Process:                                                    │
│ • Resize: 1920×1080 → 640×640                             │
│ • Gaussian Blur: Remove noise                              │
│ • CLAHE: Enhance contrast                                  │
│ • Normalize: Scale to [0, 1]                               │
│                                                             │
│ Processing Time: ~6ms                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ OUTPUT:                    │
        │ Preprocessed Frame         │
        ├────────────────────────────┤
        │ • Clean frame (640×640)    │
        │ • Noise reduced            │
        │ • Contrast enhanced        │
        │ • Ready for AI detection   │
        └────────────┬───────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Human Detection (YOLOv8)                           │
│                                                             │
│ Process:                                                    │
│ • Run YOLOv8n model on GPU                                 │
│ • Detect all persons in frame                              │
│ • Filter and refine detections                             │
│                                                             │
│ Processing Time: ~25ms                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ OUTPUT:                    │
        │ Person Detections          │
        ├────────────────────────────┤
        │ • Bounding boxes for each  │
        │   person detected          │
        │ • Confidence scores        │
        │ • Person centers (x, y)    │
        │                            │
        │ • Total count: 47 people   │
        └────────────┬───────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Multi-Object Tracking (DeepSORT)                   │
│                                                             │
│ Process:                                                    │
│ • Extract appearance features                              │
│ • Predict next position (Kalman Filter)                    │
│ • Match detections → Assign persistent IDs                 │
│                                                             │
│ Processing Time: ~15ms                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ OUTPUT:                    │
        │ Tracked Individuals        │
        ├────────────────────────────┤
        │ • Each person has unique   │
        │   ID (e.g., Person #17)    │
        │ • Position history         │
        │   trajectory over time     │
        │ • Velocity (m/s)           │
        │                            │
        │ • Active tracks: 47        │
        └────────────┬───────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Crowd Flow Vector Field                            │
│                                                             │
│ Process:                                                    │
│ • Compute optical flow (motion between frames)             │
│ • Calculate velocity vectors                               │
│ • Extract movement metrics                                 │
│                                                             │
│ Processing Time: ~35ms                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ OUTPUT:                    │
        │ Motion V ector Field      │
        ├────────────────────────────┤
        │ • Movement vectors (vx,vy) │
        │ • Average speed: 2.1 m/s   │
        │ • Speed variance: 0.8      │
        │ • Direction chaos: 1.4     │
        │ • Turbulence index: 0.3    │
        │                            │
        │ • Visualization: Green     │
        │   arrows showing flow      │
        └────────────┬───────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: Choke Point Detection                              │
│                                                             │
│ Process:                                                    │
│ • Divide venue into grid (10×10 cells)                    │
│ • Calculate metrics per grid:                              │
│   - Density (people/m²)                                    │
│   - Speed variance                                         │
│   - Direction conflict                                     │
│ • Identify congestion hotspots                             │
│                                                             │
│ Formula: ChokeIndex = Density × Conflict × SpeedDrop       │
│                                                             │
│ Processing Time: ~10ms                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ OUTPUT:                    │
        │ Choke Point Locations      │
        ├────────────────────────────┤
        │ • Grid-based density map   │
        │                            │
        │ • Identified chokepoints:  │
        │   - Location: Gate 3       │
        │     (15.2m, 8.4m)          │
        │   - Severity: HIGH         │
        │   - Index: 2.1             │
        │                            │
        │ • Bottleneck regions       │
        │   marked for intervention  │
        └────────────┬───────────────┘
                     │
                     ↓
                     
┌═════════════════════════════════════════════════════════════┐
│        LAYER 3: PREDICTIVE DYNAMICS ENGINE                  │
└═════════════════════════════════════════════════════════════┘

┌─────────────────────────────────────────────────────────────┐
│ STEP 8: Feature Engineering                                │
│                                                             │
│ Process:                                                    │
│ • Aggregate all data from previous steps                  │
│ • Create statistical feature vector                        │
│                                                             │
│ Features:                                                   │
│ • Density, Speed variance, Entry/exit rates               │
│ • Direction conflict, Acceleration, Choke severity        │
│                                                             │
│ Processing Time: ~5ms                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ OUTPUT:                    │
        │ Feature Vector             │
        ├────────────────────────────┤
        │ • 7 numerical features     │
        │   normalized to [0, 1]     │
        │                            │
        │ • Example:                 │
        │   [4.2, 0.8, 0.6, 42.0,  │
        │    38.0, 0.3, 1.2]        │
        │                            │
        │ • Ready for ML models      │
        └────────────┬───────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 9: Anomaly Detection                                  │
│                                                             │
│ Process:                                                    │
│ • Use Isolation Forest algorithm                           │
│ • Detect unusual crowd behavior patterns                   │
│                                                             │
│ Detects:                                                    │
│ • Sudden density spikes                                    │
│ • Panic-like acceleration                                  │
│ • Flash crowd formation                                    │
│                                                             │
│ Processing Time: ~2ms                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ OUTPUT:                    │
        │ Anomaly Score              │
        ├────────────────────────────┤
        │ • Score: -0.42 (range -1  │
        │   to 1, <-0.5 = anomaly)   │
        │                            │
        │ • Is anomalous: Yes        │
        │                            │
        │ • Type: Density spike      │
        │                            │
        │ • Confidence: 87%          │
        └────────────┬───────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 10: Surge Prediction (LSTM)                           │
│                                                             │
│ Process:                                                    │
│ • Collect sequence of 30 feature vectors                  │
│ • Feed to trained LSTM neural network                      │
│ • Predict future density (5-30 seconds ahead)              │
│                                                             │
│ Note: Requires pre-trained model on historical data        │
│                                                             │
│ Processing Time: ~3-5ms                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ OUTPUT:                    │
        │ Future Predictions         │
        ├────────────────────────────┤
        │ • Current: 4.2 people/m²  │
        │                            │
        │ • Predictions:             │
        │   +5s: 4.8 people/m²      │
        │   +10s: 5.3               │
        │   +15s: 5.9               │
        │   +20s: 6.4 (DANGER!)     │
        │                            │
        │ • Surge probability: 76%   │
        │ • Trend: Increasing        │
        └────────────┬───────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 11: Spatial Risk Propagation                          │
│                                                             │
│ Process:                                                    │
│ • Model venue as grid graph                                │
│ • Apply diffusion equation to spread risk                  │
│ • Account for barriers and exits                           │
│                                                             │
│ Formula: R_t+1 = R_t + α × ∇²R_t                         │
│                                                             │
│ Processing Time: ~20ms                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ OUTPUT:                    │
        │ Risk Heatmap               │
        ├────────────────────────────┤
        │ • 2D risk map (10×10 grid) │
        │   Values: [0, 1]           │
        │   0 = Safe, 1 = Critical   │
        │                            │
        │ • High-risk zones:         │
        │   - Zone (2,3): 0.89       │
        │   - Zone (3,3): 0.91       │
        │                            │
        │ • Risk spread direction    │
        │   visualized with vectors  │
        └────────────┬───────────────┘
                     │
                     ↓
                     
┌═════════════════════════════════════════════════════════════┐
│        LAYER 4: ORCHESTRATION & DECISION ENGINE             │
└═════════════════════════════════════════════════════════════┘

┌─────────────────────────────────────────────────────────────┐
│ STEP 12: Risk Fusion & Adaptive Decision                   │
│                                                             │
│ Process:                                                    │
│ • Combine all intelligence from previous steps             │
│ • Calculate unified risk score                             │
│ • Classify risk level                                      │
│ • Generate actionable alerts                               │
│                                                             │
│ Risk Formula:                                               │
│   Risk = 0.25×Density + 0.15×SpeedVar + 0.15×Conflict      │
│        + 0.15×Anomaly + 0.15×Surge + 0.15×SpatialRisk      │
│                                                             │
│ Classification:                                             │
│   Risk < 0.50     → Safe ✅                                │
│   0.50 ≤ Risk < 0.75 → Warning ⚠️                         │
│   Risk ≥ 0.75     → Critical 🚨                           │
│                                                             │
│ Processing Time: ~5ms                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ OUTPUT:                    │
        │ Final Risk Assessment      │
        ├────────────────────────────┤
        │ • Risk score: 0.78         │
        │                            │
        │ • Status: CRITICAL 🚨      │
        │                            │
        │ • Primary concern:         │
        │   "High density + surge"   │
        │                            │
        │ • Affected zones:          │
        │   North Gate, Zone 3       │
        │                            │
        │ • Confidence: 89%          │
        └────────────┬───────────────┘
                     │
                     ↓
                     
┌═════════════════════════════════════════════════════════════┐
│        LAYER 5: ACTION & INTERVENTION                       │
└═════════════════════════════════════════════════════════════┘

┌─────────────────────────────────────────────────────────────┐
│ STEP 13: Evacuation Path Planning (A*)                     │
│ Module: phase13_evacuation.py                              │
│                                                             │
│ Process:                                                    │
│ • Model venue as graph (nodes = locations, edges = paths)  │
│ • Mark high-risk zones as obstacles                        │
│ • Use A* algorithm to find optimal evacuation routes       │
│ • Consider crowd density in path cost                      │
│                                                             │
│ Algorithm:                                                  │
│   graph = build_venue_graph()                              │
│                                                             │
│   for each high_risk_zone:                                 │
│       start = zone.location                                │
│       goals = [exit1, exit2, exit3]                        │
│                                                             │
│       path = a_star_search(                                │
│           start=start,                                     │
│           goal=nearest_exit(goals),                        │
│           heuristic=euclidean_distance,                    │
│           cost=lambda edge: (                              │
│               edge.distance                                │
│               + density_penalty(edge)                      │
│               + congestion_penalty(edge)                   │
│           )                                                 │
│       )                                                     │
│                                                             │
│       evacuation_routes.append(path)                       │
│                                                             │
│ Processing Time: ~15ms per route                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ DATA STRUCTURE #13:        │
        │ Evacuation Plan            │
        ├────────────────────────────┤
        │ • routes: List[Path]       │
        │   [                        │
        │     {                      │
        │       'from': 'North Gate',│
        │       'to': 'Exit_A',      │
        │       'path': [            │
        │         (15.2, 8.4),       │
        │         (16.0, 9.1),       │
        │         (17.5, 10.2),      │
        │         (18.0, 12.0)       │
        │       ],                   │
        │       'distance': 45m,     │
        │       'estimated_time': 90s│
        │       'capacity': 200      │
        │     }                      │
        │   ]                        │
        │                            │
        │ • alternate_routes: [...]  │
        │                            │
        │ • overload_warnings:       │
        │   "Exit_A at 90% capacity" │
        └────────────┬───────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 14: Alert Generation & Dashboard Update               │
│ Module: phase14_alerts.py                                  │
│                                                             │
│ Process:                                                    │
│ • Generate alert message                                   │
│ • Update real-time dashboard                               │
│ • Send notifications to authorities                        │
│ • Log event for analysis                                   │
│                                                             │
│ Alert Types:                                                │
│                                                             │
│ 🟢 Safe (Risk < 0.5):                                      │
│    "All zones normal. Crowd density: 2.3 people/m²"       │
│                                                             │
│ 🟡 Warning (Risk 0.5-0.75):                                │
│    "Warning: Increasing density at North Gate (4.2/m²)    │
│     Recommend: Monitor closely, prepare for crowd control" │
│                                                             │
│ 🔴 Critical (Risk ≥ 0.75):                                 │
│    "⚠️ CRITICAL ALERT ⚠️                                   │
│     Location: North Gate + Zone 3                          │
│     Density: 6.4 people/m² (DANGER)                        │
│     Surge predicted: 7.2 people/m² in 15 seconds           │
│     ACTION REQUIRED:                                        │
│     1. Close North Gate entrance immediately               │
│     2. Redirect crowd to South entrance                    │
│     3. Activate evacuation via Exit_A                      │
│     4. Deploy security to choke point (15.2m, 8.4m)"      │
│                                                             │
│ Dashboard Updates:                                          │
│ • Real-time count: 3,247 people                            │
│ • Risk heatmap visualization                               │
│ • Evacuation route overlay                                 │
│ • Timeline of events                                       │
│ • Video feed with annotations                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ FINAL OUTPUT               │
        ├────────────────────────────┤
        │ • Alert Message             │
        │ • Risk Score: 0.78          │
        │ • Status: CRITICAL 🚨       │
        │ • Actions: [3 steps]        │
        │                             │
        │ • Dashboard Data (JSON)     │
        │ • Video with overlays       │
        │ • PDF Report                │
        │ • Event log entry           │
        │                             │
        │ • Notifications sent to:    │
        │   - Control room            │
        │   - Security team           │
        │   - Emergency services      │
        └─────────────────────────────┘

```

---

## 📈 **Complete Pipeline Performance**

### **Processing Timeline (Single Frame):**

```
Frame arrives at t=0
    ↓
Step 1: Data acquisition         +1ms   → t=1ms
Step 2: Geo-referencing          +3ms   → t=4ms
Step 3: Preprocessing            +6ms   → t=10ms
Step 4: YOLO detection          +25ms   → t=35ms
Step 5: DeepSORT tracking       +15ms   → t=50ms
Step 6: Optical flow            +35ms   → t=85ms
Step 7: Choke point detection   +10ms   → t=95ms
Step 8: Feature engineering      +5ms   → t=100ms
Step 9: Anomaly detection        +2ms   → t=102ms
Step 10: LSTM prediction         +3ms   → t=105ms
Step 11: Risk propagation       +20ms   → t=125ms
Step 12: Risk fusion             +5ms   → t=130ms
Step 13: Evacuation planning    +15ms   → t=145ms
Step 14: Alert generation        +2ms   → t=147ms
    ↓
Alert displayed at t=147ms

Processing Speed: ~6-7 FPS
```

### **For 10-minute Video (9,000 frames):**
- Total processing time: **22-25 minutes**
- Acceptable for post-event analysis ✅

---

## 🔄 **Data Flow Summary Table**

| Step | Input | Process | Output | Time |
|------|-------|---------|--------|------|
| 1 | Video file | Load frames | Raw frames | 1ms |
| 2 | Raw frames | Geo-transform | Calibrated frames | 3ms |
| 3 | Calibrated frames | Preprocess | Clean frames | 6ms |
| 4 | Clean frames | YOLO detect | Bounding boxes | 25ms |
| 5 | Bounding boxes | Track IDs | Trajectories | 15ms |
| 6 | Trajectories | Optical flow | Motion vectors | 35ms |
| 7 | Motion + density | Analyze | Choke points | 10ms |
| 8 | All metrics | Engineer | Feature vector | 5ms |
| 9 | Features | Detect | Anomaly score | 2ms |
| 10 | Feature sequence | Predict | Surge forecast | 3ms |
| 11 | Risk data | Propagate | Risk heatmap | 20ms |
| 12 | All intelligence | Fuse | Risk score | 5ms |
| 13 | Risk zones | Plan | Evacuation routes | 15ms |
| 14 | Risk + routes | Generate | Alerts | 2ms |

**Total: ~147ms per frame = 6.8 FPS**

---

## 🎯 **Key Data Transformations**

```
Video (binary) 
    → Frames (pixels)
    → Preprocessed (normalized)
    → Detections (bounding boxes)
    → Tracks (IDs + trajectories)
    → Flow (motion vectors)
    → Features (statistics)
    → Risk (probability)
    → Actions (instructions)
```

---

## 🔍 **What Flows Between Phases:**

1. **Phase 1→2:** Raw pixel frames
2. **Phase 2→3:** Geo-referenced frames  
3. **Phase 3→4:** Clean, normalized frames
4. **Phase 4→5:** Person bounding boxes
5. **Phase 5→6:** Tracked trajectories with IDs
6. **Phase 6→7:** Motion velocity fields
7. **Phase 7→8:** Choke point locations + metrics
8. **Phase 8→9:** Aggregated feature vector
9. **Phase 9→10:** Anomaly scores + features
10. **Phase 10→11:** Predictions + current state
11. **Phase 11→12:** Risk heatmap
12. **Phase 12→13:** Final risk score + zones
13. **Phase 13→14:** Evacuation plans
14. **Phase 14→Output:** Alerts + visualization

---

## 💾 **Memory Usage Throughout Pipeline**

```
Phase 1: Raw frame              = 6 MB (1920×1080×3)
Phase 2: + Homography matrix    = 6 MB + 72 bytes
Phase 3: Preprocessed           = 1.2 MB (640×640×3)
Phase 4: + YOLO model           = 1.2 MB + 1.5 GB (GPU)
Phase 5: + DeepSORT             = + 0.5 GB tracks (GPU)
Phase 6: + Optical flow         = + 0.5 GB buffers (GPU)
Phase 7: + Grid analysis        = + 10 KB
Phase 8: + Features             = + 2 KB
Phase 9: + Anomaly model        = + 50 MB (CPU)
Phase 10: + LSTM model          = + 0.3 GB (GPU)
Phase 11: + Risk map            = + 10 KB
Phase 12: + Fusion data         = + 5 KB
Phase 13: + Graph               = + 100 KB
Phase 14: + Alert               = + 1 KB

Peak GPU VRAM: ~4.5 GB (fits in RTX 3050 6GB) ✅
Peak CPU RAM: ~500 MB
```

---

This workflow document shows exactly how data transforms through your PRAVAHA system from raw video to actionable alerts!
