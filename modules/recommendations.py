
def generate_recommendations(df):
    recommendations = []

    if df.empty:
        return ["No household records available for analysis."]

    # Income-based recommendation
    if "Monthly_Income" in df.columns:
        low_income_threshold = df["Monthly_Income"].quantile(0.25)

        low_income_count = (
            df["Monthly_Income"] <= low_income_threshold
        ).sum()

        recommendations.append(
            f"{low_income_count} household(s) are within "
            "the lowest income group. Consider reviewing them "
            "for possible livelihood or financial assistance."
        )

    # Family size recommendation
    if "Family_Size" in df.columns:
        large_family_count = (df["Family_Size"] >= 6).sum()

        recommendations.append(
            f"{large_family_count} household(s) have 6 or more "
            "members. Consider evaluating their food and basic "
            "needs assistance."
        )

    # Senior citizen recommendation
    if "Senior_Count" in df.columns:
        senior_households = (df["Senior_Count"] > 0).sum()

        recommendations.append(
            f"{senior_households} household(s) have senior citizens. "
            "Consider health outreach and senior support programs."
        )

    # PWD recommendation
    if "PWD_Count" in df.columns:
        pwd_households = (df["PWD_Count"] > 0).sum()

        recommendations.append(
            f"{pwd_households} household(s) have persons with "
            "disabilities. Consider accessibility and appropriate "
            "support services."
        )

    # Employment recommendation
    if "Employment_Status" in df.columns:
        unemployed = df["Employment_Status"].astype(str).str.lower()

        unemployed_count = unemployed.str.contains(
            "unemployed",
            na=False
        ).sum()

        recommendations.append(
            f"{unemployed_count} household record(s) indicate "
            "unemployment. Consider livelihood or employment programs."
        )

    if not recommendations:
        recommendations.append(
            "The dataset does not contain the expected fields for "
            "generating recommendations. Review the dataset columns."
        )

    return recommendations
