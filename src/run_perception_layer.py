"""
PRAVAHA Perception Layer Pipeline
Runs Phases 1-4 (Data Acquisition → Preprocessing → Detection → Tracking)

Usage:
    python run_perception_layer.py <input_video> [options]

Example:
    python run_perception_layer.py ../data/input/crowd_video.mp4 --output ../data/output/result.mp4
"""

import cv2
import numpy as np
import sys
import os
import argparse
import time
from pathlib import Path

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from phase1_data_acquisition import VideoDataLoader
from phase2_preprocessing import FramePreprocessor
from phase3_yolo_detection import YOLODetector
from phase4_deepsort_tracking import DeepSORTTracker


def draw_tracks_on_frame(frame: np.ndarray, tracks: list, show_trajectory: bool = True) -> np.ndarray:
    """
    Draw tracking visualization on frame
    
    Args:
        frame: Input frame (RGB, uint8)
        tracks: List of track dicts from Phase 4
        show_trajectory: Whether to draw trajectory trails
        
    Returns:
        Annotated frame (BGR for video writing)
    """
    # Convert RGB to BGR for OpenCV
    vis_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    
    # Define colors for different tracks (cycle through)
    colors = [
        (0, 255, 0),    # Green
        (255, 0, 0),    # Blue
        (0, 0, 255),    # Red
        (255, 255, 0),  # Cyan
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Yellow
    ]
    
    for track in tracks:
        track_id = track['track_id']
        bbox = track['bbox']
        confidence = track['confidence']
        trajectory = track['trajectory']
        
        # Select color based on track ID
        color = colors[track_id % len(colors)]
        
        # Draw bounding box
        x1, y1, x2, y2 = [int(v) for v in bbox]
        cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, 2)
        
        # Draw track ID and info
        label = f"ID:{track_id} ({confidence:.2f})"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        
        # Background for text
        cv2.rectangle(vis_frame, 
                     (x1, y1 - label_size[1] - 5), 
                     (x1 + label_size[0], y1), 
                     color, -1)
        
        # Text
        cv2.putText(vis_frame, label, (x1, y1 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # Draw trajectory
        if show_trajectory and len(trajectory) > 1:
            for i in range(len(trajectory) - 1):
                pt1 = (int(trajectory[i][0]), int(trajectory[i][1]))
                pt2 = (int(trajectory[i+1][0]), int(trajectory[i+1][1]))
                cv2.line(vis_frame, pt1, pt2, color, 2)
            
            # Draw center point
            center = (int(trajectory[-1][0]), int(trajectory[-1][1]))
            cv2.circle(vis_frame, center, 3, color, -1)
    
    return vis_frame


def run_perception_pipeline(
    input_video: str,
    output_video: str = None,
    confidence_threshold: float = 0.4,
    max_tracks: int = 100,
    show_preview: bool = False,
    save_stats: bool = True,
    model_path: str = "yolov8n.pt"
):
    """
    Run complete perception layer pipeline (Phases 1-4)

    Args:
        input_video: Path to input video file
        output_video: Path to output video file (optional)
        confidence_threshold: YOLO confidence threshold
        max_tracks: Maximum number of simultaneous tracks
        show_preview: Show live preview window
        save_stats: Save statistics to file
        model_path: YOLOv8 model to use (yolov8n.pt, yolov8s.pt, yolov8m.pt, etc.)
    """
    
    print("="*70)
    print("🌊 PRAVAHA - Perception Layer Pipeline")
    print("="*70)
    print(f"\n📹 Input:  {input_video}")
    
    if output_video:
        print(f"📼 Output: {output_video}")
    
    # Check if input exists
    if not os.path.exists(input_video):
        print(f"\n❌ Error: Input video not found: {input_video}")
        return
    
    try:
        # Initialize all phases
        print("\n🔧 Initializing pipeline...")
        
        loader = VideoDataLoader(input_video)
        preprocessor = FramePreprocessor(target_size=(640, 640), normalize=True)
        detector = YOLODetector(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            device="cuda",
            verbose=False
        )
        tracker = DeepSORTTracker(
            max_iou_distance=0.5,
            max_age=30,
            n_init=3,
            max_tracks=max_tracks
        )
        
        print(f"✓ Phase 1: Data Acquisition")
        print(f"   - Frames: {loader.total_frames}")
        print(f"   - Resolution: {loader.width}×{loader.height}")
        print(f"   - FPS: {loader.fps}")
        print(f"✓ Phase 2: Preprocessing")
        print(f"✓ Phase 3: YOLO Detection (conf={confidence_threshold})")
        print(f"✓ Phase 4: DeepSORT Tracking (max_tracks={max_tracks})")
        
        # Setup output video writer
        video_writer = None
        if output_video:
            os.makedirs(os.path.dirname(output_video), exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(
                output_video,
                fourcc,
                loader.fps,
                (640, 640)  # Output size matches preprocessed size
            )
        
        # Process video
        print("\n🔄 Processing video...")
        print(f"   Total frames: {loader.total_frames}")
        print(f"   Estimated time: {loader.total_frames / 6:.1f}s @ 6 FPS\n")
        
        frame_count = 0
        start_time = time.time()
        
        for raw_frame, frame_metadata in loader.frame_generator():
            # Phase 2: Preprocess
            processed_frame, _ = preprocessor.process(raw_frame)
            
            # Phase 3: Detect
            detections, _ = detector.detect(processed_frame)
            
            # Phase 4: Track
            tracks = tracker.update(detections)
            
            # Visualize
            # Convert normalized frame back to uint8 for visualization
            if processed_frame.dtype == np.float32:
                vis_frame = (processed_frame * 255).astype(np.uint8)
            else:
                vis_frame = processed_frame
            
            annotated_frame = draw_tracks_on_frame(vis_frame, tracks, show_trajectory=True)
            
            # Add frame info overlay
            info_text = f"Frame: {frame_count+1}/{loader.total_frames} | Tracks: {len(tracks)}"
            cv2.putText(annotated_frame, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Write to output video
            if video_writer:
                video_writer.write(annotated_frame)
            
            # Show preview
            if show_preview:
                cv2.imshow("PRAVAHA - Perception Layer", annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\n⚠️  Preview stopped by user")
                    break
            
            # Print progress
            frame_count += 1
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                eta = (loader.total_frames - frame_count) / fps if fps > 0 else 0
                print(f"   Progress: {frame_count}/{loader.total_frames} "
                      f"({frame_count/loader.total_frames*100:.1f}%) | "
                      f"FPS: {fps:.2f} | "
                      f"ETA: {eta:.1f}s")
        
        # Cleanup
        if video_writer:
            video_writer.release()
        
        if show_preview:
            cv2.destroyAllWindows()
        
        loader.release()
        
        # Display statistics
        total_time = time.time() - start_time
        
        preprocess_stats = preprocessor.get_stats()
        detection_stats = detector.get_stats()
        tracking_stats = tracker.get_stats()
        
        print("\n" + "="*70)
        print("📊 Pipeline Statistics")
        print("="*70)
        
        print(f"\n⏱️  Overall Performance:")
        print(f"   Total frames:         {frame_count}")
        print(f"   Total time:           {total_time:.2f} seconds")
        print(f"   Average FPS:          {frame_count/total_time:.2f}")
        print(f"   Time per frame:       {total_time/frame_count*1000:.2f} ms")
        
        print(f"\n🖼️  Phase 2 (Preprocessing):")
        print(f"   Avg time/frame:       {preprocess_stats['avg_time_ms']:.2f} ms")
        
        print(f"\n🎯 Phase 3 (Detection):")
        print(f"   Total detections:     {detection_stats['total_detections']}")
        print(f"   Avg persons/frame:    {detection_stats['avg_detections_per_frame']:.1f}")
        print(f"   Avg time/frame:       {detection_stats['avg_time_sec']*1000:.2f} ms")
        
        print(f"\n🔍 Phase 4 (Tracking):")
        print(f"   Total tracks created: {tracking_stats['total_tracks_created']}")
        print(f"   Peak active tracks:   {tracking_stats['active_tracks_peak']}")
        print(f"   Avg time/frame:       {tracking_stats['avg_time_sec']*1000:.2f} ms")
        
        print("="*70)
        
        # Save statistics to file
        if save_stats:
            stats_file = output_video.replace('.mp4', '_stats.txt') if output_video else 'perception_stats.txt'
            with open(stats_file, 'w') as f:
                f.write("PRAVAHA Perception Layer Statistics\n")
                f.write("="*70 + "\n\n")
                f.write(f"Input Video: {input_video}\n")
                f.write(f"Output Video: {output_video}\n\n")
                f.write(f"Total frames: {frame_count}\n")
                f.write(f"Total time: {total_time:.2f} seconds\n")
                f.write(f"Average FPS: {frame_count/total_time:.2f}\n\n")
                f.write(f"Phase 2 avg time: {preprocess_stats['avg_time_ms']:.2f} ms\n")
                f.write(f"Phase 3 avg time: {detection_stats['avg_time_sec']*1000:.2f} ms\n")
                f.write(f"Phase 4 avg time: {tracking_stats['avg_time_sec']*1000:.2f} ms\n\n")
                f.write(f"Total detections: {detection_stats['total_detections']}\n")
                f.write(f"Total tracks created: {tracking_stats['total_tracks_created']}\n")
                f.write(f"Peak active tracks: {tracking_stats['active_tracks_peak']}\n")
            
            print(f"\n💾 Statistics saved to: {stats_file}")
        
        if output_video:
            print(f"\n✅ Output video saved to: {output_video}")
        
        print("\n✅ Perception Layer complete!")
        print("   Ready for Phase 5-8 (Prediction Layer - Motion & Density Analysis)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="PRAVAHA Perception Layer Pipeline (Phases 1-4)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "input",
        type=str,
        help="Input video file path"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output video file path (default: auto-generated in data/output/)"
    )
    
    parser.add_argument(
        "-c", "--confidence",
        type=float,
        default=0.4,
        help="YOLO confidence threshold (0.0-1.0)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n.pt",
        choices=["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"],
        help="YOLOv8 model size (n=nano, s=small, m=medium, l=large, x=xlarge)"
    )

    parser.add_argument(
        "-m", "--max-tracks",
        type=int,
        default=100,
        help="Maximum number of simultaneous tracks"
    )
    
    parser.add_argument(
        "-p", "--preview",
        action="store_true",
        help="Show live preview window (press 'q' to quit)"
    )
    
    parser.add_argument(
        "--no-stats",
        action="store_true",
        help="Don't save statistics file"
    )
    
    args = parser.parse_args()
    
    # Auto-generate output path if not provided
    if args.output is None:
        input_name = Path(args.input).stem
        args.output = f"../data/output/{input_name}_tracked.mp4"
    
    # Run pipeline
    run_perception_pipeline(
        input_video=args.input,
        output_video=args.output,
        confidence_threshold=args.confidence,
        max_tracks=args.max_tracks,
        show_preview=args.preview,
        save_stats=not args.no_stats,
        model_path=args.model
    )


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: python run_perception_layer.py <input_video> [options]")
        print("\nOptions:")
        print("  -o, --output <path>        Output video path")
        print("  -c, --confidence <float>   YOLO confidence threshold (default: 0.4)")
        print("  -m, --max-tracks <int>     Max simultaneous tracks (default: 100)")
        print("  -p, --preview              Show live preview")
        print("  --no-stats                 Don't save statistics file")
        print("\nExample:")
        print("  python run_perception_layer.py ../data/input/crowd_video.mp4")
        print("  python run_perception_layer.py video.mp4 -o output.mp4 -c 0.5 -p")
    else:
        main()
