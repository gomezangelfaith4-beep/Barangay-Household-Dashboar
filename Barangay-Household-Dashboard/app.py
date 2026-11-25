
from pathlib import Path

import streamlit as st
import pandas as pd

from modules.data_processing import load_data, clean_data
from modules.clustering import perform_clustering
from modules.dashboard import show_dashboard
from modules.recommendations import generate_recommendations


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "barangay_household_dataset.csv"

st.set_page_config(
    page_title="Barangay Household Dashboard",
    page_icon="🏘️",
    layout="wide"
)

st.title("🏘️ Barangay Household Profile Analysis")
st.caption("Household Data Analysis and Social Assistance Planning Dashboard")

@st.cache_data
def get_data():
    return load_data(DATA_PATH)

try:
    df = get_data()
    cleaned_df = clean_data(df)

    st.sidebar.header("Navigation")
    page = st.sidebar.radio(
        "Choose a page",
        ["Home", "Household Data", "Clustering", "Recommendations"]
    )

    clustered_df = perform_clustering(cleaned_df)

    if page == "Home":
        show_dashboard(clustered_df)

    elif page == "Household Data":
        st.subheader("Household Dataset")
        st.dataframe(clustered_df, use_container_width=True)

        st.download_button(
            "Download Household Data",
            clustered_df.to_csv(index=False),
            "household_analysis.csv",
            "text/csv"
        )

    elif page == "Clustering":
        st.subheader("Household Clustering Results")
        st.dataframe(clustered_df, use_container_width=True)

        if "Cluster" in clustered_df.columns:
            st.bar_chart(clustered_df["Cluster"].value_counts())

    elif page == "Recommendations":
        st.subheader("Social Assistance Recommendations")
        recommendations = generate_recommendations(clustered_df)
        st.write(recommendations)

except FileNotFoundError:
    st.error("Dataset not found. Please check the data folder.")

except Exception as e:
    st.error(f"An error occurred: {e}")
