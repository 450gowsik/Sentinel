"""
PRAVAHA - Phase 1: Multi-Modal Data Acquisition
===============================================
Purpose: Load and read video files frame by frame with metadata
This is the foundation that feeds all other phases of the system.

Author: PRAVAHA Team
Date: February 2026
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Generator
import time


class VideoDataLoader:
    """
    Handles loading video files (CCTV, Drone footage) and
    provides frame-by-frame access with metadata
    
    This is the INPUT LAYER of the PRAVAHA system.
    """
    
    def __init__(self, video_path: str):
        """
        Initialize video loader
        
        Args:
            video_path: Path to video file (MP4, AVI, MOV, etc.)
            
        Raises:
            FileNotFoundError: If video file doesn't exist
            ValueError: If video cannot be opened
        """
        self.video_path = Path(video_path)
        
        if not self.video_path.exists():
            raise FileNotFoundError(f"❌ Video file not found: {video_path}")
        
        # Open video capture
        self.cap = cv2.VideoCapture(str(video_path))
        
        if not self.cap.isOpened():
            raise ValueError(f"❌ Cannot open video file: {video_path}")
        
        # Extract video metadata
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0
        
        self.current_frame = 0
        
        print(f"✅ Video loaded: {self.video_path.name}")
        print(f"   Resolution: {self.width}x{self.height}")
        print(f"   FPS: {self.fps:.2f}")
        print(f"   Duration: {self.duration:.2f} seconds")
        print(f"   Total Frames: {self.total_frames}")
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], dict]:
        """
        Read next frame from video
        
        Returns:
            success (bool): Whether frame was read successfully
            frame (np.ndarray): RGB frame image (H, W, 3)
            metadata (dict): Frame metadata (timestamp, frame_id, etc.)
            
        Example:
            >>> loader = VideoDataLoader("crowd.mp4")
            >>> success, frame, metadata = loader.read_frame()
            >>> if success:
            >>>     print(f"Frame {metadata['frame_id']} at {metadata['timestamp']:.2f}s")
        """
        ret, frame = self.cap.read()
        
        if not ret:
            return False, None, {}
        
        # Convert BGR (OpenCV default) to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Calculate timestamp
        timestamp = self.current_frame / self.fps if self.fps > 0 else 0
        
        # Create metadata
        metadata = {
            'frame_id': self.current_frame,
            'timestamp': timestamp,
            'fps': self.fps,
            'resolution': (self.width, self.height),
            'source': self.video_path.name
        }
        
        self.current_frame += 1
        
        return True, frame_rgb, metadata
    
    def frame_generator(self) -> Generator[Tuple[np.ndarray, dict], None, None]:
        """
        Generator that yields frames one by one
        Useful for processing entire video
        
        Usage:
            >>> loader = VideoDataLoader("crowd.mp4")
            >>> for frame, metadata in loader.frame_generator():
            >>>     # Process frame
            >>>     print(f"Processing frame {metadata['frame_id']}")
        """
        while True:
            success, frame, metadata = self.read_frame()
            
            if not success:
                break
            
            yield frame, metadata
    
    def get_info(self) -> dict:
        """
        Get video information
        
        Returns:
            dict: Video properties (path, fps, resolution, duration, etc.)
        """
        return {
            'path': str(self.video_path),
            'filename': self.video_path.name,
            'fps': self.fps,
            'total_frames': self.total_frames,
            'width': self.width,
            'height': self.height,
            'duration': self.duration,
            'current_frame': self.current_frame,
            'progress': f"{(self.current_frame/self.total_frames*100):.1f}%" if self.total_frames > 0 else "0%"
        }
    
    def seek(self, frame_number: int) -> bool:
        """
        Jump to specific frame number
        
        Args:
            frame_number: Target frame (0-indexed)
        
        Returns:
            bool: Success status
        """
        if 0 <= frame_number < self.total_frames:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            self.current_frame = frame_number
            return True
        return False
    
    def reset(self):
        """Reset to beginning of video"""
        self.seek(0)
    
    def release(self):
        """Release video capture resources"""
        if self.cap:
            self.cap.release()
            print(f"✅ Released video: {self.video_path.name}")
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.release()
    
    def __del__(self):
        """Destructor"""
        self.release()


class WebcamDataLoader:
    """
    Real-time webcam capture (for testing/demo)
    Useful when you don't have recorded video
    """
    
    def __init__(self, camera_id: int = 0):
        """
        Initialize webcam
        
        Args:
            camera_id: Camera device ID (usually 0 for default webcam)
        """
        self.cap = cv2.VideoCapture(camera_id)
        
        if not self.cap.isOpened():
            raise ValueError(f"❌ Cannot open webcam with ID: {camera_id}")
        
        self.fps = 30  # Typical webcam FPS
        self.frame_count = 0
        
        print(f"✅ Webcam initialized (Camera ID: {camera_id})")
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], dict]:
        """Read frame from webcam"""
        ret, frame = self.cap.read()
        
        if not ret:
            return False, None, {}
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        metadata = {
            'frame_id': self.frame_count,
            'timestamp': self.frame_count / self.fps,
            'fps': self.fps,
            'source': 'webcam'
        }
        
        self.frame_count += 1
        
        return True, frame_rgb, metadata
    
    def release(self):
        """Release webcam"""
        if self.cap:
            self.cap.release()
            print("✅ Webcam released")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def test_video_loader(video_path: str, num_frames: int = 10):
    """
    Test video loader with sample video
    
    Args:
        video_path: Path to test video
        num_frames: Number of frames to process and display
    """
    print("\n" + "="*60)
    print("🎬 PHASE 1 TEST: Video Data Acquisition")
    print("="*60 + "\n")
    
    try:
        # Load video
        with VideoDataLoader(video_path) as loader:
            # Display video info
            info = loader.get_info()
            print("\n📊 Video Information:")
            for key, value in info.items():
                print(f"   {key}: {value}")
            
            print(f"\n🎬 Reading first {num_frames} frames...\n")
            
            # Read and process frames
            start_time = time.time()
            for i in range(num_frames):
                success, frame, metadata = loader.read_frame()
                
                if not success:
                    print(f"⚠️  End of video reached at frame {i}")
                    break
                
                # Display frame info
                print(f"✓ Frame {metadata['frame_id']:4d} | "
                      f"Time: {metadata['timestamp']:6.2f}s | "
                      f"Shape: {frame.shape} | "
                      f"Type: {frame.dtype} | "
                      f"Range: [{frame.min()}-{frame.max()}]")
            
            elapsed = time.time() - start_time
            fps_processed = (i+1) / elapsed if elapsed > 0 else 0
            
            print(f"\n✅ Phase 1 Complete!")
            print(f"   Processed: {i+1} frames")
            print(f"   Time: {elapsed:.2f}s")
            print(f"   Processing Speed: {fps_processed:.1f} FPS")
            print(f"\n📌 These frames are ready for Phase 2 (Preprocessing)")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    print("="*60)
    print("🛡 PRAVAHA - Crowd Management System")
    print("Phase 1: Multi-Modal Data Acquisition")
    print("="*60)
    
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        print("\n📝 Usage:")
        print("  python phase1_data_acquisition.py <video_path>")
        print("\n📌 Example:")
        print("  python phase1_data_acquisition.py ../data/input/crowd_video.mp4")
        print("\n💡 Or test with webcam:")
        print("  python ../tests/test_webcam_phase1.py")
        sys.exit(1)
    
    # Test with video file
    success = test_video_loader(video_path, num_frames=30)
    
    if success:
        print("\n" + "="*60)
        print("✅ Phase 1 is working! Ready to build Phase 2.")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ Phase 1 failed. Check the video file path.")
        print("="*60)
        sys.exit(1)
