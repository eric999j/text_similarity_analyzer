import math
from collections import Counter

import jieba
import Levenshtein
import numpy as np


class SimilarityModel:
    STOPWORDS = {
        "的", "是", "在", "有", "和", "就", "不", "人", "都", "一", "一個", "上", "也", "很", "到", "說", "要", "去", "你", "會", "著", "沒有", "看", "好", "自己", "這",
        "我", "他", "她", "它", "們", "被", "把", "等", "與", "或", "但", "因為", "所以", "如果", "那麼",
        "the", "a", "an", "in", "on", "of", "is", "are", "was", "were", "to", "for", "with", "by", "at", "from", "it", "this", "that",
        "and", "or", "but", "if", "then", "be", "have", "do", "can", "will", "would", "should", "could"
    }

    def __init__(self):
        pass

    def _get_tokens(self, text, remove_stopwords):
        """Helper to tokenize text with optional stopword filtering."""
        if not text:
            return []

        tokens = []
        for raw in jieba.cut(text):
            token = raw.strip()
            if not token:
                continue
            if remove_stopwords and token in self.STOPWORDS:
                continue
            tokens.append(token)
        return tokens

    def _get_token_counter(self, text, remove_stopwords):
        return Counter(self._get_tokens(text, remove_stopwords))

    def _counter_cosine_similarity(self, counter_a, counter_b):
        if not counter_a or not counter_b:
            return 0.0

        if len(counter_a) <= len(counter_b):
            dot_product = sum(value * counter_b.get(token, 0) for token, value in counter_a.items())
        else:
            dot_product = sum(value * counter_a.get(token, 0) for token, value in counter_b.items())

        norm_a = math.sqrt(sum(value * value for value in counter_a.values()))
        norm_b = math.sqrt(sum(value * value for value in counter_b.values()))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def _sorted_counter_cosine_similarity(self, counter_a, counter_b, union_size=None):
        if not counter_a or not counter_b:
            return 0.0

        if union_size is None:
            union_size = len(set(counter_a.keys()).union(counter_b.keys()))

        if union_size == 0:
            return 0.0

        a_sorted = np.sort(np.fromiter(counter_a.values(), dtype=np.float64))
        b_sorted = np.sort(np.fromiter(counter_b.values(), dtype=np.float64))

        if a_sorted.size < union_size:
            a_sorted = np.pad(a_sorted, (union_size - a_sorted.size, 0))
        if b_sorted.size < union_size:
            b_sorted = np.pad(b_sorted, (union_size - b_sorted.size, 0))

        norm_a = np.linalg.norm(a_sorted)
        norm_b = np.linalg.norm(b_sorted)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return float(np.dot(a_sorted, b_sorted) / (norm_a * norm_b))

    def _levenshtein_similarity_strings(self, text1, text2):
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0

        distance = Levenshtein.distance(text1, text2)
        max_len = max(len(text1), len(text2))
        if max_len == 0:
            return 1.0
        return 1 - (distance / max_len)

    def _get_word_set(self, text, remove_stopwords):
        return set(self._get_tokens(text, remove_stopwords))

    def calculate_jaccard_similarity(self, text1, text2, remove_stopwords=False):
        """
        Jaccard Similarity = |A ∩ B| / |A ∪ B|
        """
        words1 = self._get_word_set(text1, remove_stopwords)
        words2 = self._get_word_set(text2, remove_stopwords)

        if not words1 or not words2:
            return 0.0

        union = len(words1.union(words2))
        if union == 0:
            return 0.0

        intersection = len(words1.intersection(words2))
        return intersection / union

    def calculate_levenshtein_similarity(self, text1, text2, remove_stopwords=False):
        """
        Levenshtein Similarity = 1 - (distance / max_len)
        If remove_stopwords is True, stopwords are removed from the original text before calculation.
        """
        if not text1 or not text2:
            return 0.0

        if remove_stopwords:
            text1 = "".join(self._get_tokens(text1, True))
            text2 = "".join(self._get_tokens(text2, True))
        else:
            text1 = text1
            text2 = text2

        return self._levenshtein_similarity_strings(text1, text2)

    def get_vectors(self, text1, text2, remove_stopwords=False):
        """
        使用 jieba 斷詞並轉為 Bag-of-Words 向量
        """
        counter_a = self._get_token_counter(text1, remove_stopwords)
        counter_b = self._get_token_counter(text2, remove_stopwords)

        if not counter_a or not counter_b:
            return None, None

        vocabulary = sorted(set(counter_a.keys()).union(counter_b.keys()))
        vec_a = np.array([counter_a.get(token, 0) for token in vocabulary], dtype=np.float64)
        vec_b = np.array([counter_b.get(token, 0) for token in vocabulary], dtype=np.float64)
        return vec_a, vec_b

    def calculate_standard_cosine(self, text1, text2, remove_stopwords=False):
        counter_a = self._get_token_counter(text1, remove_stopwords)
        counter_b = self._get_token_counter(text2, remove_stopwords)
        return self._counter_cosine_similarity(counter_a, counter_b)

    def calculate_sorted_cosine(self, text1, text2, remove_stopwords=False):
        counter_a = self._get_token_counter(text1, remove_stopwords)
        counter_b = self._get_token_counter(text2, remove_stopwords)
        return self._sorted_counter_cosine_similarity(counter_a, counter_b)

    def calculate_tfidf_similarity(self, text1, text2, remove_stopwords=False):
        """
        TF-IDF Cosine Similarity with smoothed IDF.
        TF (Term Frequency) = count of term in document / total terms in document
        IDF (Inverse Document Frequency) = log((N + 1) / (df + 1)) + 1 (smoothed to avoid zero for common terms)
        """
        if not text1 or not text2:
            return 0.0

        tokens1 = self._get_tokens(text1, remove_stopwords)
        tokens2 = self._get_tokens(text2, remove_stopwords)

        if not tokens1 or not tokens2:
            return 0.0

        counter1 = Counter(tokens1)
        counter2 = Counter(tokens2)

        # Build vocabulary
        vocabulary = set(counter1.keys()).union(counter2.keys())
        if not vocabulary:
            return 0.0

        # Calculate document frequency (df) for each term
        df = {}
        for term in vocabulary:
            df[term] = (1 if term in counter1 else 0) + (1 if term in counter2 else 0)

        # Calculate TF-IDF vectors with smoothed IDF
        N = 2  # Two documents
        len1, len2 = len(tokens1), len(tokens2)

        def tfidf_vector(counter, total_len):
            vec = []
            for term in vocabulary:
                tf = counter.get(term, 0) / total_len if total_len > 0 else 0
                # Smoothed IDF: avoids zero for terms appearing in all documents
                idf = math.log((N + 1) / (df[term] + 1)) + 1
                vec.append(tf * idf)
            return np.array(vec, dtype=np.float64)

        vec1 = tfidf_vector(counter1, len1)
        vec2 = tfidf_vector(counter2, len2)

        # Cosine similarity
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def get_common_and_unique_words(self, text1, text2, remove_stopwords=False):
        """
        找出兩個文本的共同詞彙與各自獨有詞彙
        return: (common_words, unique_in_a, unique_in_b)
        """
        if not text1 or not text2:
            return set(), set(), set()

        words_a = self._get_word_set(text1, remove_stopwords)
        words_b = self._get_word_set(text2, remove_stopwords)
        common = words_a.intersection(words_b)
        return common, words_a - words_b, words_b - words_a

    def get_common_words(self, text1, text2, remove_stopwords=False):
        """
        找出兩個文本的共同詞彙
        """
        common, _, _ = self.get_common_and_unique_words(text1, text2, remove_stopwords)
        return common

    def get_unique_words(self, text1, text2, remove_stopwords=False):
        """
        找出兩個文本各自獨有的詞彙
        return: (unique_in_a, unique_in_b)
        """
        _, unique_a, unique_b = self.get_common_and_unique_words(text1, text2, remove_stopwords)
        return unique_a, unique_b

    def get_word_frequencies(self, text, remove_stopwords=False):
        """
        取得詞頻
        return: dict {word: count}
        """
        if not text:
            return {}
        return dict(self._get_token_counter(text, remove_stopwords))

    def create_similarity_scorer(self, base_text, method_index, remove_stopwords=False):
        """
        建立可重複使用的相似度評分函式，避免批次模式重複計算基準文本。
        return: function(target_text) -> score
        """
        base_text = base_text or ""

        if method_index == 0:  # Standard Cosine
            base_counter = self._get_token_counter(base_text, remove_stopwords)

            def score_fn(target_text):
                target_counter = self._get_token_counter(target_text, remove_stopwords)
                return self._counter_cosine_similarity(base_counter, target_counter)

            return score_fn

        if method_index == 1:  # Rearrangement Cosine
            base_counter = self._get_token_counter(base_text, remove_stopwords)
            base_keys = set(base_counter.keys())

            def score_fn(target_text):
                target_counter = self._get_token_counter(target_text, remove_stopwords)
                union_size = len(base_keys.union(target_counter.keys()))
                return self._sorted_counter_cosine_similarity(base_counter, target_counter, union_size)

            return score_fn

        if method_index == 2:  # Jaccard
            base_set = self._get_word_set(base_text, remove_stopwords)

            def score_fn(target_text):
                target_set = self._get_word_set(target_text, remove_stopwords)
                if not base_set or not target_set:
                    return 0.0
                union_size = len(base_set.union(target_set))
                if union_size == 0:
                    return 0.0
                return len(base_set.intersection(target_set)) / union_size

            return score_fn

        if method_index == 3:  # Levenshtein
            has_base_text = bool(base_text)

            if remove_stopwords:
                base_processed = "".join(self._get_tokens(base_text, True))

                def score_fn(target_text):
                    if not has_base_text or not target_text:
                        return 0.0
                    target_processed = "".join(self._get_tokens(target_text, True))
                    return self._levenshtein_similarity_strings(base_processed, target_processed)

                return score_fn

            def score_fn(target_text):
                if not has_base_text or not target_text:
                    return 0.0
                return self._levenshtein_similarity_strings(base_text, target_text)

            return score_fn

        raise ValueError(f"Unsupported method index: {method_index}")

    def calculate_batch_similarity(self, base_text, target_files, method_index, remove_stopwords=False, progress_callback=None):
        """
        批次計算相似度
        target_files: list of (filename, file_content)
        return: sorted list of (filename, score)
        """
        if not target_files:
            return []

        scorer = self.create_similarity_scorer(base_text, method_index, remove_stopwords)
        total_files = len(target_files)
        results = []

        for index, (fname, content) in enumerate(target_files, start=1):
            results.append((fname, scorer(content)))
            if progress_callback:
                progress_callback(index, total_files, fname)

        results.sort(key=lambda x: x[1], reverse=True)
        return results
