from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd


def calculate_age(date_of_birth: Any, on_date: date | None = None) -> int | None:
    if date_of_birth is None or pd.isna(date_of_birth) or not str(date_of_birth).strip():
        return None
    try:
        birth = date.fromisoformat(str(date_of_birth)[:10])
    except ValueError:
        return None
    current = on_date or date.today()
    if birth > current:
        return None
    return current.year - birth.year - (
        (current.month, current.day) < (birth.month, birth.day)
    )


def age_group(age: int | None) -> str | None:
    if age is None:
        return None
    if age < 18:
        return "Child (0-17)"
    if age < 60:
        return "Adult (18-59)"
    return "Senior (60+)"


def add_area_label(records: pd.DataFrame) -> pd.DataFrame:
    result = records.copy()
    if "purok" in result.columns:
        purok = result["purok"].astype("string").str.strip()
        has_purok = purok.notna() & purok.ne("")
        barangay = (
            result["barangay"]
            if "barangay" in result.columns
            else pd.Series(index=result.index, dtype="object")
        )
        result["area_label"] = purok.where(has_purok, barangay)
    elif "barangay" in result.columns:
        result["area_label"] = result["barangay"]
    else:
        result["area_label"] = pd.Series(index=result.index, dtype="object")
    return result


def filter_households(
    households: pd.DataFrame,
    *,
    zones: list[str] | None = None,
    household_statuses: list[str] | None = None,
    age_profiles: list[str] | None = None,
) -> pd.DataFrame:
    result = households.copy()
    if zones is not None:
        if not zones:
            return result.iloc[0:0].copy()
        result = result[add_area_label(result)["area_label"].astype("string").isin(zones)]
    if household_statuses is not None:
        if not household_statuses:
            return result.iloc[0:0].copy()
        status = result["household_status"].fillna("Not recorded").astype(str)
        result = result[status.isin(household_statuses)]
    if age_profiles is not None:
        if not age_profiles:
            return result.iloc[0:0].copy()
        profiles = result["age_group_profile"].fillna("Not recorded").astype(str)
        result = result[profiles.isin(age_profiles)]
    return result.copy()


def filter_residents(
    residents: pd.DataFrame,
    *,
    households: pd.DataFrame,
    sexes: list[str] | None = None,
    age_groups: list[str] | None = None,
    civil_statuses: list[str] | None = None,
    education_levels: list[str] | None = None,
    household_ids: list[str] | None = None,
) -> pd.DataFrame:
    result = residents.copy()
    if result.empty:
        for column in ("age", "age_group"):
            if column not in result.columns:
                result[column] = pd.Series(dtype="object")
        return result

    result["age"] = result["date_of_birth"].map(calculate_age).astype("Int64")
    result["age_group"] = result["age"].map(
        lambda value: age_group(int(value)) if pd.notna(value) else "Not recorded"
    )
    linked_household_ids = (
        households["household_id"].astype(str).tolist()
        if "household_id" in households.columns
        else []
    )
    result = result[result["household_id"].astype(str).isin(linked_household_ids)]
    for column, selected in (
        ("sex", sexes),
        ("age_group", age_groups),
        ("civil_status", civil_statuses),
        ("educational_attainment", education_levels),
        ("household_id", household_ids),
    ):
        if selected is not None:
            if not selected:
                return result.iloc[0:0].copy()
            values = (
                result[column].fillna("Not recorded").astype(str)
                if column != "household_id"
                else result[column].astype(str)
            )
            result = result[values.isin(selected)]
    return add_area_label(result)


def _count_available(
    residents: pd.DataFrame,
    field: str,
    value: str,
) -> int | None:
    if residents.empty or field not in residents.columns:
        return None
    observed = residents[field].dropna().astype(str).str.strip()
    if observed.empty:
        return None
    return int(observed.str.casefold().eq(value.casefold()).sum())


