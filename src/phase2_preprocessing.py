"""
Phase 2: Frame Preprocessing
Prepares raw frames for YOLO detection by resizing, denoising, enhancing contrast, and normalizing

Input: Raw RGB frames from Phase 1 (variable size, [0-255] range)
Output: Preprocessed frames (640×640, normalized [0-1] range)
"""

import cv2
import numpy as np
from typing import Tuple, Optional
import time


class FramePreprocessor:
    """
    Preprocesses frames for optimal YOLO detection performance
    
    Operations:
    1. Resize to 640×640 (YOLO input size)
    2. Gaussian blur (denoise)
    3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    4. Normalize to [0, 1] range
    """
    
    def __init__(
        self,
        target_size: Tuple[int, int] = (640, 640),
        blur_kernel: Tuple[int, int] = (5, 5),
        clahe_clip_limit: float = 2.0,
        clahe_tile_size: Tuple[int, int] = (8, 8),
        normalize: bool = True
    ):
        """
        Initialize preprocessor with configuration
        
        Args:
            target_size: Output frame size (width, height). Default: (640, 640)
            blur_kernel: Gaussian blur kernel size. Default: (5, 5)
            clahe_clip_limit: CLAHE clip limit. Default: 2.0
            clahe_tile_size: CLAHE tile grid size. Default: (8, 8)
            normalize: Whether to normalize to [0, 1]. Default: True
        """
        self.target_size = target_size
        self.blur_kernel = blur_kernel
        self.normalize = normalize
        
        # Create CLAHE object for contrast enhancement
        self.clahe = cv2.createCLAHE(
            clipLimit=clahe_clip_limit,
            tileGridSize=clahe_tile_size
        )
        
        # Statistics
        self.frames_processed = 0
        self.total_time = 0.0
    
    def resize(self, frame: np.ndarray) -> np.ndarray:
        """
        Resize frame to target size with aspect ratio preservation
        
        Args:
            frame: Input frame (H, W, 3)
            
        Returns:
            Resized frame (target_size[1], target_size[0], 3)
        """
        # Use INTER_LINEAR for good quality and speed balance
        return cv2.resize(frame, self.target_size, interpolation=cv2.INTER_LINEAR)
    
    def denoise(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply Gaussian blur to reduce noise
        
        Args:
            frame: Input frame (H, W, 3)
            
        Returns:
            Denoised frame
        """
        return cv2.GaussianBlur(frame, self.blur_kernel, 0)
    
    def enhance_contrast(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        Enhances contrast while preventing over-amplification in uniform regions
        
        Args:
            frame: Input frame (H, W, 3) in RGB
            
        Returns:
            Contrast-enhanced frame in RGB
        """
        # Convert RGB to LAB color space (better for contrast enhancement)
        lab = cv2.cvtColor(frame, cv2.COLOR_RGB2LAB)
        
        # Apply CLAHE to L channel only (luminance)
        lab[:, :, 0] = self.clahe.apply(lab[:, :, 0])
        
        # Convert back to RGB
        return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    
    def normalize_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Normalize frame to [0, 1] range
        
        Args:
            frame: Input frame with values in [0, 255]
            
        Returns:
            Normalized frame with values in [0.0, 1.0]
        """
        return frame.astype(np.float32) / 255.0
    
    def process(self, frame: np.ndarray) -> Tuple[np.ndarray, dict]:
        """
        Apply full preprocessing pipeline
        
        Pipeline:
        1. Resize to target size
        2. Denoise with Gaussian blur
        3. Enhance contrast with CLAHE
        4. Normalize to [0, 1] (optional)
        
        Args:
            frame: Raw input frame from Phase 1 (H, W, 3) in RGB, [0-255]
            
        Returns:
            Tuple of (preprocessed_frame, metadata)
            - preprocessed_frame: Processed frame ready for YOLO
            - metadata: Dict with preprocessing info
        """
        start_time = time.time()
        
        # Store original dimensions
        original_shape = frame.shape
        
        # 1. Resize
        frame = self.resize(frame)
        
        # 2. Denoise
        frame = self.denoise(frame)
        
        # 3. Enhance contrast
        frame = self.enhance_contrast(frame)
        
        # 4. Normalize (optional)
        if self.normalize:
            frame = self.normalize_frame(frame)
            value_range = (0.0, 1.0)
        else:
            value_range = (0, 255)
        
        # Update statistics
        processing_time = time.time() - start_time
        self.frames_processed += 1
        self.total_time += processing_time
        
        # Create metadata
        metadata = {
            'original_shape': original_shape,
            'processed_shape': frame.shape,
            'normalized': self.normalize,
            'value_range': value_range,
            'processing_time_ms': processing_time * 1000,
            'frame_number': self.frames_processed
        }
        
        return frame, metadata
    
    def get_stats(self) -> dict:
        """
        Get preprocessing statistics
        
        Returns:
            Dict with performance statistics
        """
        avg_time = (self.total_time / self.frames_processed * 1000) if self.frames_processed > 0 else 0
        
        return {
            'frames_processed': self.frames_processed,
            'total_time_sec': self.total_time,
            'avg_time_ms': avg_time,
            'fps': 1.0 / (self.total_time / self.frames_processed) if self.frames_processed > 0 else 0
        }
    
    def reset_stats(self):
        """Reset statistics counters"""
        self.frames_processed = 0
        self.total_time = 0.0


def test_preprocessor():
    """Test the preprocessing pipeline"""
    import sys
    import os
    
    # Add parent directory to path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    from phase1_data_acquisition import VideoDataLoader
    
    print("="*70)
    print("🖼️  PRAVAHA - Phase 2: Frame Preprocessing Test")
    print("="*70)
    
    # Check if video path provided
    if len(sys.argv) < 2:
        print("\n❌ Usage: python phase2_preprocessing.py <video_path>")
        print("   Example: python phase2_preprocessing.py ../data/input/crowd_video.mp4")
        return
    
    video_path = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(video_path):
        print(f"\n❌ Error: Video file not found: {video_path}")
        return
    
    print(f"\n📹 Loading video: {video_path}")
    
    try:
        # Initialize Phase 1 (data loader) and Phase 2 (preprocessor)
        loader = VideoDataLoader(video_path)
        preprocessor = FramePreprocessor(
            target_size=(640, 640),
            blur_kernel=(5, 5),
            clahe_clip_limit=2.0,
            normalize=True
        )
        
        print(f"✓ Video loaded: {loader.total_frames} frames")
        print(f"✓ Resolution: {loader.width}×{loader.height}")
        print(f"✓ FPS: {loader.fps}")
        
        print("\n🔄 Processing frames...")
        print("   Processing first 30 frames for testing\n")
        
        frame_count = 0
        max_frames = 30
        
        for raw_frame, frame_metadata in loader.frame_generator():
            if frame_count >= max_frames:
                break
            
            # Preprocess frame
            processed_frame, preprocess_metadata = preprocessor.process(raw_frame)
            
            # Print progress every 10 frames
            if (frame_count + 1) % 10 == 0:
                print(f"   Frame {frame_count + 1}/{max_frames} | "
                      f"Time: {preprocess_metadata['processing_time_ms']:.1f}ms | "
                      f"Shape: {preprocess_metadata['processed_shape']}")
            
            frame_count += 1
        
        # Get and display statistics
        stats = preprocessor.get_stats()
        
        print("\n" + "="*70)
        print("📊 Preprocessing Statistics")
        print("="*70)
        print(f"Frames processed:     {stats['frames_processed']}")
        print(f"Total time:           {stats['total_time_sec']:.2f} seconds")
        print(f"Average time/frame:   {stats['avg_time_ms']:.2f} ms")
        print(f"Processing FPS:       {stats['fps']:.2f}")
        print("="*70)
        
        # Display sample frame info
        print("\n🎯 Sample Frame Info:")
        print(f"   Original: {preprocess_metadata['original_shape']} in range [0, 255]")
        print(f"   Processed: {preprocess_metadata['processed_shape']} in range {preprocess_metadata['value_range']}")
        print(f"   Normalized: {preprocess_metadata['normalized']}")
        
        print("\n✅ Phase 2 test complete!")
        print("   Ready to proceed to Phase 3 (YOLO Detection)")
        
        loader.release()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_preprocessor()
