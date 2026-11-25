
def total_residents(df):
    return len(df)

def total_households(df):
    if "Household_ID" in df.columns:
        return df["Household_ID"].nunique()
    return 0

def population_by_sex(df):
    if "Sex" not in df.columns:
        return {}
    return df["Sex"].value_counts().to_dict()

def population_by_purok(df):
    if "Purok" not in df.columns:
        return {}
    return df["Purok"].value_counts().to_dict()

def population_by_age(df):
    if "Age" not in df.columns:
        return {}

    bins = [0, 12, 17, 59, 120]
    labels = ["Children", "Teenagers", "Adults", "Senior Citizens"]

    groups = __import__("pandas").cut(
        df["Age"], bins=bins, labels=labels
    )
    return groups.value_counts().to_dict()