def dashboard_summary(
    households: pd.DataFrame,
    residents: pd.DataFrame,
) -> dict[str, Any]:
    household_count = len(households)
    member_counts = (
        pd.to_numeric(households["household_members"], errors="coerce")
        if "household_members" in households.columns
        else pd.Series(dtype="float64")
    )
    total_population = (
        int(member_counts.sum())
        if member_counts.notna().any()
        else None
    )
    average_size = (
        float(member_counts.mean())
        if member_counts.notna().any()
        else None
    )

    def household_count_field(column: str) -> int | None:
        if column not in households.columns or households.empty:
            return None
        counts = pd.to_numeric(households[column], errors="coerce")
        return int(counts.sum()) if counts.notna().any() else None

    if residents.empty:
        male_count = female_count = child_count = None
        senior_count = household_count_field("senior_citizens_count")
        pwd_count = household_count_field("pwd_count")
        demographic_help = (
            "Unavailable: no individually registered resident records are present."
        )
        senior_help = (
            "Sum of the source dataset's household-level Senior_Citizens_Count field."
            if senior_count is not None
            else "Unavailable: no senior-citizen count is present in the data."
        )
        pwd_help = (
            "Sum of the source dataset's household-level PWD_Count field."
            if pwd_count is not None
            else "Unavailable: no PWD count is present in the data."
        )
    else:
        male_count = _count_available(residents, "sex", "Male")
        female_count = _count_available(residents, "sex", "Female")
        ages = residents["date_of_birth"].map(calculate_age)
        known_ages = ages.dropna()
        child_count = (
            int(known_ages.lt(18).sum()) if not known_ages.empty else None
        )
        resident_senior_count = (
            int(known_ages.ge(60).sum()) if not known_ages.empty else None
        )
        senior_count = household_count_field("senior_citizens_count")
        if senior_count is None:
            senior_count = resident_senior_count
        pwd_values = (
            residents["pwd_status"].dropna().astype(str).str.strip()
            if "pwd_status" in residents.columns
            else pd.Series(dtype="object")
        )
        resident_pwd_count = (
            int(pwd_values.str.casefold().eq("yes").sum())
            if not pwd_values.empty
            else None
        )
        pwd_count = household_count_field("pwd_count")
        if pwd_count is None:
            pwd_count = resident_pwd_count
        demographic_help = (
            "Count of individually registered residents matching current resident "
            "filters; the register may be incomplete."
        )
        senior_help = (
            "Source household-level senior counts are used when available; the "
            "individual resident registry may be incomplete."
        )
        pwd_help = (
            "Source household-level PWD counts are used when available; the "
            "individual resident registry may be incomplete."
        )

    return {
        "total_households": household_count,
        "total_population": total_population,
        "male_residents": male_count,
        "female_residents": female_count,
        "children": child_count,
        "senior_citizens": senior_count,
        "pwd_residents": pwd_count,
        "registered_families": None,
        "average_household_size": average_size,
        "population_help": (
            "Sum of household_members in matching household records; not an individual "
            "resident registry count."
        ),
        "male_help": demographic_help,
        "female_help": demographic_help,
        "children_help": demographic_help,
        "senior_help": senior_help,
        "pwd_help": pwd_help,
        "families_help": (
            "Family identifiers or registered-family fields are not present in the data."
        ),
        "average_help": "Mean of the recorded household_members field.",
    }


def household_insights(
    households: pd.DataFrame,
    residents: pd.DataFrame,
) -> list[str]:
    observations: list[str] = []
    if not households.empty:
        household_data = add_area_label(households)
        household_counts = household_data.groupby("area_label").size()
        top_household_zone = household_counts.idxmax()
        observations.append(
            f"{top_household_zone} has the most household records "
            f"({int(household_counts.max()):,})."
        )
        population_by_zone = household_data.groupby("area_label")[
            "household_members"
        ].sum(min_count=1)
        if population_by_zone.notna().any():
            top_population_zone = population_by_zone.idxmax()
            observations.append(
                f"{top_population_zone} has the highest sum of recorded household "
                f"members ({int(population_by_zone.max()):,})."
            )
        mean_size = pd.to_numeric(
            households["household_members"], errors="coerce"
        ).mean()
        if pd.notna(mean_size):
            observations.append(
                f"Average recorded household size is {mean_size:.1f} members."
            )
        if "vulnerability_level" in households.columns:
            high_count = int(
                households["vulnerability_level"]
                .astype("string")
                .str.casefold()
                .eq("high")
                .sum()
            )
            if high_count:
                observations.append(
                    f"{high_count:,} household record(s) are marked High vulnerability "
                    "in the source data."
                )
        for column, label in (
            ("senior_citizens_count", "senior citizens"),
            ("pwd_count", "PWD members"),
        ):
            if column in households.columns:
                counts = pd.to_numeric(households[column], errors="coerce")
                if counts.notna().any():
                    observations.append(
                        f"The household source records {int(counts.sum()):,} "
                        f"{label} across the current selection."
                    )
    if not residents.empty:
        age_values = residents["date_of_birth"].map(calculate_age)
        children = int(
            age_values.map(lambda age: age is not None and age < 18).sum()
        )
        seniors = int(
            age_values.map(lambda age: age is not None and age >= 60).sum()
        )
        observations.append(
            f"The individual resident register contains {children:,} recorded "
            f"children and {seniors:,} recorded senior citizens; it may be incomplete."
        )
        sex_counts = (
            residents["sex"].fillna("Not recorded").value_counts().to_dict()
            if "sex" in residents.columns
            else {}
        )
        if sex_counts:
            observations.append(
                "Resident records by sex: "
                + ", ".join(f"{key}: {value:,}" for key, value in sorted(sex_counts.items()))
                + "."
            )
    return observations
