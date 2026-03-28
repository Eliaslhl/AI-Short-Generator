"""
motion_processor.py – Real motion detection using frame analysis.

Features:
- Extract frames from video
- Compute optical flow
- Detect scene changes
- Calculate motion intensity
"""

import logging
import numpy as np
from typing import Tuple, List, Optional
import cv2

logger = logging.getLogger(__name__)


class MotionProcessor:
    """Real motion processing using OpenCV."""
    
    def __init__(self, fps: int = 30):
        self.fps = fps
    
    def load_video_frames(
        self,
        file_path: str,
        max_frames: Optional[int] = None,
        skip_frames: int = 1,
    ) -> Tuple[List[np.ndarray], int, Tuple[int, int]]:
        """
        Load video frames from file.
        
        Args:
            file_path: path to video file
            max_frames: maximum frames to load (None = all)
            skip_frames: skip every N frames (for performance)
        
        Returns:
            (frames, fps, (height, width))
        """
        try:
            logger.info(f"🎬 Loading video from: {file_path}")
            
            cap = cv2.VideoCapture(file_path)
            
            if not cap.isOpened():
                raise ValueError("Cannot open video file")
            
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            
            logger.info(f"📹 Video: {width}x{height} @ {fps} fps, {total_frames} frames")
            
            frames = []
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Skip frames for performance
                if frame_count % skip_frames == 0:
                    # Convert to grayscale for faster processing
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    frames.append(gray)
                    
                    if max_frames and len(frames) >= max_frames:
                        break
                
                frame_count += 1
            
            cap.release()
            
            logger.info(f"✅ Loaded {len(frames)} frames")
            return frames, fps, (height, width)
        
        except Exception as e:
            logger.error(f"❌ Failed to load video: {e}")
            raise
    
    def compute_frame_differences(
        self,
        frames: List[np.ndarray],
        resize_to: Optional[Tuple[int, int]] = (320, 180),
    ) -> np.ndarray:
        """
        Compute frame-to-frame differences (optical flow magnitude).
        
        Args:
            frames: list of grayscale frames
            resize_to: resize frames for faster computation
        
        Returns:
            array of motion scores (0-1) per frame
        """
        try:
            logger.info(f"🔍 Computing frame differences for {len(frames)} frames...")
            
            motion_scores = np.zeros(len(frames))
            
            for i in range(1, len(frames)):
                frame1 = frames[i-1]
                frame2 = frames[i]
                
                # Resize for faster computation
                if resize_to:
                    frame1 = cv2.resize(frame1, resize_to)
                    frame2 = cv2.resize(frame2, resize_to)
                
                # Compute absolute difference
                diff = cv2.absdiff(frame1, frame2)
                
                # Motion score = mean difference normalized to 0-1
                motion_score = np.mean(diff) / 255.0
                motion_scores[i] = motion_score
            
            # Normalize to 0-1 scale
            max_score = np.max(motion_scores)
            if max_score > 0:
                motion_scores = motion_scores / max_score
            
            logger.info(f"✅ Computed motion scores: min={np.min(motion_scores):.3f}, max={np.max(motion_scores):.3f}, mean={np.mean(motion_scores):.3f}")
            
            return motion_scores
        
        except Exception as e:
            logger.error(f"❌ Failed to compute frame differences: {e}")
            raise
    
    def detect_scene_changes(
        self,
        frames: List[np.ndarray],
        threshold: float = 30.0,
        resize_to: Optional[Tuple[int, int]] = (320, 180),
    ) -> np.ndarray:
        """
        Detect scene cuts (large differences between consecutive frames).
        
        Args:
            frames: list of grayscale frames
            threshold: threshold for detecting scene changes
            resize_to: resize frames for computation
        
        Returns:
            binary array (1 = scene change, 0 = no change)
        """
        try:
            logger.info(f"🎬 Detecting scene changes (threshold={threshold})...")
            
            scene_changes = np.zeros(len(frames))
            
            for i in range(1, len(frames)):
                frame1 = frames[i-1]
                frame2 = frames[i]
                
                # Resize for faster computation
                if resize_to:
                    frame1 = cv2.resize(frame1, resize_to)
                    frame2 = cv2.resize(frame2, resize_to)
                
                # Compute histogram difference
                hist1 = cv2.calcHist([frame1], [0], None, [256], [0, 256])
                hist2 = cv2.calcHist([frame2], [0], None, [256], [0, 256])
                
                # Normalize histograms
                cv2.normalize(hist1, hist1, alpha=1, beta=0, norm_type=cv2.NORM_MINMAX)
                cv2.normalize(hist2, hist2, alpha=1, beta=0, norm_type=cv2.NORM_MINMAX)
                
                # Compare histograms
                diff = cv2.compareHist(hist1, hist2, cv2.HISTCMP_BHATTACHARYYA)
                
                if diff > threshold / 100.0:
                    scene_changes[i] = 1.0
            
            scene_cut_count = np.sum(scene_changes)
            logger.info(f"✅ Detected {int(scene_cut_count)} scene changes")
            
            return scene_changes
        
        except Exception as e:
            logger.error(f"❌ Failed to detect scene changes: {e}")
            raise
    
    def compute_optical_flow(
        self,
        frames: List[np.ndarray],
        max_frames: Optional[int] = None,
    ) -> np.ndarray:
        """
        Compute optical flow (motion vectors) between consecutive frames.
        
        Args:
            frames: list of grayscale frames
            max_frames: max frames to process (for large videos)
        
        Returns:
            array of motion magnitudes (0-1) per frame
        """
        try:
            logger.info("🌪️ Computing optical flow...")
            
            frames_to_process = frames if max_frames is None else frames[:max_frames]
            motion_magnitudes = np.zeros(len(frames_to_process))
            
            prev_gray = frames_to_process[0]
            
            for i in range(1, len(frames_to_process)):
                curr_gray = frames_to_process[i]
                
                # Compute optical flow using Farneback algorithm
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, curr_gray,
                    None,  # flow
                    0.5,   # pyr_scale
                    3,     # levels
                    15,    # winsize
                    3,     # iterations
                    5,     # poly_n
                    1.2,   # poly_sigma
                    0      # flags
                )
                
                # Compute magnitude
                mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                motion_magnitudes[i] = np.mean(mag)
                
                prev_gray = curr_gray
            
            # Normalize to 0-1
            max_mag = np.max(motion_magnitudes)
            if max_mag > 0:
                motion_magnitudes = motion_magnitudes / max_mag
            
            logger.info(f"✅ Optical flow computed: max={np.max(motion_magnitudes):.3f}, mean={np.mean(motion_magnitudes):.3f}")
            
            return motion_magnitudes
        
        except Exception as e:
            logger.error(f"❌ Failed to compute optical flow: {e}")
            raise


def process_video_for_motion_detection(
    file_path: str,
    fps: int = 30,
    max_frames: Optional[int] = None,
) -> dict:
    """
    Complete video processing pipeline for motion detection.
    
    Args:
        file_path: path to video file
        fps: frames per second
        max_frames: maximum frames to process
    
    Returns:
        dict with all motion features
    """
    processor = MotionProcessor(fps=fps)
    
    try:
        # Load frames
        frames, actual_fps, (height, width) = processor.load_video_frames(
            file_path,
            max_frames=max_frames,
            skip_frames=2  # Skip every 2nd frame for speed
        )
        
        # Compute frame differences
        frame_diffs = processor.compute_frame_differences(frames)
        
        # Detect scene changes
        scene_changes = processor.detect_scene_changes(frames)
        
        # Compute optical flow (optional, slower)
        # optical_flow = processor.compute_optical_flow(frames, max_frames=100)
        
        logger.info("✅ Video motion processing complete!")
        
        return {
            "frames": frames,
            "fps": actual_fps,
            "dimensions": (height, width),
            "frame_differences": frame_diffs,
            "scene_changes": scene_changes,
            # "optical_flow": optical_flow,
        }
    
    except Exception as e:
        logger.error(f"❌ Video processing failed: {e}")
        raise
