from __future__ import annotations
from pathlib import Path
from typing import Tuple
import pandas as pd

def ensure_dir(p: str | Path) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p

def load_eval_data(path: str | Path) -> Tuple[pd.DataFrame, pd.Series]:
    path = Path(path)
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    y = df.iloc[:, -1]
    X = df.iloc[:, :-1]
    return X, y
