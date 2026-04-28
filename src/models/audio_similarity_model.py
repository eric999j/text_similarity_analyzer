import librosa
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class AudioSimilarityModel:
    def __init__(self):
        self.sample_rate = 22050

    def load_audio(self, file_path):
        """Loads an audio file."""
        try:
            return librosa.load(file_path, sr=self.sample_rate)
        except Exception as e:
            print(f"Error loading audio {file_path}: {e}")
            return None, None

    def calculate_mfcc_similarity(self, file_path1, file_path2):
        """
        Calculates similarity based on Mel-frequency cepstral coefficients (MFCCs).
        Good for speech and timbre comparison.
        """
        y1, sr1 = self.load_audio(file_path1)
        y2, sr2 = self.load_audio(file_path2)

        if y1 is None or y2 is None:
            return 0.0

        # Extract MFCCs
        mfcc1 = librosa.feature.mfcc(y=y1, sr=sr1, n_mfcc=13)
        mfcc2 = librosa.feature.mfcc(y=y2, sr=sr2, n_mfcc=13)

        # Take the mean across time (feature aggregation) to handle different durations
        mfcc1_mean = np.mean(mfcc1, axis=1).reshape(1, -1)
        mfcc2_mean = np.mean(mfcc2, axis=1).reshape(1, -1)

        sim = cosine_similarity(mfcc1_mean, mfcc2_mean)[0][0]
        # Normalize from [-1, 1] to [0, 1] as MFCCs can be negative
        return (sim + 1) / 2

    def calculate_chroma_similarity(self, file_path1, file_path2):
        """
        Calculates similarity based on Chroma features.
        Good for music and harmonic content.
        """
        y1, sr1 = self.load_audio(file_path1)
        y2, sr2 = self.load_audio(file_path2)

        if y1 is None or y2 is None:
            return 0.0

        # Extract Chroma
        chroma1 = librosa.feature.chroma_stft(y=y1, sr=sr1)
        chroma2 = librosa.feature.chroma_stft(y=y2, sr=sr2)

        chroma1_mean = np.mean(chroma1, axis=1).reshape(1, -1)
        chroma2_mean = np.mean(chroma2, axis=1).reshape(1, -1)

        sim = cosine_similarity(chroma1_mean, chroma2_mean)[0][0]
        # Chroma features are positive, so cosine similarity is [0, 1]
        return sim

    def calculate_spectral_similarity(self, file_path1, file_path2):
        """
        Calculates similarity based on Spectral Contrast.
        Good for broad spectral characteristics.
        """
        y1, sr1 = self.load_audio(file_path1)
        y2, sr2 = self.load_audio(file_path2)

        if y1 is None or y2 is None:
            return 0.0

        contrast1 = librosa.feature.spectral_contrast(y=y1, sr=sr1)
        contrast2 = librosa.feature.spectral_contrast(y=y2, sr=sr2)

        contrast1_mean = np.mean(contrast1, axis=1).reshape(1, -1)
        contrast2_mean = np.mean(contrast2, axis=1).reshape(1, -1)

        sim = cosine_similarity(contrast1_mean, contrast2_mean)[0][0]
        # Spectral contrast is usually positive (dB differences), so cosine similarity is [0, 1]
        return sim
