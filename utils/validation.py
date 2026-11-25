
def validate_data(df):
    errors = []

    if df.empty:
        errors.append("Dataset is empty.")

    if "Age" in df.columns:
        if (df["Age"].dropna() < 0).any():
            errors.append("Invalid age detected.")

    if "Household_ID" not in df.columns:
        errors.append("Household_ID column is missing.")

    return errors
