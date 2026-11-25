from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


SOURCE_TO_INTERNAL = {
    "Household_ID": "household_id",
    "Purok": "purok",
    "Family_Members": "household_members",
    "Monthly_Household_Income_PHP": "monthly_income_php",
    "Employment_Status": "employment_status",
    "Age_Group_Profile": "age_group_profile",
    "Senior_Citizens_Count": "senior_citizens_count",
    "PWD_Count": "pwd_count",
    "Access_to_Water": "water_access",
    "Access_to_Electricity": "electricity_access",
    "Housing_Type": "housing_status",
    "Suggested_Assistance_Category": "suggested_assistance_category",
}
REQUIRED_SOURCE_COLUMNS = (
    "Household_ID",
    "Purok",
    "Family_Members",
)
NUMERIC_COLUMNS = {
    "household_head_age",
    "household_members",
    "dependents",
    "monthly_income_php",
    "senior_citizens_count",
    "pwd_count",
}
OPTIONAL_INTERNAL_COLUMNS = (
    "household_head_name",
    "household_address",
    "barangay",
    "household_head_age",
    "dependents",
    "assistance_program",
    "vulnerability_level",
    "date_registered",
    "household_status",
    "contact_number",
)


def load_households_csv(path: str | Path) -> pd.DataFrame:
    """Load the observed household schema and preserve absent fields as unknown."""
    source_path = Path(path)
    if not source_path.is_file():
        raise FileNotFoundError(f"Household CSV not found: {source_path}")
    frame = pd.read_csv(source_path)
    if frame.empty:
        raise ValueError(f"Household CSV contains no records: {source_path}")
    frame.columns = [str(column).strip() for column in frame.columns]
    missing_columns = [
        column for column in REQUIRED_SOURCE_COLUMNS if column not in frame.columns
    ]
    if missing_columns:
        raise ValueError(
            "Household CSV is missing required columns: "
            + ", ".join(missing_columns)
        )

    internal_columns = {
        source: internal
        for source, internal in SOURCE_TO_INTERNAL.items()
        if source in frame.columns
    }
    frame = frame.rename(columns=internal_columns)
    for column in OPTIONAL_INTERNAL_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA

    for column in ("household_id", "purok"):
        frame[column] = frame[column].astype("string").str.strip()
    missing_required = (
        frame["household_id"].isna()
        | frame["household_id"].eq("")
        | frame["purok"].isna()
        | frame["purok"].eq("")
    )
    if missing_required.any():
        raise ValueError(
            f"{int(missing_required.sum())} household rows have no household ID or Purok."
        )
    duplicated = frame["household_id"].duplicated(keep=False)
    if duplicated.any():
        duplicate_ids = sorted(frame.loc[duplicated, "household_id"].unique().tolist())
        raise ValueError(
            "Duplicate household IDs in the source CSV: " + ", ".join(duplicate_ids)
        )

    for column in NUMERIC_COLUMNS:
        if column not in frame.columns:
            continue
        converted = pd.to_numeric(frame[column], errors="coerce")
        invalid = frame[column].notna() & converted.isna()
        if invalid.any():
            raise ValueError(
                f"Column {column!r} contains {int(invalid.sum())} non-numeric values."
            )
        frame[column] = converted

    invalid_members = (
        frame["household_members"].isna()
        | frame["household_members"].lt(1)
        | frame["household_members"].mod(1).ne(0)
    )
    if invalid_members.any():
        raise ValueError(
            f"{int(invalid_members.sum())} household rows have an invalid member count."
        )
    for column in ("household_head_age", "senior_citizens_count", "pwd_count"):
        if column in frame.columns and frame[column].notna().any():
            invalid = (
                frame[column].dropna().lt(0)
                | frame[column].dropna().mod(1).ne(0)
            )
            if invalid.any():
                raise ValueError(
                    f"Column {column!r} must contain non-negative whole numbers."
                )
    if frame["household_head_age"].dropna().gt(120).any():
        raise ValueError("Household head ages must be between 0 and 120.")
    if frame["dependents"].dropna().lt(0).any():
        raise ValueError("Dependent counts cannot be negative.")
    if frame["monthly_income_php"].dropna().lt(0).any():
        raise ValueError("Monthly household income cannot be negative.")
    if frame["senior_citizens_count"].dropna().gt(
        frame.loc[frame["senior_citizens_count"].notna(), "household_members"]
    ).any():
        raise ValueError("Senior citizen counts cannot exceed household member counts.")
    if frame["pwd_count"].dropna().gt(
        frame.loc[frame["pwd_count"].notna(), "household_members"]
    ).any():
        raise ValueError("PWD counts cannot exceed household member counts.")

    for column in frame.select_dtypes(include=["object", "string"]).columns:
        frame[column] = (
            frame[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )
    frame["household_members"] = frame["household_members"].astype(int)
    for column in ("household_head_age", "dependents", "senior_citizens_count", "pwd_count"):
        if column in frame.columns and frame[column].notna().all():
            frame[column] = frame[column].astype(int)
    return frame


def records_to_frame(
    records: list[dict[str, Any]],
    columns: tuple[str, ...] | list[str] | None = None,
) -> pd.DataFrame:
    return pd.DataFrame.from_records(records, columns=columns)
