import pandas as pd
import numpy as np
import pickle

from pre_preocess import pre_process
from model import CosineSimilarityMatrix


def run_save_model(df: pd.DataFrame) -> None:
    data_pre_process = pre_process(df)

    model = CosineSimilarityMatrix()
    model.fit(data_pre_process)
    cs_matrix = model.transform()

    with open("./fainal_model/model.pkl", "wb") as file:
        pickle.dump(cs_matrix, file)


df = pd.read_csv("./data/RadioJavan_Top.csv")

print(run_save_model(df))
