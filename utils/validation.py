from __future__ import annotations

from datetime import date
from typing import Any


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def validate_household(values: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not _clean_text(values.get("household_id")):
        errors.append("Household ID is required")
    if not _clean_text(values.get("barangay")) and not _clean_text(values.get("purok")):
        errors.append("Purok or barangay/zone is required")
    try:
        household_members = int(values.get("household_members"))
        if household_members < 1:
            errors.append("Household members must be at least 1")
    except (TypeError, ValueError):
        errors.append("Household members must be a whole number")
    for field in ("household_head_age", "dependents"):
        value = values.get(field)
        if value is not None:
            try:
                integer = int(value)
                if integer < 0 or (field == "household_head_age" and integer > 120):
                    errors.append(
                        "Household head age must be 0–120"
                        if field == "household_head_age"
                        else "Dependent count cannot be negative"
                    )
            except (TypeError, ValueError):
                errors.append(f"{field.replace('_', ' ').capitalize()} must be a whole number")
    income = values.get("monthly_income_php")
    if income is not None:
        try:
            if float(income) < 0:
                errors.append("Monthly income cannot be negative")
        except (TypeError, ValueError):
            errors.append("Monthly income must be numeric")
    try:
        member_count = int(values.get("household_members"))
    except (TypeError, ValueError):
        member_count = 0
    for field, label in (
        ("senior_citizens_count", "Senior citizen count"),
        ("pwd_count", "PWD count"),
    ):
        value = values.get(field)
        if value is not None:
            try:
                count = int(value)
                if count < 0:
                    errors.append(f"{label} cannot be negative")
                elif member_count and count > member_count:
                    errors.append(f"{label} cannot exceed household members")
            except (TypeError, ValueError):
                errors.append(f"{label} must be a whole number")
    if values.get("date_registered"):
        try:
            registered = date.fromisoformat(str(values["date_registered"]))
            if registered > date.today():
                errors.append("Registration date cannot be in the future")
        except ValueError:
            errors.append("Registration date must be a valid date")
    return errors


def validate_resident(values: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not _clean_text(values.get("resident_id")):
        errors.append("Resident ID is required")
    if not _clean_text(values.get("full_name")):
        errors.append("Full name is required")
    if not _clean_text(values.get("household_id")):
        errors.append("A linked household is required")
    birth_date = values.get("date_of_birth")
    if not birth_date:
        errors.append("Date of birth is required")
    else:
        try:
            parsed = date.fromisoformat(str(birth_date))
            if parsed > date.today():
                errors.append("Date of birth cannot be in the future")
        except ValueError:
            errors.append("Date of birth must be a valid date")
    if values.get("sex") not in {None, "Female", "Male", "Other"}:
        errors.append("Sex must be Female, Male, Other, or not recorded")
    if values.get("pwd_status") not in {None, "Yes", "No"}:
        errors.append("PWD status must be Yes, No, or not recorded")
    return errors
