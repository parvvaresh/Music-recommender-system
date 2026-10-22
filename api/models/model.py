import pandas as pd
import numpy as np


class CosineSimilarityMatrix:
    def __init__(self):
        self._cosine_similarity_matrix = None

    def fit(self, df: pd.DataFrame) -> None:
        self.df = df
        n_samples = df.shape[0]
        self._cosine_similarity_matrix = np.zeros((n_samples, n_samples))

    def transform(self) -> np.array:
        if self._cosine_similarity_matrix is None:
            raise Exception("The cosine similarity matrix has not been fitted yet!")

        data = self.df.to_numpy()

        norms = np.linalg.norm(data, axis=1, keepdims=True)
        normalized_data = data / norms

        self._cosine_similarity_matrix = np.dot(normalized_data, normalized_data.T)

        return self._cosine_similarity_matrix
