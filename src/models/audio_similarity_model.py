import os
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from math import gcd

import librosa
import numpy as np
from scipy.signal import resample_poly


class AudioAnalysisError(RuntimeError):
    pass


class AudioSimilarityModel:
    def __init__(self):
        self.sample_rate = 22050
        self._audio_cache = OrderedDict()
        self._audio_cache_maxsize = 8
        self._feature_cache = OrderedDict()
        self._feature_cache_maxsize = 8
        self._executor = ThreadPoolExecutor(max_workers=2)

    def _cosine_similarity(self, vec1, vec2):
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def _format_error_message(self, exc):
        message = str(exc).strip()
        if not message:
            return "未知錯誤 (Unknown error)"
        return message.splitlines()[0]

    def _validate_feature_vector(self, vector, feature_name, file_path):
        if vector.size == 0:
            raise AudioAnalysisError(f"{feature_name} 特徵為空，無法分析: {os.path.basename(file_path)}")
        if not np.all(np.isfinite(vector)):
            raise AudioAnalysisError(f"{feature_name} 特徵包含無效數值: {os.path.basename(file_path)}")
        if np.linalg.norm(vector) == 0.0:
            raise AudioAnalysisError(
                f"{feature_name} 無法取得有效特徵，音訊可能過短、近乎靜音或缺少該方法需要的訊號: {os.path.basename(file_path)}"
            )

    def _evict_if_needed(self, cache_obj, maxsize):
        while len(cache_obj) > maxsize:
            cache_obj.popitem(last=False)

    def _get_file_signature(self, file_path):
        try:
            stat = os.stat(file_path)
            return stat.st_mtime_ns, stat.st_size
        except OSError:
            return None, None

    def _is_same_audio_source(self, file_path1, file_path2):
        try:
            return os.path.samefile(file_path1, file_path2)
        except (OSError, ValueError):
            return False

    def _load_audio_with_fallback(self, file_path):
        # Load at native sample rate to avoid resampy dependency entirely.
        # Any backend (soundfile/audioread) can decode without resampling.
        y, orig_sr = librosa.load(file_path, sr=None, mono=True, dtype=np.float32)
        if orig_sr != self.sample_rate:
            g = gcd(orig_sr, self.sample_rate)
            y = resample_poly(y, self.sample_rate // g, orig_sr // g).astype(np.float32)
        return y, self.sample_rate

    def _get_audio_cached(self, file_path):
        signature = self._get_file_signature(file_path)
        cached = self._audio_cache.get(file_path)
        if cached and cached[0] == signature:
            self._audio_cache.move_to_end(file_path)
            return signature, cached[1], cached[2]

        try:
            y, sr = self._load_audio_with_fallback(file_path)
        except Exception as exc:
            raise AudioAnalysisError(f"無法讀取音訊檔案 {os.path.basename(file_path)}: {self._format_error_message(exc)}") from exc

        if y is None or y.size == 0:
            raise AudioAnalysisError(f"音訊檔案沒有可分析的資料: {os.path.basename(file_path)}")

        self._audio_cache[file_path] = (signature, y, sr)
        self._audio_cache.move_to_end(file_path)
        self._evict_if_needed(self._audio_cache, self._audio_cache_maxsize)
        return signature, y, sr

    def _extract_feature_vector(self, y, sr, feature_name):
        if feature_name == "mfcc":
            return np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13), axis=1)
        if feature_name == "chroma":
            return np.mean(librosa.feature.chroma_stft(y=y, sr=sr), axis=1)
        if feature_name == "spectral":
            return np.mean(librosa.feature.spectral_contrast(y=y, sr=sr), axis=1)
        raise ValueError(f"Unsupported feature: {feature_name}")

    def _get_feature_cached(self, file_path, feature_name):
        signature, y, sr = self._get_audio_cached(file_path)
        cached = self._feature_cache.get(file_path)
        if cached and cached[0] == signature:
            self._feature_cache.move_to_end(file_path)
            feature_map = cached[1]
        else:
            feature_map = {}

        if feature_name not in feature_map:
            try:
                feature_vector = self._extract_feature_vector(y, sr, feature_name)
            except Exception as exc:
                raise AudioAnalysisError(
                    f"{feature_name.upper()} 特徵擷取失敗，檔案 {os.path.basename(file_path)}: {self._format_error_message(exc)}"
                ) from exc
            self._validate_feature_vector(feature_vector, feature_name.upper(), file_path)
            feature_map[feature_name] = feature_vector

        self._feature_cache[file_path] = (signature, feature_map)
        self._feature_cache.move_to_end(file_path)
        self._evict_if_needed(self._feature_cache, self._feature_cache_maxsize)
        return feature_map[feature_name]

    def _get_feature_pair(self, file_path1, file_path2, feature_name):
        if file_path1 == file_path2:
            features = self._get_feature_cached(file_path1, feature_name)
            return features, features
        future1 = self._executor.submit(self._get_feature_cached, file_path1, feature_name)
        future2 = self._executor.submit(self._get_feature_cached, file_path2, feature_name)
        return future1.result(), future2.result()

    def load_audio(self, file_path):
        """Loads an audio file."""
        try:
            _, y, sr = self._get_audio_cached(file_path)
            return y, sr
        except AudioAnalysisError:
            raise
        except Exception as e:
            print(f"Error loading audio {file_path}: {e}")
            return None, None

    def calculate_mfcc_similarity(self, file_path1, file_path2):
        """
        Calculates similarity based on Mel-frequency cepstral coefficients (MFCCs).
        Good for speech and timbre comparison.
        """
        if self._is_same_audio_source(file_path1, file_path2):
            return 1.0
        feature1, feature2 = self._get_feature_pair(file_path1, file_path2, "mfcc")
        sim = self._cosine_similarity(feature1, feature2)
        return (sim + 1) / 2

    def calculate_chroma_similarity(self, file_path1, file_path2):
        """
        Calculates similarity based on Chroma features.
        Good for music and harmonic content.
        """
        if self._is_same_audio_source(file_path1, file_path2):
            return 1.0
        feature1, feature2 = self._get_feature_pair(file_path1, file_path2, "chroma")
        return self._cosine_similarity(feature1, feature2)

    def calculate_spectral_similarity(self, file_path1, file_path2):
        """
        Calculates similarity based on Spectral Contrast.
        Good for broad spectral characteristics.
        """
        if self._is_same_audio_source(file_path1, file_path2):
            return 1.0
        feature1, feature2 = self._get_feature_pair(file_path1, file_path2, "spectral")
        return self._cosine_similarity(feature1, feature2)
