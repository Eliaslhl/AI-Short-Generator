"""
highlight_detector.py – Advanced algorithm for detecting highlights in video segments.

Features analyzed:
- Audio (volume, spikes, intensity)
- Motion (frame changes, scene cuts)
- Transcription (keyword detection, sentiment)
- Context (silence penalties, calm moments)

Score formula:
    highlight_score = (0.5 * audio_score) + (0.2 * motion_score) + (0.3 * text_score)
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class HighlightSegment:
    """Represents a detected highlight segment."""
    start_time: float  # seconds
    end_time: float    # seconds
    score: float       # 0-100
    audio_score: float
    motion_score: float
    text_score: float
    reason: str        # Why this was detected


class AudioAnalyzer:
    """Analyzes audio for highlights."""
    
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate
    
    def extract_audio_features(
        self,
        audio_data: np.ndarray,
        frame_size: int = 2048,
    ) -> List[Dict]:
        """Extract audio features per frame."""
        features = []
        
        # Process audio in chunks
        for i in range(0, len(audio_data) - frame_size, frame_size // 2):
            frame = audio_data[i:i + frame_size]
            
            # Calculate RMS (volume)
            rms = np.sqrt(np.mean(frame ** 2))
            
            # Normalize to 0-1
            volume_normalized = min(rms / 0.1, 1.0)
            
            # Detect peaks (sudden changes)
            if i > 0:
                prev_frame = audio_data[i - frame_size // 2:i + frame_size // 2]
                prev_rms = np.sqrt(np.mean(prev_frame ** 2))
                spike = max(0, (rms - prev_rms) / (prev_rms + 1e-6))
            else:
                spike = 0.0
            
            features.append({
                "timestamp": i / self.sample_rate,
                "volume": volume_normalized,
                "spike": min(spike, 1.0),
            })
        
        return features
    
    def compute_audio_score(
        self,
        audio_features: List[Dict],
        window_start: float,
        window_end: float,
    ) -> float:
        """Compute audio score for a time window."""
        # Filter features in window
        window_features = [
            f for f in audio_features
            if window_start <= f["timestamp"] < window_end
        ]
        
        if not window_features:
            return 0.0
        
        # Average volume and spike
        avg_volume = np.mean([f["volume"] for f in window_features])
        avg_spike = np.mean([f["spike"] for f in window_features])
        
        # Score: weighted average
        audio_score = (0.6 * avg_volume) + (0.4 * avg_spike)
        
        return min(audio_score, 1.0)


class MotionAnalyzer:
    """Analyzes video motion for highlights."""
    
    def compute_motion_score(
        self,
        frame_diffs: List[float],
        window_idx: int,
        window_size: int = 10,
    ) -> float:
        """Compute motion score based on frame differences."""
        # Get frames in window
        start_idx = max(0, window_idx - window_size // 2)
        end_idx = min(len(frame_diffs), window_idx + window_size // 2)
        
        window_diffs = frame_diffs[start_idx:end_idx]
        
        if not window_diffs:
            return 0.0
        
        # Average frame difference (normalized 0-1)
        avg_diff = np.mean(window_diffs)
        motion_score = min(avg_diff, 1.0)
        
        return motion_score


class TextAnalyzer:
    """Analyzes transcription text for highlights."""
    
    # Keywords that indicate exciting moments
    EXCITEMENT_KEYWORDS = {
        "en": [
            "omg", "wow", "holy", "insane", "crazy", "amazing", "incredible",
            "no way", "what", "what the", "dude", "bro", "lol", "haha",
            "yes", "yeah", "hell yeah", "f*** yeah", "awesome", "sick",
            "clutch", "gg", "nice", "perfect", "legend", "beast", "pro",
        ],
        "fr": [
            "omg", "wow", "incroyable", "dingue", "fou", "magnifique",
            "pas possible", "quoi", "mec", "lol", "haha", "oui", "ouais",
            "génial", "trop bien", "top", "wahou", "top chrono", "bien joué",
        ],
        "es": [
            "omg", "wow", "increíble", "loco", "asombroso", "espectacular",
            "qué", "tío", "jaja", "sí", "siii", "brutal", "épico", "gg",
        ],
        "de": [
            "omg", "wow", "krass", "verrückt", "unglaublich", "fantastisch",
            "was", "mann", "lol", "ja", "cool", "großartig", "episch",
        ],
    }
    
    NEGATIVE_KEYWORDS = {
        "en": ["sorry", "oops", "fail", "mistake", "die", "death", "lost"],
        "fr": ["désolé", "oups", "fail", "erreur", "mort"],
        "es": ["perdón", "oops", "fail", "error", "muerte"],
        "de": ["sorry", "oops", "fehler"],
    }
    
    def compute_text_score(
        self,
        text: str,
        language: str = "en",
    ) -> Tuple[float, List[str]]:
        """
        Compute text score based on keywords and sentiment.
        
        Returns: (score, matched_keywords)
        """
        if not text or not isinstance(text, str):
            return 0.0, []
        
        text_lower = text.lower()
        matched_keywords = []
        
        # Default to English if language not found
        excitement_keys = self.EXCITEMENT_KEYWORDS.get(language, self.EXCITEMENT_KEYWORDS["en"])
        negative_keys = self.NEGATIVE_KEYWORDS.get(language, self.NEGATIVE_KEYWORDS["en"])
        
        # Count excitement keywords
        excitement_count = 0
        for keyword in excitement_keys:
            if keyword in text_lower:
                excitement_count += text_lower.count(keyword)
                matched_keywords.append(keyword)
        
        # Count negative keywords
        negative_count = 0
        for keyword in negative_keys:
            if keyword in text_lower:
                negative_count += text_lower.count(keyword)
        
        # Calculate text score
        # Normalize by text length to avoid long texts having inflated scores
        text_length = len(text.split())
        excitement_density = excitement_count / max(text_length, 1)
        negative_density = negative_count / max(text_length, 1)
        
        # Score: excitement bonus, negative penalty
        text_score = excitement_density * 0.7 - negative_density * 0.3
        text_score = max(0.0, min(text_score, 1.0))
        
        return text_score, matched_keywords


class HighlightDetector:
    """Main detector for highlights using multiple features."""
    
    def __init__(self, language: str = "en"):
        self.language = language
        self.audio_analyzer = AudioAnalyzer()
        self.motion_analyzer = MotionAnalyzer()
        self.text_analyzer = TextAnalyzer()
    
    def detect_highlights(
        self,
        audio_data: Optional[np.ndarray] = None,
        frame_diffs: Optional[List[float]] = None,
        transcription: Optional[str] = None,
        segment_duration: float = 60.0,
        window_size: float = 15.0,  # seconds, typical short clip
        overlap: float = 0.5,  # 50% overlap for sliding window
    ) -> List[HighlightSegment]:
        """
        Detect highlights in a segment.
        
        Args:
            audio_data: numpy array of audio samples
            frame_diffs: list of frame difference scores
            transcription: text transcription of audio
            segment_duration: total duration of segment in seconds
            window_size: duration of each analysis window in seconds
            overlap: overlap ratio for sliding window (0.5 = 50%)
        
        Returns:
            List of highlight segments sorted by score
        """
        highlights: List[HighlightSegment] = []
        
        # Extract features
        audio_features = []
        if audio_data is not None:
            audio_features = self.audio_analyzer.extract_audio_features(audio_data)
            logger.info(f"📊 Extracted audio features: {len(audio_features)} frames")
        
        # Sliding window analysis
        step_size = window_size * (1 - overlap)
        num_windows = int((segment_duration - window_size) / step_size) + 1
        
        logger.info(f"🔍 Analyzing {num_windows} windows (size={window_size}s, overlap={overlap})")
        
        for window_idx in range(num_windows):
            window_start = window_idx * step_size
            window_end = window_start + window_size
            
            # Skip if window exceeds segment
            if window_end > segment_duration:
                break
            
            # Compute scores
            audio_score = 0.0
            if audio_features:
                audio_score = self.audio_analyzer.compute_audio_score(
                    audio_features,
                    window_start,
                    window_end,
                )
            
            motion_score = 0.0
            if frame_diffs:
                frame_idx = int(window_start * 30)  # assuming 30 fps
                motion_score = self.motion_analyzer.compute_motion_score(
                    frame_diffs,
                    frame_idx,
                )
            
            text_score = 0.0
            reason = "Unknown"
            if transcription:
                # Extract text segment from transcription
                # Simple heuristic: use all text (more sophisticated in production)
                text_score, keywords = self.text_analyzer.compute_text_score(
                    transcription,
                    self.language,
                )
                if keywords:
                    reason = f"Keywords: {', '.join(keywords[:3])}"
            
            # Combined score
            final_score = (0.5 * audio_score) + (0.2 * motion_score) + (0.3 * text_score)
            final_score = min(final_score, 1.0)
            
            # Only include if score exceeds threshold
            if final_score > 0.3:  # 30% threshold
                highlight = HighlightSegment(
                    start_time=window_start,
                    end_time=window_end,
                    score=final_score * 100,  # Convert to 0-100 scale
                    audio_score=audio_score * 100,
                    motion_score=motion_score * 100,
                    text_score=text_score * 100,
                    reason=reason,
                )
                highlights.append(highlight)
        
        # Sort by score descending
        highlights.sort(key=lambda h: h.score, reverse=True)
        
        logger.info(f"✅ Detected {len(highlights)} highlights")
        return highlights
    
    def filter_and_merge_highlights(
        self,
        highlights: List[HighlightSegment],
        min_score: float = 40.0,  # Keep only top 40+ scores
        merge_threshold: float = 2.0,  # Merge segments within 2 seconds
    ) -> List[HighlightSegment]:
        """
        Filter low-score highlights and merge overlapping ones.
        
        Args:
            highlights: list of detected highlights
            min_score: minimum score to keep (0-100)
            merge_threshold: merge segments within this distance (seconds)
        
        Returns:
            Filtered and merged highlights
        """
        # Filter by score
        filtered = [h for h in highlights if h.score >= min_score]
        logger.info(f"🔽 Filtered to {len(filtered)} highlights (threshold={min_score})")
        
        if not filtered:
            return []
        
        # Sort by start time
        filtered.sort(key=lambda h: h.start_time)
        
        # Merge nearby segments
        merged = []
        for highlight in filtered:
            if merged and (highlight.start_time - merged[-1].end_time) < merge_threshold:
                # Merge: extend previous segment, take better score
                prev = merged[-1]
                merged[-1] = HighlightSegment(
                    start_time=prev.start_time,
                    end_time=max(prev.end_time, highlight.end_time),
                    score=max(prev.score, highlight.score),
                    audio_score=(prev.audio_score + highlight.audio_score) / 2,
                    motion_score=(prev.motion_score + highlight.motion_score) / 2,
                    text_score=(prev.text_score + highlight.text_score) / 2,
                    reason=f"{prev.reason} + {highlight.reason}",
                )
            else:
                merged.append(highlight)
        
        logger.info(f"🔗 Merged to {len(merged)} highlights")
        return merged
