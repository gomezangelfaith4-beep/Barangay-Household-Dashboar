
import streamlit as st
import pandas as pd
import plotly.express as px


def show_dashboard(df):
    st.header("Barangay Household Dashboard")

    total_households = len(df)

    numeric_columns = df.select_dtypes(include="number").columns.tolist()

    if "Cluster" in numeric_columns:
        numeric_columns.remove("Cluster")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Households", total_households)

    if "Family_Size" in df.columns:
        col2.metric(
            "Average Family Size",
            round(df["Family_Size"].mean(), 2)
        )
    else:
        col2.metric("Numeric Variables", len(numeric_columns))

    if "Monthly_Income" in df.columns:
        col3.metric(
            "Average Monthly Income",
            f"₱{df['Monthly_Income'].mean():,.2f}"
        )
    else:
        col3.metric(
            "Number of Clusters",
            df["Cluster"].nunique() if "Cluster" in df.columns else 0
        )

    st.divider()

    st.subheader("Household Dataset Overview")

    st.dataframe(df.head(20), use_container_width=True)

    if "Cluster" in df.columns:
        st.subheader("Households per Cluster")

        cluster_counts = (
            df["Cluster"]
            .value_counts()
            .sort_index()
            .reset_index()
        )

        cluster_counts.columns = ["Cluster", "Households"]

        fig = px.bar(
            cluster_counts,
            x="Cluster",
            y="Households",
            title="Household Distribution by Cluster",
            text="Households"
        )

        st.plotly_chart(fig, use_container_width=True)

    if "Monthly_Income" in df.columns:
        st.subheader("Household Income Distribution")

        fig = px.histogram(
            df,
            x="Monthly_Income",
            nbins=20,
            title="Distribution of Monthly Household Income"
        )

        st.plotly_chart(fig, use_container_width=True)

    if "Employment_Status" in df.columns:
        st.subheader("Employment Status")

        employment_counts = df["Employment_Status"].value_counts()

        fig = px.pie(
            values=employment_counts.values,
            names=employment_counts.index,
            title="Employment Status Distribution"
        )

        st.plotly_chart(fig, use_container_width=True)
