"""
audio_processor.py – Real audio extraction and processing using librosa.

Features:
- Extract audio from video files
- Compute RMS (volume) energy
- Detect spikes (sudden changes)
- Extract MFCC features (optional)
"""

import logging
import numpy as np
from typing import Tuple, Optional
import librosa

logger = logging.getLogger(__name__)


class RealAudioProcessor:
    """Real audio processing using librosa."""
    
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate
    
    def load_audio_from_file(self, file_path: str) -> Tuple[np.ndarray, int]:
        """
        Load audio from a video or audio file.
        
        Args:
            file_path: Path to audio/video file
        
        Returns:
            (audio_data, sample_rate)
        """
        try:
            logger.info(f"🎵 Loading audio from: {file_path}")
            
            # librosa can load audio from video files too
            audio, sr = librosa.load(file_path, sr=self.sample_rate, mono=True)
            
            logger.info(f"✅ Loaded {len(audio)} samples at {sr} Hz")
            return audio, sr
        
        except Exception as e:
            logger.error(f"❌ Failed to load audio: {e}")
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
            S = librosa.feature.melspectrogram(y=audio, sr=self.sample_rate)
            rms_energy = librosa.feature.rms(S=S)[0]
            
            # Convert frame indices to time
            times = librosa.frames_to_time(np.arange(len(rms_energy)), sr=self.sample_rate)
            
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
            
            mfcc = librosa.feature.mfcc(y=audio, sr=self.sample_rate, n_mfcc=n_mfcc)
            
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
            D = librosa.stft(audio)
            magnitude = np.abs(D)
            
            # Spectral centroid (brightness)
            spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=self.sample_rate)[0]
            
            # Spectral rolloff (where most energy is below)
            spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=self.sample_rate)[0]
            
            # Zero crossing rate (noisiness)
            zcr = librosa.feature.zero_crossing_rate(audio)[0]
            
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
) -> dict:
    """
    Complete audio processing pipeline for highlight detection.
    
    Args:
        file_path: path to audio/video file
        sample_rate: target sample rate
    
    Returns:
        dict with all audio features
    """
    processor = RealAudioProcessor(sample_rate=sample_rate)
    
    try:
        # Load audio
        audio, sr = processor.load_audio_from_file(file_path)
        
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
        logger.error(f"❌ Audio processing failed: {e}")
        raise
