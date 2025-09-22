import pandas as pd
import json
from pathlib import Path

DATA_FILE = Path(r"E:\updated_with_coordinates.csv")


def safe_json_parse(x):
    try:
        return json.loads(x) if pd.notna(x) else []
    except json.JSONDecodeError:
        return []


def load_dataset():
    try:
        df = pd.read_csv(DATA_FILE)
        category_cols = [col for col in df.columns if col.startswith("Category_")]
        for col in category_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        for col in ["Travel_Method_Suitable", "Travel_Method_Low_Budget"]:
            if col in df.columns:
                df[col] = df[col].apply(safe_json_parse)
        if "Travel_Guide_needed" in df.columns:
            df["Travel_Guide_needed"] = pd.to_numeric(df["Travel_Guide_needed"], errors="coerce").fillna(0).astype(int)
        return df
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return pd.DataFrame()


DATASET = load_dataset()


def get_locations(city: str = None, interests: list[str] = None):
    df = DATASET.copy()
    if city:
        df = df[df["Nearest_City"].str.strip().str.lower() == city.strip().lower()]
    if interests:
        for interest in interests:
            col = f"Category_{interest.strip().capitalize()}"
            if col in df.columns:
                df = df[df[col] == 1]
    return df.to_dict(orient="records")
