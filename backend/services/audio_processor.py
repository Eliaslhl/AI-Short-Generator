"""
audio_processor.py – Real audio extraction and processing using _get_librosa().

Features:
- Extract audio from video files
- Compute RMS (volume) energy
- Detect spikes (sudden changes)
- Extract MFCC features (optional)
"""

import logging
import math
import subprocess
import numpy as np
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Lazy import: librosa is only loaded when actually needed
# This avoids startup failures if librosa is not installed
_librosa = None


def _source_has_audio_stream(file_path: str) -> Optional[bool]:
    """Return whether ffprobe can confirm an audio stream without decoding it."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=index",
                "-of",
                "csv=p=0",
                file_path,
            ],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return bool(result.stdout.strip())

def _get_librosa():
    """Lazy-load librosa on first use."""
    global _librosa
    if _librosa is None:
        try:
            import librosa
            _librosa = librosa
        except ImportError:
            logger.error(
                "librosa is not installed but is required for audio processing. "
                "Install with: pip install librosa"
            )
            raise RuntimeError(
                "Audio processing (librosa) not available. This feature is disabled "
                "if librosa was not in requirements.txt at build time."
            )
    return _librosa


class RealAudioProcessor:
    """Real audio processing using _get_librosa()."""
    
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate
    
    def load_audio_from_file(
        self,
        file_path: str,
        start_time: float = 0.0,
        duration: Optional[float] = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Load audio from a video or audio file.
        
        Args:
            file_path: Path to audio/video file
        
        Returns:
            (audio_data, sample_rate)
        """
        try:
            logger.info("Loading audio for highlight analysis")
            
            if not math.isfinite(start_time) or start_time < 0:
                raise ValueError("Audio start_time must be a finite non-negative number")
            if duration is not None and (
                not math.isfinite(duration) or duration <= 0
            ):
                raise ValueError("Audio duration must be a finite positive number")

            # librosa can load audio from video files too. ``offset`` and
            # ``duration`` keep Twitch analysis inside its logical chunk without
            # materializing an intermediate video file.
            audio, sr = _get_librosa().load(
                file_path,
                sr=self.sample_rate,
                mono=True,
                offset=start_time,
                duration=duration,
            )
            
            logger.info(f"✅ Loaded {len(audio)} samples at {sr} Hz")
            return audio, sr
        
        except Exception as e:
            # librosa/audioread reports a missing stream as NoBackendError. Do
            # not silently downgrade decoder failures: ffprobe must positively
            # confirm that this source has no audio stream.
            if (
                type(e).__name__ == "NoBackendError"
                and _source_has_audio_stream(file_path) is False
            ):
                logger.info("Source has no audio stream; continuing with motion analysis")
                return np.array([], dtype=np.float32), self.sample_rate
            logger.error("Audio loading failed: exception_type=%s", type(e).__name__)
            raise
    
    def compute_rms_energy(
        self,
        audio: np.ndarray,
        frame_length: int = 2048,
        hop_length: int = 512,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute RMS (volume) energy of audio.
        
        Args:
            audio: audio time series
            frame_length: length of frames
            hop_length: number of samples between frames
        
        Returns:
            (rms_energy, time_frames) where rms_energy is normalized to 0-1
        """
        try:
            logger.info("🔊 Computing RMS energy...")
            
            # Compute RMS energy using librosa
            S = _get_librosa().feature.melspectrogram(y=audio, sr=self.sample_rate)
            rms_energy = _get_librosa().feature.rms(S=S)[0]
            
            # Convert frame indices to time
            times = _get_librosa().frames_to_time(np.arange(len(rms_energy)), sr=self.sample_rate)
            
            # Normalize to 0-1
            rms_normalized = rms_energy / (np.max(rms_energy) + 1e-6)
            
            logger.info(f"✅ Computed {len(rms_energy)} RMS frames")
            return rms_normalized, times
        
        except Exception as e:
            logger.error(f"❌ Failed to compute RMS: {e}")
            raise
    
    def detect_spikes(
        self,
        rms_energy: np.ndarray,
        threshold_percentile: float = 75.0,
        window_size: int = 5,
    ) -> np.ndarray:
        """
        Detect sudden changes (spikes) in audio energy.
        
        Args:
            rms_energy: normalized RMS energy (0-1)
            threshold_percentile: percentile for spike detection
            window_size: size of moving window for diff
        
        Returns:
            spike_scores (0-1) for each frame
        """
        try:
            logger.info("📈 Detecting spikes...")
            
            # Compute differences between frames
            diffs = np.abs(np.diff(rms_energy, prepend=rms_energy[0]))
            
            # Normalize differences
            spike_threshold = np.percentile(diffs, threshold_percentile)
            spikes = np.clip(diffs / (spike_threshold + 1e-6), 0, 1.0)
            
            # Smooth spikes with moving average
            spikes_smoothed = np.convolve(spikes, np.ones(window_size) / window_size, mode='same')
            
            logger.info(f"✅ Detected spikes: max={np.max(spikes_smoothed):.2f}, mean={np.mean(spikes_smoothed):.2f}")
            return spikes_smoothed
        
        except Exception as e:
            logger.error(f"❌ Failed to detect spikes: {e}")
            raise
    
    def extract_mfcc_features(
        self,
        audio: np.ndarray,
        n_mfcc: int = 13,
    ) -> np.ndarray:
        """
        Extract MFCC (Mel-Frequency Cepstral Coefficient) features.
        
        Useful for distinguishing speech, music, silence.
        
        Args:
            audio: audio time series
            n_mfcc: number of MFCCs to extract
        
        Returns:
            MFCC matrix (n_mfcc x n_frames)
        """
        try:
            logger.info("🎼 Extracting MFCC features...")
            
            mfcc = _get_librosa().feature.mfcc(y=audio, sr=self.sample_rate, n_mfcc=n_mfcc)
            
            logger.info(f"✅ Extracted MFCC: shape={mfcc.shape}")
            return mfcc
        
        except Exception as e:
            logger.error(f"❌ Failed to extract MFCC: {e}")
            raise
    
    def extract_spectral_features(
        self,
        audio: np.ndarray,
    ) -> dict:
        """
        Extract spectral features for audio analysis.
        
        Args:
            audio: audio time series
        
        Returns:
            dict with spectral features
        """
        try:
            logger.info("🎵 Extracting spectral features...")
            
            # Compute spectrogram
            D = _get_librosa().stft(audio)
            magnitude = np.abs(D)
            
            # Spectral centroid (brightness)
            spectral_centroid = _get_librosa().feature.spectral_centroid(y=audio, sr=self.sample_rate)[0]
            
            # Spectral rolloff (where most energy is below)
            spectral_rolloff = _get_librosa().feature.spectral_rolloff(y=audio, sr=self.sample_rate)[0]
            
            # Zero crossing rate (noisiness)
            zcr = _get_librosa().feature.zero_crossing_rate(audio)[0]
            
            logger.info("✅ Extracted spectral features")
            
            return {
                "spectral_centroid": spectral_centroid,
                "spectral_rolloff": spectral_rolloff,
                "zero_crossing_rate": zcr,
                "magnitude": magnitude,
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to extract spectral features: {e}")
            raise


def process_audio_for_highlight_detection(
    file_path: str,
    sample_rate: int = 22050,
    start_time: float = 0.0,
    duration: Optional[float] = None,
) -> dict:
    """
    Complete audio processing pipeline for highlight detection.
    
    Args:
        file_path: path to audio/video file
        sample_rate: target sample rate
        start_time: start of the analysis window in the source, in seconds
        duration: optional analysis-window duration in seconds
    
    Returns:
        dict with all audio features
    """
    processor = RealAudioProcessor(sample_rate=sample_rate)
    
    try:
        # Load audio
        audio, sr = processor.load_audio_from_file(
            file_path,
            start_time=start_time,
            duration=duration,
        )

        # A video without an audio stream is valid for motion-only detection.
        if audio.size == 0:
            return {
                "audio": audio,
                "sample_rate": sr,
                "rms_energy": np.array([]),
                "times": np.array([]),
                "spikes": np.array([]),
                "mfcc": np.array([]),
                "spectral": {},
            }
        
        # Compute RMS energy
        rms_energy, times = processor.compute_rms_energy(audio)
        
        # Detect spikes
        spikes = processor.detect_spikes(rms_energy)
        
        # Extract MFCC
        mfcc = processor.extract_mfcc_features(audio)
        
        # Extract spectral features
        spectral = processor.extract_spectral_features(audio)
        
        logger.info("✅ Audio processing complete!")
        
        return {
            "audio": audio,
            "sample_rate": sr,
            "rms_energy": rms_energy,
            "times": times,
            "spikes": spikes,
            "mfcc": mfcc,
            "spectral": spectral,
        }
    
    except Exception as e:
        logger.error("Audio processing failed: exception_type=%s", type(e).__name__)
        raise
