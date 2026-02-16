"""
Phase 3: YOLOv8 Person Detection
Detects persons in preprocessed frames using YOLOv8n model

Input: Preprocessed frames from Phase 2 (640×640, normalized [0-1])
Output: Bounding boxes with confidence scores for detected persons
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import time
import os


class YOLODetector:
    """
    YOLOv8n-based person detector optimized for RTX 3050 6GB
    
    Features:
    - Lightweight YOLOv8n model (~6MB)
    - GPU acceleration (CUDA)
    - Person-only detection (class_id=0)
    - Confidence filtering
    """
    
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        confidence_threshold: float = 0.4,
        device: str = "cuda",
        verbose: bool = False
    ):
        """
        Initialize YOLO detector
        
        Args:
            model_path: Path to YOLOv8 model file (or model name for auto-download)
            confidence_threshold: Minimum confidence for detections (0.0-1.0)
            device: Device to run on ('cuda' or 'cpu')
            verbose: Print verbose model info
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.verbose = verbose
        
        # Load model
        self.model = None
        self._load_model()
        
        # Statistics
        self.frames_processed = 0
        self.total_detections = 0
        self.total_time = 0.0
    
    def _load_model(self):
        """Load YOLOv8 model"""
        try:
            from ultralytics import YOLO
            
            print(f"🔄 Loading YOLOv8 model: {self.model_path}")
            
            # Load model (auto-downloads if not found)
            self.model = YOLO(self.model_path)
            
            # Set device
            if self.device == "cuda":
                import torch
                if torch.cuda.is_available():
                    print(f"✓ Using GPU: {torch.cuda.get_device_name(0)}")
                else:
                    print("⚠️  CUDA not available, falling back to CPU")
                    self.device = "cpu"
            else:
                print("✓ Using CPU")
            
            print(f"✓ Model loaded successfully")
            
        except ImportError:
            raise ImportError(
                "ultralytics not installed. Install with: pip install ultralytics"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load YOLO model: {e}")
    
    def detect(
        self,
        frame: np.ndarray,
        return_crops: bool = False
    ) -> Tuple[List[Dict], np.ndarray]:
        """
        Detect persons in frame
        
        Args:
            frame: Preprocessed frame (640×640, 3 channels)
                   Can be normalized [0-1] or uint8 [0-255]
            return_crops: Whether to return cropped person images
            
        Returns:
            Tuple of (detections, annotated_frame)
            - detections: List of detection dicts with keys:
                * bbox: [x1, y1, x2, y2] in pixels
                * confidence: Detection confidence [0-1]
                * class_id: Always 0 (person)
                * class_name: Always 'person'
                * crop: Cropped image (optional, if return_crops=True)
            - annotated_frame: Frame with bounding boxes drawn (uint8 [0-255])
        """
        start_time = time.time()
        
        # Convert normalized frame to uint8 if needed
        if frame.dtype == np.float32 or frame.dtype == np.float64:
            frame_uint8 = (frame * 255).astype(np.uint8)
        else:
            frame_uint8 = frame
        
        # Run inference
        results = self.model.predict(
            frame_uint8,
            conf=self.confidence_threshold,
            classes=[0],  # Person class only
            device=self.device,
            verbose=self.verbose
        )
        
        # Parse results
        detections = []
        
        if len(results) > 0:
            result = results[0]  # First (and only) image
            
            if result.boxes is not None and len(result.boxes) > 0:
                boxes = result.boxes.xyxy.cpu().numpy()  # [x1, y1, x2, y2]
                confidences = result.boxes.conf.cpu().numpy()
                class_ids = result.boxes.cls.cpu().numpy()
                
                for i in range(len(boxes)):
                    detection = {
                        'bbox': boxes[i].tolist(),  # [x1, y1, x2, y2]
                        'confidence': float(confidences[i]),
                        'class_id': int(class_ids[i]),
                        'class_name': 'person'
                    }
                    
                    # Extract crop if requested
                    if return_crops:
                        x1, y1, x2, y2 = boxes[i].astype(int)
                        crop = frame_uint8[y1:y2, x1:x2]
                        detection['crop'] = crop
                    
                    detections.append(detection)
        
        # Get annotated frame
        annotated_frame = results[0].plot() if len(results) > 0 else frame_uint8
        
        # Update statistics
        detection_time = time.time() - start_time
        self.frames_processed += 1
        self.total_detections += len(detections)
        self.total_time += detection_time
        
        return detections, annotated_frame
    
    def get_stats(self) -> dict:
        """
        Get detection statistics
        
        Returns:
            Dict with performance statistics
        """
        avg_time = (self.total_time / self.frames_processed) if self.frames_processed > 0 else 0
        avg_detections = (self.total_detections / self.frames_processed) if self.frames_processed > 0 else 0
        
        return {
            'frames_processed': self.frames_processed,
            'total_detections': self.total_detections,
            'avg_detections_per_frame': avg_detections,
            'total_time_sec': self.total_time,
            'avg_time_sec': avg_time,
            'fps': 1.0 / avg_time if avg_time > 0 else 0
        }
    
    def reset_stats(self):
        """Reset statistics counters"""
        self.frames_processed = 0
        self.total_detections = 0
        self.total_time = 0.0


def test_yolo_detector():
    """Test YOLO detection pipeline"""
    import sys
    
    # Add parent directory to path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    from phase1_data_acquisition import VideoDataLoader
    from phase2_preprocessing import FramePreprocessor
    
    print("="*70)
    print("🎯 PRAVAHA - Phase 3: YOLOv8 Detection Test")
    print("="*70)
    
    # Check if video path provided
    if len(sys.argv) < 2:
        print("\n❌ Usage: python phase3_yolo_detection.py <video_path>")
        print("   Example: python phase3_yolo_detection.py ../data/input/crowd_video.mp4")
        return
    
    video_path = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(video_path):
        print(f"\n❌ Error: Video file not found: {video_path}")
        return
    
    print(f"\n📹 Loading video: {video_path}")
    
    try:
        # Initialize all phases
        loader = VideoDataLoader(video_path)
        preprocessor = FramePreprocessor(target_size=(640, 640), normalize=True)
        detector = YOLODetector(
            model_path="yolov8n.pt",
            confidence_threshold=0.4,
            device="cuda",
            verbose=False
        )
        
        print(f"✓ Video loaded: {loader.total_frames} frames")
        print(f"✓ All phases initialized")
        
        print("\n🔄 Processing frames...")
        print("   Processing first 30 frames for testing\n")
        
        frame_count = 0
        max_frames = 30
        
        # Create output directory for samples
        output_dir = "../data/output/phase3_samples"
        os.makedirs(output_dir, exist_ok=True)
        
        for raw_frame, _ in loader.frame_generator():
            if frame_count >= max_frames:
                break
            
            # Phase 2: Preprocess
            processed_frame, _ = preprocessor.process(raw_frame)
            
            # Phase 3: Detect
            detections, annotated_frame = detector.detect(processed_frame)
            
            # Print progress
            print(f"   Frame {frame_count + 1}/{max_frames} | "
                  f"Persons detected: {len(detections)}")
            
            # Save first 3 annotated frames
            if frame_count < 3:
                output_path = os.path.join(output_dir, f"frame_{frame_count:03d}_detected.jpg")
                cv2.imwrite(output_path, annotated_frame)
                print(f"      Saved: {output_path}")
            
            frame_count += 1
        
        # Get and display statistics
        preprocess_stats = preprocessor.get_stats()
        detection_stats = detector.get_stats()
        
        print("\n" + "="*70)
        print("📊 Phase 2 + 3 Statistics")
        print("="*70)
        
        print("\n🖼️  Phase 2 (Preprocessing):")
        print(f"   Frames processed:     {preprocess_stats['frames_processed']}")
        print(f"   Avg time/frame:       {preprocess_stats['avg_time_ms']:.2f} ms")
        print(f"   Processing FPS:       {preprocess_stats['fps']:.2f}")
        
        print("\n🎯 Phase 3 (Detection):")
        print(f"   Frames processed:     {detection_stats['frames_processed']}")
        print(f"   Total detections:     {detection_stats['total_detections']}")
        print(f"   Avg persons/frame:    {detection_stats['avg_detections_per_frame']:.1f}")
        print(f"   Avg time/frame:       {detection_stats['avg_time_sec']*1000:.2f} ms")
        print(f"   Detection FPS:        {detection_stats['fps']:.2f}")
        
        combined_time = (preprocess_stats['avg_time_ms']/1000) + detection_stats['avg_time_sec']
        combined_fps = 1.0 / combined_time if combined_time > 0 else 0
        
        print("\n⚡ Combined (Phase 2 + 3):")
        print(f"   Avg time/frame:       {combined_time*1000:.2f} ms")
        print(f"   Combined FPS:         {combined_fps:.2f}")
        
        print("="*70)
        
        print("\n✅ Phase 3 test complete!")
        print(f"   Sample frames saved to: {output_dir}/")
        print("   Ready to proceed to Phase 4 (DeepSORT Tracking)")
        
        loader.release()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_yolo_detector()
