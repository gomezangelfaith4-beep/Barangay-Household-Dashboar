
import pandas as pd
from pathlib import Path


def load_data(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Dataset not found: {file_path}")

    return pd.read_csv(file_path)


def clean_data(df):
    df = df.copy()

    # Standardize column names
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(" ", "_")
    )

    # Remove duplicate records
    df = df.drop_duplicates()

    # Clean text values
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype("string").str.strip()

    # Fill missing numeric values with median
    numeric_columns = df.select_dtypes(include="number").columns

    for col in numeric_columns:
        df[col] = df[col].fillna(df[col].median())

    # Fill missing text values
    text_columns = df.select_dtypes(include=["object", "string"]).columns

    for col in text_columns:
        df[col] = df[col].fillna("Unknown")

    return df
