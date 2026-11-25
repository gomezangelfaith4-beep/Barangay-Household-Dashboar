
import pandas as pd
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "barangay_households.csv"

def load_data():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip()
    return df

def clean_data(df):
    df = df.copy()
    df = df.drop_duplicates()
    df.columns = df.columns.str.strip()
    return df

def filter_data(df, purok=None, sex=None):
    filtered = df.copy()

    if purok and "Purok" in filtered.columns:
        filtered = filtered[filtered["Purok"] == purok]

    if sex and "Sex" in filtered.columns:
        filtered = filtered[filtered["Sex"] == sex]

    return filtered
