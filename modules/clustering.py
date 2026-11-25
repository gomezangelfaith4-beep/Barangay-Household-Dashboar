
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


def perform_clustering(df, n_clusters=3):
    df = df.copy()

    numeric_columns = df.select_dtypes(include="number").columns.tolist()

    # Exclude ID-like fields from clustering
    numeric_columns = [
        col for col in numeric_columns
        if "id" not in col.lower()
    ]

    if len(numeric_columns) == 0:
        df["Cluster"] = 0
        return df

    features = df[numeric_columns].copy()

    # Replace any remaining missing values
    features = features.fillna(features.median())

    # Standardize features
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    # Prevent the number of clusters from exceeding records
    actual_clusters = min(n_clusters, len(df))

    if actual_clusters < 2:
        df["Cluster"] = 0
        return df

    model = KMeans(
        n_clusters=actual_clusters,
        random_state=42,
        n_init=10
    )

    df["Cluster"] = model.fit_predict(scaled_features)

    return df
