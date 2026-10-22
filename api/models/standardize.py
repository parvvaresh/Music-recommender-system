import pandas as pd


class MinMaxScaler:
    def __init__(self) -> None:
        self._min = None
        self._max = None

    def fit(self, df: pd.DataFrame) -> None:
        self._min = df.min()
        self._max = df.max()

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:

        if self._max is None or self._min is None:
            raise Exception("The scaler has not been fitted yet!")

        return (df - self._min) / (self._max - self._min)
