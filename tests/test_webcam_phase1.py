"""
Test Phase 1 with Webcam
Test the video data acquisition system using your computer's webcam
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from phase1_data_acquisition import WebcamDataLoader
import cv2
import numpy as np


def test_webcam_live():
    """Test webcam with live display"""
    print("="*60)
    print("🎥 PRAVAHA - Phase 1 Webcam Test")
    print("="*60)
    print("\n📹 Starting webcam...")
    print("   Press 'q' to quit")
    print("   Press 's' to save current frame\n")
    
    try:
        with WebcamDataLoader(camera_id=0) as loader:
            frame_count = 0
            
            while True:
                success, frame, metadata = loader.read_frame()
                
                if not success:
                    print("❌ Failed to read frame")
                    break
                
                # Convert back to BGR for display
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Add info overlay
                info_text = f"Frame: {metadata['frame_id']} | Time: {metadata['timestamp']:.2f}s"
                cv2.putText(frame_bgr, info_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.putText(frame_bgr, "Press 'q' to quit", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Display
                cv2.imshow("PRAVAHA - Phase 1: Data Acquisition", frame_bgr)
                
                # Handle keys
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    print("\n✅ Quitting...")
                    break
                elif key == ord('s'):
                    filename = f"../data/output/webcam_frame_{frame_count}.jpg"
                    cv2.imwrite(filename, frame_bgr)
                    print(f"💾 Saved: {filename}")
                
                frame_count += 1
                
                # Print progress every 30 frames
                if frame_count % 30 == 0:
                    print(f"✓ Processed {frame_count} frames...")
            
            cv2.destroyAllWindows()
            
            print(f"\n✅ Test complete!")
            print(f"   Total frames: {frame_count}")
            print(f"   Duration: {frame_count/30:.1f} seconds")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        cv2.destroyAllWindows()


def test_webcam_batch():
    """Test webcam by capturing batch of frames"""
    print("="*60)
    print("🎥 PRAVAHA - Phase 1 Webcam Batch Test")
    print("="*60)
    
    try:
        with WebcamDataLoader(camera_id=0) as loader:
            print("\n📸 Capturing 100 frames...")
            
            frames_captured = []
            
            for i in range(100):
                success, frame, metadata = loader.read_frame()
                
                if not success:
                    print(f"❌ Failed at frame {i}")
                    break
                
                frames_captured.append((frame, metadata))
                
                if (i+1) % 10 == 0:
                    print(f"✓ Captured {i+1}/100 frames...")
            
            print(f"\n✅ Captured {len(frames_captured)} frames")
            
            # Analyze frames
            if frames_captured:
                frame, metadata = frames_captured[0]
                print(f"\n📊 Frame Analysis:")
                print(f"   Shape: {frame.shape}")
                print(f"   Type: {frame.dtype}")
                print(f"   Range: [{frame.min()}, {frame.max()}]")
                print(f"   FPS: {metadata['fps']}")
                
                # Calculate statistics
                mean_brightness = np.mean(frames_captured[0][0])
                print(f"   Mean brightness: {mean_brightness:.1f}")
            
            print(f"\n✅ Phase 1 webcam test successful!")
            print(f"   Ready to proceed to Phase 2 (Preprocessing)")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    print("\nSelect test mode:")
    print("1. Live webcam display (press 'q' to quit)")
    print("2. Batch capture (100 frames)")
    
    choice = input("\nEnter choice (1 or 2) [default: 1]: ").strip()
    
    if choice == "2":
        test_webcam_batch()
    else:
        test_webcam_live()
