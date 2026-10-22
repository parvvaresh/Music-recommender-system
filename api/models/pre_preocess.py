import pandas as pd
from standardize import MinMaxScaler
from word2vec.pre_process import preprocessing_text
from word2vec.TfIdf import TfIdf


def pre_process(df: pd.DataFrame) -> pd.DataFrame:
    selected_columns = [
        "Radiojavan_play",
        "Radiojavan_likes",
        "lyric",
        "popularity",
        "danceability",
        "energy",
        "key",
        "loudness",
        "mode",
        "speechiness",
        "acousticness",
        "instrumentalness",
        "liveness",
        "valence",
        "tempo",
    ]

    df_selected = df[selected_columns]
    df_selected_lyric = df_selected[["lyric"]]
    df_selected = df_selected.drop(columns=["lyric"])

    preprocessing_lyric = preprocessing_text(df_selected_lyric, "lyric")
    model_TfIdf = TfIdf(preprocessing_lyric["Text - preproces"].to_list())

    vector_lyric = model_TfIdf.transform()
    vector_lyric = pd.DataFrame(vector_lyric)

    StandardScaler_model = MinMaxScaler()
    StandardScaler_model.fit(vector_lyric)
    vector_lyric = StandardScaler_model.transform(vector_lyric)

    StandardScaler_model = MinMaxScaler()
    StandardScaler_model.fit(df_selected)
    df_selected_Standardize = StandardScaler_model.transform(df_selected)

    data_sets = pd.concat([df_selected_Standardize, vector_lyric], axis=1)

    return data_sets
