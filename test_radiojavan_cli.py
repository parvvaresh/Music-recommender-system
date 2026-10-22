import pandas as pd
import pickle
import numpy as np
import subprocess
import sys
import os
from pathlib import Path


def test_cli_gentleman(tmp_path):
    # Create expected directory structure
    data_dir = tmp_path / "api" / "models" / "data"
    model_dir = tmp_path / "api" / "models" / "fainal_model"
    data_dir.mkdir(parents=True)
    model_dir.mkdir(parents=True)

    csv_path = data_dir / "RadioJavan_Top.csv"
    model_path = model_dir / "model.pkl"

    # Prepare dummy CSV with the required songs
    songs = [
        ("Gentleman", "Sasy"),
        ("Nakoni Bavar", "Zedbazi"),
        ("Mr. Lodeh", "Amir Tataloo"),
        ("To Ke Nisti Pisham", "Masih"),
        ("Moohat", "Mohsen Yeganeh"),
        ("Doctor", "Sasy"),
        ("Harjaye Shahr", "Ali Yasini"),
        ("Tekoon Bede", "Arash"),
        ("Ashegham Kardi", "Hoorosh Band"),
        ("Ey Vay", "Sahar"),
        ("Ey Joonam", "Sami Beigi"),
    ]
    df = pd.DataFrame(songs, columns=["musicName", "artistName"])
    df.to_csv(csv_path, index=False)

    # Make similarity matrix so that Gentleman is most similar to others in given order
    n = len(songs)
    sim_matrix = np.eye(n)
    order = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    for rank, idx in enumerate(order, start=1):
        sim_matrix[0, idx] = 1.0 - (rank * 0.01)
        sim_matrix[idx, 0] = sim_matrix[0, idx]

    with open(model_path, "wb") as f:
        pickle.dump(sim_matrix, f)

    # Copy script into tmp dir
    script_path = Path(__file__).parent / "RJ_Recommendation_System.py"
    local_script = tmp_path / "RJ_Recommendation_System.py"
    local_script.write_text(script_path.read_text(), encoding="utf-8")

    # Run CLI inside tmp_path (so ./api/models/... exists)
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parent)}
    result = subprocess.run(
        [sys.executable, str(local_script), "Gentleman"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
    )

    expected_output = """ rank          musicName     artistName
    1       Nakoni Bavar        Zedbazi
    2          Mr. Lodeh   Amir Tataloo
    3 To Ke Nisti Pisham          Masih
    4             Moohat Mohsen Yeganeh
    5             Doctor           Sasy
    6      Harjaye Shahr     Ali Yasini
    7        Tekoon Bede          Arash
    8     Ashegham Kardi   Hoorosh Band
    9             Ey Vay          Sahar
   10          Ey Joonam     Sami Beigi"""

    assert result.returncode == 0, result.stderr
    assert expected_output.strip() in result.stdout.strip()
