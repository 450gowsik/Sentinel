"""
Phase 4: DeepSORT Multi-Object Tracking
Tracks detected persons across frames using DeepSORT algorithm

Input: Detections from Phase 3 (bounding boxes with confidence)
Output: Tracked objects with unique IDs and trajectory history

DeepSORT Components:
1. Kalman Filter: Predicts object motion
2. Hungarian Algorithm: Associates detections with tracks
3. ReID Features: Appearance-based matching
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import time
import os


class Track:
    """
    Represents a single tracked object
    
    Attributes:
        track_id: Unique identifier for this track
        bbox: Current bounding box [x1, y1, x2, y2]
        confidence: Detection confidence
        history: List of historical bounding boxes
        age: Number of frames this track has existed
        hits: Number of consecutive detections
        time_since_update: Frames since last detection
    """
    
    def __init__(self, track_id: int, bbox: List[float], confidence: float):
        self.track_id = track_id
        self.bbox = bbox
        self.confidence = confidence
        self.history = [bbox]
        self.age = 0
        self.hits = 1
        self.time_since_update = 0
        self.state = 'tentative'  # tentative, confirmed, deleted
    
    def update(self, bbox: List[float], confidence: float):
        """Update track with new detection"""
        self.bbox = bbox
        self.confidence = confidence
        self.history.append(bbox)
        self.hits += 1
        self.time_since_update = 0
        
        # Confirm track after 3 consecutive hits
        if self.hits >= 3:
            self.state = 'confirmed'
    
    def predict(self):
        """Predict next position using simple linear motion"""
        self.age += 1
        self.time_since_update += 1
        
        # Simple prediction: use last known position
        # (Real DeepSORT uses Kalman Filter here)
        if len(self.history) >= 2:
            # Linear extrapolation
            prev_bbox = self.history[-2]
            curr_bbox = self.history[-1]
            
            dx = curr_bbox[0] - prev_bbox[0]
            dy = curr_bbox[1] - prev_bbox[1]
            
            predicted_bbox = [
                curr_bbox[0] + dx,
                curr_bbox[1] + dy,
                curr_bbox[2] + dx,
                curr_bbox[3] + dy
            ]
            self.bbox = predicted_bbox
    
    def mark_missed(self):
        """Mark track as missed (no detection matched)"""
        self.time_since_update += 1
        
        # Delete track if missed for too long
        if self.time_since_update > 30:  # 30 frames = 1 second at 30fps
            self.state = 'deleted'
    
    def get_center(self) -> Tuple[float, float]:
        """Get center point of bounding box"""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    def get_trajectory(self, max_points: int = 30) -> List[Tuple[float, float]]:
        """Get recent trajectory points"""
        trajectory = []
        for bbox in self.history[-max_points:]:
            x1, y1, x2, y2 = bbox
            center = ((x1 + x2) / 2, (y1 + y2) / 2)
            trajectory.append(center)
        return trajectory


class DeepSORTTracker:
    """
    Simplified DeepSORT tracker optimized for crowd scenarios
    
    Features:
    - Track initialization and deletion
    - Simple motion prediction (linear)
    - IoU-based matching (simplified from full DeepSORT)
    - Trajectory history maintenance
    
    Note: This is a simplified version. Full DeepSORT uses:
    - Kalman Filter for motion prediction
    - Hungarian Algorithm for optimal matching
    - Deep features for appearance matching
    """
    
    def __init__(
        self,
        max_iou_distance: float = 0.5,
        max_age: int = 30,
        n_init: int = 3,
        max_tracks: int = 100
    ):
        """
        Initialize tracker
        
        Args:
            max_iou_distance: Maximum IoU distance for matching (0-1)
            max_age: Maximum frames to keep alive without detections
            n_init: Number of consecutive detections before confirming track
            max_tracks: Maximum number of simultaneous tracks (RTX 3050 limit)
        """
        self.max_iou_distance = max_iou_distance
        self.max_age = max_age
        self.n_init = n_init
        self.max_tracks = max_tracks
        
        self.tracks = []
        self.next_id = 1
        
        # Statistics
        self.frames_processed = 0
        self.total_tracks_created = 0
        self.active_tracks_peak = 0
        self.total_time = 0.0
    
    def _compute_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """
        Compute Intersection over Union (IoU) between two bounding boxes
        
        Args:
            bbox1: [x1, y1, x2, y2]
            bbox2: [x1, y1, x2, y2]
            
        Returns:
            IoU score (0-1)
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Intersection area
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Union area
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _match_detections_to_tracks(
        self,
        detections: List[Dict],
        tracks: List[Track]
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """
        Match detections to existing tracks using IoU
        
        Returns:
            Tuple of (matches, unmatched_detections, unmatched_tracks)
            - matches: List of (detection_idx, track_idx) pairs
            - unmatched_detections: List of detection indices
            - unmatched_tracks: List of track indices
        """
        if len(tracks) == 0:
            return [], list(range(len(detections))), []
        
        if len(detections) == 0:
            return [], [], list(range(len(tracks)))
        
        # Compute IoU matrix
        iou_matrix = np.zeros((len(detections), len(tracks)))
        for d_idx, det in enumerate(detections):
            for t_idx, track in enumerate(tracks):
                iou_matrix[d_idx, t_idx] = self._compute_iou(det['bbox'], track.bbox)
        
        # Simple greedy matching (full DeepSORT uses Hungarian Algorithm)
        matches = []
        unmatched_detections = list(range(len(detections)))
        unmatched_tracks = list(range(len(tracks)))
        
        # Match highest IoU pairs first
        while True:
            if len(unmatched_detections) == 0 or len(unmatched_tracks) == 0:
                break
            
            # Find best match
            max_iou = 0
            best_det = -1
            best_track = -1
            
            for d_idx in unmatched_detections:
                for t_idx in unmatched_tracks:
                    if iou_matrix[d_idx, t_idx] > max_iou:
                        max_iou = iou_matrix[d_idx, t_idx]
                        best_det = d_idx
                        best_track = t_idx
            
            # Check if match is good enough
            if max_iou < (1.0 - self.max_iou_distance):
                break
            
            # Add match
            matches.append((best_det, best_track))
            unmatched_detections.remove(best_det)
            unmatched_tracks.remove(best_track)
        
        return matches, unmatched_detections, unmatched_tracks
    
    def update(self, detections: List[Dict]) -> List[Dict]:
        """
        Update tracks with new detections
        
        Args:
            detections: List of detection dicts from Phase 3
                       Each dict has: bbox, confidence, class_id, class_name
        
        Returns:
            List of track dicts with keys:
                - track_id: Unique track identifier
                - bbox: Current bounding box [x1, y1, x2, y2]
                - confidence: Detection confidence
                - trajectory: Recent trajectory points
                - age: Frames since track creation
                - state: 'tentative', 'confirmed', or 'deleted'
        """
        start_time = time.time()
        
        # Predict new locations for existing tracks
        for track in self.tracks:
            track.predict()
        
        # Match detections to tracks
        matches, unmatched_detections, unmatched_tracks = \
            self._match_detections_to_tracks(detections, self.tracks)
        
        # Update matched tracks
        for det_idx, track_idx in matches:
            self.tracks[track_idx].update(
                detections[det_idx]['bbox'],
                detections[det_idx]['confidence']
            )
        
        # Mark unmatched tracks as missed
        for track_idx in unmatched_tracks:
            self.tracks[track_idx].mark_missed()
        
        # Create new tracks for unmatched detections
        for det_idx in unmatched_detections:
            if len(self.tracks) < self.max_tracks:
                new_track = Track(
                    self.next_id,
                    detections[det_idx]['bbox'],
                    detections[det_idx]['confidence']
                )
                self.tracks.append(new_track)
                self.next_id += 1
                self.total_tracks_created += 1
        
        # Remove deleted tracks
        self.tracks = [t for t in self.tracks if t.state != 'deleted']
        
        # Update statistics
        self.frames_processed += 1
        self.active_tracks_peak = max(self.active_tracks_peak, len(self.tracks))
        self.total_time += (time.time() - start_time)
        
        # Return confirmed tracks only
        output_tracks = []
        for track in self.tracks:
            if track.state == 'confirmed':
                output_tracks.append({
                    'track_id': track.track_id,
                    'bbox': track.bbox,
                    'confidence': track.confidence,
                    'trajectory': track.get_trajectory(),
                    'age': track.age,
                    'state': track.state
                })
        
        return output_tracks
    
    def get_stats(self) -> dict:
        """Get tracking statistics"""
        avg_time = (self.total_time / self.frames_processed) if self.frames_processed > 0 else 0
        
        return {
            'frames_processed': self.frames_processed,
            'total_tracks_created': self.total_tracks_created,
            'active_tracks_current': len(self.tracks),
            'active_tracks_peak': self.active_tracks_peak,
            'total_time_sec': self.total_time,
            'avg_time_sec': avg_time,
            'fps': 1.0 / avg_time if avg_time > 0 else 0
        }
    
    def reset(self):
        """Reset tracker (clear all tracks)"""
        self.tracks = []
        self.next_id = 1
    
    def reset_stats(self):
        """Reset statistics"""
        self.frames_processed = 0
        self.total_tracks_created = 0
        self.active_tracks_peak = 0
        self.total_time = 0.0


def test_deepsort_tracker():
    """Test DeepSORT tracking pipeline"""
    import sys
    import cv2
    
    # Add parent directory to path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    from phase1_data_acquisition import VideoDataLoader
    from phase2_preprocessing import FramePreprocessor
    from phase3_yolo_detection import YOLODetector
    
    print("="*70)
    print("🔍 PRAVAHA - Phase 4: DeepSORT Tracking Test")
    print("="*70)
    
    # Check if video path provided
    if len(sys.argv) < 2:
        print("\n❌ Usage: python phase4_deepsort_tracking.py <video_path>")
        print("   Example: python phase4_deepsort_tracking.py ../data/input/crowd_video.mp4")
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
        detector = YOLODetector(model_path="yolov8n.pt", confidence_threshold=0.4, device="cuda", verbose=False)
        tracker = DeepSORTTracker(max_iou_distance=0.5, max_age=30, n_init=3, max_tracks=100)
        
        print(f"✓ Video loaded: {loader.total_frames} frames")
        print(f"✓ All phases initialized (1-4)")
        
        print("\n🔄 Processing frames...")
        print("   Processing first 50 frames for testing\n")
        
        frame_count = 0
        max_frames = 50
        
        # Create output directory
        output_dir = "../data/output/phase4_samples"
        os.makedirs(output_dir, exist_ok=True)
        
        for raw_frame, _ in loader.frame_generator():
            if frame_count >= max_frames:
                break
            
            # Phase 2: Preprocess
            processed_frame, _ = preprocessor.process(raw_frame)
            
            # Phase 3: Detect
            detections, _ = detector.detect(processed_frame)
            
            # Phase 4: Track
            tracks = tracker.update(detections)
            
            # Print progress
            print(f"   Frame {frame_count + 1}/{max_frames} | "
                  f"Detections: {len(detections)} | "
                  f"Tracks: {len(tracks)}")
            
            # Draw tracks on frame for visualization
            if frame_count < 3:
                # Convert to BGR for visualization
                if processed_frame.dtype == np.float32:
                    vis_frame = (processed_frame * 255).astype(np.uint8)
                else:
                    vis_frame = processed_frame.copy()
                
                vis_frame = cv2.cvtColor(vis_frame, cv2.COLOR_RGB2BGR)
                
                # Draw tracks
                for track in tracks:
                    bbox = track['bbox']
                    track_id = track['track_id']
                    
                    x1, y1, x2, y2 = [int(v) for v in bbox]
                    
                    # Draw bounding box
                    cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Draw track ID
                    cv2.putText(vis_frame, f"ID: {track_id}", (x1, y1-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                    # Draw trajectory
                    trajectory = track['trajectory']
                    for i in range(len(trajectory) - 1):
                        pt1 = (int(trajectory[i][0]), int(trajectory[i][1]))
                        pt2 = (int(trajectory[i+1][0]), int(trajectory[i+1][1]))
                        cv2.line(vis_frame, pt1, pt2, (255, 0, 0), 2)
                
                output_path = os.path.join(output_dir, f"frame_{frame_count:03d}_tracked.jpg")
                cv2.imwrite(output_path, vis_frame)
                print(f"      Saved: {output_path}")
            
            frame_count += 1
        
        # Get and display statistics
        preprocess_stats = preprocessor.get_stats()
        detection_stats = detector.get_stats()
        tracking_stats = tracker.get_stats()
        
        print("\n" + "="*70)
        print("📊 Phase 2 + 3 + 4 Statistics")
        print("="*70)
        
        print("\n🖼️  Phase 2 (Preprocessing):")
        print(f"   Avg time/frame:       {preprocess_stats['avg_time_ms']:.2f} ms")
        
        print("\n🎯 Phase 3 (Detection):")
        print(f"   Total detections:     {detection_stats['total_detections']}")
        print(f"   Avg persons/frame:    {detection_stats['avg_detections_per_frame']:.1f}")
        print(f"   Avg time/frame:       {detection_stats['avg_time_sec']*1000:.2f} ms")
        
        print("\n🔍 Phase 4 (Tracking):")
        print(f"   Total tracks created: {tracking_stats['total_tracks_created']}")
        print(f"   Active tracks (peak): {tracking_stats['active_tracks_peak']}")
        print(f"   Active tracks (now):  {tracking_stats['active_tracks_current']}")
        print(f"   Avg time/frame:       {tracking_stats['avg_time_sec']*1000:.2f} ms")
        
        combined_time = (
            preprocess_stats['avg_time_ms']/1000 +
            detection_stats['avg_time_sec'] +
            tracking_stats['avg_time_sec']
        )
        combined_fps = 1.0 / combined_time if combined_time > 0 else 0
        
        print("\n⚡ Combined (Phase 2 + 3 + 4):")
        print(f"   Avg time/frame:       {combined_time*1000:.2f} ms")
        print(f"   Combined FPS:         {combined_fps:.2f}")
        
        print("="*70)
        
        print("\n✅ Phase 4 test complete!")
        print(f"   Sample frames saved to: {output_dir}/")
        print("   Perception Layer (Phases 2-4) fully functional!")
        print("\n📌 Next: Phase 5-8 (Prediction Layer - Motion & Density Analysis)")
        
        loader.release()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_deepsort_tracker()
