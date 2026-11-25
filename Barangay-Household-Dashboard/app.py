from __future__ import annotations

import os
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from database.database import (
    create_household,
    create_resident,
    delete_household,
    delete_resident,
    initialize_database,
    list_households,
    list_residents,
    update_household,
    update_resident,
)
from utils.analytics import (
    add_area_label,
    dashboard_summary,
    filter_households,
    filter_residents,
    household_insights,
)
from utils.data_processing import load_households_csv, records_to_frame
from utils.reports import build_pdf_report
from utils.validation import validate_household, validate_resident


ROOT = Path(__file__).resolve().parent
SOURCE_PATH = ROOT / "data" / "barangay_households.csv"
DEFAULT_DB_PATH = ROOT / "instance" / "barangay_households.sqlite3"
NAVIGATION = {
    "Dashboard overview": "dashboard",
    "Household records": "home",
    "Resident records": "groups",
    "Population analytics": "query_stats",
    "Reports and downloads": "download",
    "System information": "settings",
}
AGE_GROUPS = ["Child (0-17)", "Adult (18-59)", "Senior (60+)"]
SEX_OPTIONS = ["Female", "Male", "Other", "Not recorded"]
DEFAULT_CIVIL_STATUSES = [
    "Single",
    "Married",
    "Widowed",
    "Separated",
    "Divorced",
    "Not recorded",
]
DEFAULT_EDUCATION_LEVELS = [
    "No formal education",
    "Elementary",
    "High school",
    "Senior high school",
    "Vocational",
    "College",
    "Postgraduate",
    "Not recorded",
]
HOUSEHOLD_FIELDS = [
    "household_id",
    "household_head_name",
    "household_address",
    "barangay",
    "purok",
    "household_head_age",
    "household_members",
    "dependents",
    "monthly_income_php",
    "housing_status",
    "water_access",
    "electricity_access",
    "assistance_program",
    "employment_status",
    "age_group_profile",
    "senior_citizens_count",
    "pwd_count",
    "suggested_assistance_category",
    "vulnerability_level",
    "date_registered",
    "household_status",
    "contact_number",
]
RESIDENT_FIELDS = [
    "resident_id",
    "full_name",
    "sex",
    "date_of_birth",
    "civil_status",
    "occupation",
    "educational_attainment",
    "household_id",
    "contact_number",
    "pwd_status",
]
FILTER_KEYS = {
    "zone": "zone_filter",
    "sex": "sex_filter",
    "age_group": "age_group_filter",
    "age_profile": "household_age_profile_filter",
    "civil_status": "civil_status_filter",
    "education": "education_filter",
    "household_status": "household_status_filter",
    "household_id": "resident_household_filter",
}

st.set_page_config(
    page_title="Barangay household dashboard",
    page_icon=":material/home_work:",
    layout="wide",
)


def current_database_path() -> Path:
    configured = os.environ.get("BARANGAY_DB_PATH")
    return Path(configured).expanduser() if configured else DEFAULT_DB_PATH


def show_plotly_chart(figure: go.Figure, key: str, alt: str) -> None:
    st.plotly_chart(
        figure,
        width="stretch",
        theme="streamlit",
        key=key,
        alt=alt,
    )


def display_households(records: pd.DataFrame, alt: str) -> None:
    columns = [
        column
        for column in HOUSEHOLD_FIELDS
        if column in records.columns
    ]
    visible = records.loc[:, columns].copy()
    visible = visible.rename(
        columns={
            "household_id": "Household ID",
            "household_head_name": "Household head",
            "household_address": "Address",
            "barangay": "Barangay / zone",
            "purok": "Purok",
            "household_head_age": "Head age",
            "household_members": "Household members",
            "dependents": "Dependents",
            "monthly_income_php": "Monthly income (PHP)",
            "housing_status": "Housing type",
            "water_access": "Water access",
            "electricity_access": "Electricity access",
            "assistance_program": "Assistance program",
            "employment_status": "Employment status",
            "age_group_profile": "Household age-group profile",
            "senior_citizens_count": "Recorded senior citizens",
            "pwd_count": "Recorded PWD members",
            "suggested_assistance_category": "Suggested assistance category",
            "vulnerability_level": "Vulnerability",
            "date_registered": "Date registered",
            "household_status": "Registration status",
            "contact_number": "Contact number",
        }
    )
    st.dataframe(
        visible,
        hide_index=True,
        width="stretch",
        alt=alt,
    )


def display_residents(records: pd.DataFrame, alt: str) -> None:
    columns = [
        column
        for column in RESIDENT_FIELDS + ["age", "barangay", "purok"]
        if column in records.columns
    ]
    visible = records.loc[:, columns].rename(
        columns={
            "resident_id": "Resident ID",
            "full_name": "Full name",
            "sex": "Sex",
            "date_of_birth": "Date of birth",
            "age": "Age",
            "civil_status": "Civil status",
            "occupation": "Occupation",
            "educational_attainment": "Educational attainment",
            "household_id": "Household ID",
            "barangay": "Barangay / zone",
            "purok": "Purok",
            "contact_number": "Contact number",
            "pwd_status": "PWD status",
        }
    )
    st.dataframe(
        visible,
        hide_index=True,
        width="stretch",
        alt=alt,
    )


def reset_filters(defaults: dict[str, list[str]]) -> None:
    for name, key in FILTER_KEYS.items():
        st.session_state[key] = defaults[name]


def household_form(
    initial: dict[str, object] | None = None,
    *,
    form_key: str,
    submit_label: str,
) -> tuple[dict[str, object], bool]:
    values = initial or {}

    def text_value(column: str, label: str, required: bool = False) -> str:
        return st.text_input(
            label,
            value=str(values.get(column) or ""),
            key=f"{form_key}_{column}",
            help="Required field" if required else None,
        )

    def choice_value(
        column: str,
        label: str,
        options: list[str],
    ) -> str | None:
        choices = ["Not recorded", *options]
        existing = str(values.get(column) or "")
        if existing and existing not in choices:
            choices.append(existing)
        choice = st.selectbox(
            label,
            choices,
            index=choices.index(existing) if existing in choices else 0,
            key=f"{form_key}_{column}",
        )
        return None if choice == "Not recorded" else choice

    with st.form(form_key):
        st.subheader("Household details")
        first, second = st.columns(2)
        with first:
            household_id = text_value("household_id", "Household ID", True)
            household_head_name = text_value("household_head_name", "Household head")
            household_address = text_value("household_address", "Household address")
            barangay = text_value("barangay", "Barangay (optional if Purok is known)")
            purok = text_value("purok", "Purok / area", True)
            contact_number = text_value("contact_number", "Contact number")
            date_registered = st.date_input(
                "Date registered",
                value=(
                    date.fromisoformat(str(values["date_registered"]))
                    if values.get("date_registered")
                    else None
                ),
                key=f"{form_key}_date_registered",
            )
        with second:
            household_members = st.number_input(
                "Number of household members",
                min_value=1,
                value=max(1, int(values.get("household_members") or 1)),
                step=1,
                key=f"{form_key}_household_members",
            )
            head_age = st.number_input(
                "Household head age (optional)",
                min_value=0,
                max_value=120,
                value=min(120, max(0, int(values.get("household_head_age") or 0))),
                step=1,
                key=f"{form_key}_household_head_age",
            )
            dependents = st.number_input(
                "Dependents (optional)",
                min_value=0,
                value=max(0, int(values.get("dependents") or 0)),
                step=1,
                key=f"{form_key}_dependents",
            )
            monthly_income = st.number_input(
                "Monthly household income (PHP, optional)",
                min_value=0.0,
                value=max(0.0, float(values.get("monthly_income_php") or 0)),
                step=500.0,
                key=f"{form_key}_monthly_income_php",
            )
            housing_status = choice_value(
                "housing_status",
                "Housing type",
                ["Concrete", "Light Materials", "Semi-concrete", "Owned", "Rented", "Shared", "Informal"],
            )
            water_access = choice_value(
                "water_access",
                "Water access",
                ["Yes", "No", "Safe", "Unsafe", "Other"],
            )
            electricity_access = choice_value(
                "electricity_access",
                "Electricity access",
                ["Yes", "No", "Connected", "Not Connected"],
            )
            assistance_program = text_value(
                "assistance_program",
                "Assistance program (optional)",
            )
            employment_status = text_value("employment_status", "Employment status")
            age_group_profile = text_value(
                "age_group_profile",
                "Household age-group profile",
            )
            senior_citizens_count = st.number_input(
                "Recorded senior citizens in household",
                min_value=0,
                max_value=int(household_members),
                value=min(
                    int(household_members),
                    max(0, int(values.get("senior_citizens_count") or 0)),
                ),
                step=1,
                key=f"{form_key}_senior_citizens_count",
            )
            pwd_count = st.number_input(
                "Recorded PWD members in household",
                min_value=0,
                max_value=int(household_members),
                value=min(
                    int(household_members),
                    max(0, int(values.get("pwd_count") or 0)),
                ),
                step=1,
                key=f"{form_key}_pwd_count",
            )
            suggested_assistance_category = text_value(
                "suggested_assistance_category",
                "Suggested assistance category",
            )
            vulnerability = choice_value(
                "vulnerability_level",
                "Vulnerability level",
                ["Low", "Moderate", "High"],
            )
            household_status = choice_value(
                "household_status",
                "Household registration status",
                ["Registered", "Pending", "Inactive"],
            )
        submitted = st.form_submit_button(submit_label, type="primary")

    form_values: dict[str, object] = {
        "household_id": household_id,
        "household_head_name": household_head_name,
        "household_address": household_address,
        "barangay": barangay,
        "purok": purok,
        "contact_number": contact_number,
        "date_registered": date_registered.isoformat() if date_registered else None,
        "household_members": int(household_members),
        "household_head_age": int(head_age) if head_age else None,
        "dependents": int(dependents),
        "monthly_income_php": float(monthly_income) if monthly_income else None,
        "housing_status": housing_status,
        "water_access": water_access,
        "electricity_access": electricity_access,
        "assistance_program": assistance_program,
        "employment_status": employment_status,
        "age_group_profile": age_group_profile,
        "senior_citizens_count": int(senior_citizens_count),
        "pwd_count": int(pwd_count),
        "suggested_assistance_category": suggested_assistance_category,
        "vulnerability_level": vulnerability,
        "household_status": household_status,
    }
    return form_values, submitted


def resident_form(
    initial: dict[str, object] | None,
    household_ids: list[str],
    *,
    form_key: str,
    submit_label: str,
) -> tuple[dict[str, object], bool]:
    values = initial or {}
    with st.form(form_key):
        first, second = st.columns(2)
        with first:
            resident_id = st.text_input(
                "Resident ID",
                value=str(values.get("resident_id") or ""),
                key=f"{form_key}_resident_id",
            )
            full_name = st.text_input(
                "Full name",
                value=str(values.get("full_name") or ""),
                key=f"{form_key}_full_name",
            )
            sex_options = ["Female", "Male", "Other", "Not recorded"]
            sex_value = str(values.get("sex") or "Not recorded")
            sex = st.selectbox(
                "Sex",
                sex_options,
                index=sex_options.index(sex_value)
                if sex_value in sex_options
                else len(sex_options) - 1,
                key=f"{form_key}_sex",
            )
            birth_date_value = values.get("date_of_birth")
            birth_date = st.date_input(
                "Date of birth",
                value=(
                    date.fromisoformat(str(birth_date_value))
                    if birth_date_value
                    else None
                ),
                key=f"{form_key}_date_of_birth",
            )
            civil_options = DEFAULT_CIVIL_STATUSES
            civil_value = str(values.get("civil_status") or "Not recorded")
            civil_status = st.selectbox(
                "Civil status",
                civil_options,
                index=civil_options.index(civil_value)
                if civil_value in civil_options
                else len(civil_options) - 1,
                key=f"{form_key}_civil_status",
            )
        with second:
            if not household_ids:
                st.warning("Add a household record before registering a resident.")
            household_value = str(values.get("household_id") or "")
            household_id = st.selectbox(
                "Household",
                household_ids or [""],
                index=household_ids.index(household_value)
                if household_value in household_ids
                else 0,
                key=f"{form_key}_household_id",
                disabled=not household_ids,
            )
            occupation = st.text_input(
                "Occupation",
                value=str(values.get("occupation") or ""),
                key=f"{form_key}_occupation",
            )
            education_options = DEFAULT_EDUCATION_LEVELS
            education_value = str(
                values.get("educational_attainment") or "Not recorded"
            )
            education = st.selectbox(
                "Educational attainment",
                education_options,
                index=education_options.index(education_value)
                if education_value in education_options
                else len(education_options) - 1,
                key=f"{form_key}_educational_attainment",
            )
            contact_number = st.text_input(
                "Contact number",
                value=str(values.get("contact_number") or ""),
                key=f"{form_key}_contact_number",
            )
            pwd_options = ["Not recorded", "No", "Yes"]
            pwd_value = str(values.get("pwd_status") or "Not recorded")
            pwd_status = st.selectbox(
                "PWD status",
                pwd_options,
                index=pwd_options.index(pwd_value)
                if pwd_value in pwd_options
                else 0,
                key=f"{form_key}_pwd_status",
            )
        submitted = st.form_submit_button(
            submit_label,
            type="primary",
            disabled=not household_ids,
        )

    return (
        {
            "resident_id": resident_id,
            "full_name": full_name,
            "sex": None if sex == "Not recorded" else sex,
            "date_of_birth": birth_date.isoformat() if birth_date else None,
            "civil_status": None if civil_status == "Not recorded" else civil_status,
            "occupation": occupation,
            "educational_attainment": (
                None if education == "Not recorded" else education
            ),
            "household_id": household_id,
            "contact_number": contact_number,
            "pwd_status": None if pwd_status == "Not recorded" else pwd_status,
        },
        submitted,
    )


def report_summary(
    household_data: pd.DataFrame,
    resident_data: pd.DataFrame,
    summary: dict[str, object],
) -> None:
    st.subheader("Current data scope")
    left, right = st.columns(2)
    with left:
        st.write(f"Household records: **{len(household_data):,}**")
        population = summary["total_population"]
        average_size = summary["average_household_size"]
        st.write(
            f"Recorded household members: **{population:,}**"
            if population is not None
            else "Recorded household members: **Unavailable**"
        )
        st.write(
            f"Average recorded household size: **{average_size:.1f}**"
            if average_size is not None
            else "Average recorded household size: **Unavailable**"
        )
    with right:
        st.write(f"Individual resident records: **{len(resident_data):,}**")
        st.write(f"Individually recorded male residents: **{summary['male_residents'] if summary['male_residents'] is not None else 'N/A'}**")
        st.write(f"Individually recorded female residents: **{summary['female_residents'] if summary['female_residents'] is not None else 'N/A'}**")
        seniors = summary["senior_citizens"]
        pwd_count = summary["pwd_residents"]
        st.write(
            f"Source-recorded senior citizens: **{seniors:,}**"
            if seniors is not None
            else "Source-recorded senior citizens: **Unavailable**"
        )
        st.write(
            f"Source-recorded PWD members: **{pwd_count:,}**"
            if pwd_count is not None
            else "Source-recorded PWD members: **Unavailable**"
        )


try:
    source_households = load_households_csv(SOURCE_PATH)
    db_path = current_database_path()
    initial_records = source_households.astype(object).where(
        source_households.notna(), None
    )
    initialize_database(db_path, initial_records.to_dict(orient="records"))
    households = records_to_frame(
        list_households(db_path),
        columns=HOUSEHOLD_FIELDS,
    )
    residents = records_to_frame(
        list_residents(db_path),
        columns=RESIDENT_FIELDS + ["barangay", "purok"],
    )
except (OSError, sqlite3.Error, UnicodeError, pd.errors.EmptyDataError, pd.errors.ParserError, ValueError) as exc:
    st.error(
        f"Unable to load household records or initialize the database: {exc}",
        icon=":material/error:",
    )
    st.stop()

zones = sorted(
    {
        str(value)
        for value in add_area_label(households)["area_label"].dropna()
        if str(value).strip()
    }
)
housing_statuses = sorted(
    {
        str(value)
        for value in households.get("household_status", pd.Series(dtype="object")).dropna()
        if str(value).strip()
    }
    | {"Not recorded"}
)
resident_sexes = sorted(
    {
        str(value)
        for value in residents.get("sex", pd.Series(dtype="object")).dropna()
        if str(value).strip()
    }
    | set(SEX_OPTIONS)
)
resident_civil_statuses = sorted(
    {
        str(value)
        for value in residents.get("civil_status", pd.Series(dtype="object")).dropna()
        if str(value).strip()
    }
    | set(DEFAULT_CIVIL_STATUSES)
)
resident_education = sorted(
    {
        str(value)
        for value in residents.get(
            "educational_attainment", pd.Series(dtype="object")
        ).dropna()
        if str(value).strip()
    }
    | set(DEFAULT_EDUCATION_LEVELS)
)
household_age_profiles = sorted(
    {
        str(value)
        for value in households["age_group_profile"].dropna()
        if str(value).strip()
    }
    | {"Not recorded"}
)
household_ids_for_filter = sorted(households["household_id"].astype(str).tolist())
filter_defaults = {
    "zone": zones,
    "sex": resident_sexes,
    "age_group": AGE_GROUPS,
    "age_profile": household_age_profiles,
    "civil_status": resident_civil_statuses,
    "education": resident_education,
    "household_status": housing_statuses,
    "household_id": household_ids_for_filter,
}

with st.sidebar:
    st.title("Barangay dashboard", icon=":material/home_work:")
    st.caption("Household management and community analytics")
    page = st.radio(
        "Navigation",
        options=list(NAVIGATION),
        format_func=lambda label: f":material/{NAVIGATION[label]}:  {label}",
    )
    st.subheader("Dashboard filters")
    if st.button(
        "Reset filters",
        icon=":material/filter_alt_off:",
        width="stretch",
    ):
        reset_filters(filter_defaults)

    selected_zones = st.multiselect(
        "Barangay / zone",
        zones,
        default=filter_defaults["zone"],
        key=FILTER_KEYS["zone"],
    )
    selected_sexes = st.multiselect(
        "Sex (resident records)",
        resident_sexes,
        default=filter_defaults["sex"],
        key=FILTER_KEYS["sex"],
    )
    selected_age_groups = st.multiselect(
        "Age group (resident records)",
        AGE_GROUPS,
        default=filter_defaults["age_group"],
        key=FILTER_KEYS["age_group"],
    )
    selected_age_profiles = st.multiselect(
        "Household age-group profile (source)",
        household_age_profiles,
        default=filter_defaults["age_profile"],
        key=FILTER_KEYS["age_profile"],
    )
    selected_civil_status = st.multiselect(
        "Civil status (resident records)",
        resident_civil_statuses,
        default=filter_defaults["civil_status"],
        key=FILTER_KEYS["civil_status"],
    )
    selected_education = st.multiselect(
        "Education (resident records)",
        resident_education,
        default=filter_defaults["education"],
        key=FILTER_KEYS["education"],
    )
    selected_household_status = st.multiselect(
        "Household registration status",
        housing_statuses,
        default=filter_defaults["household_status"],
        key=FILTER_KEYS["household_status"],
    )
    selected_household_ids = st.multiselect(
        "Household (resident records)",
        household_ids_for_filter,
        default=filter_defaults["household_id"],
        key=FILTER_KEYS["household_id"],
    )
    st.caption(
        "Household totals use household records. Demographics use individually "
        "registered residents and may not represent every person in the barangay."
    )

filtered_households = filter_households(
    households,
    zones=selected_zones,
    household_statuses=selected_household_status,
    age_profiles=selected_age_profiles,
)
filtered_residents = filter_residents(
    residents,
    households=filtered_households,
    sexes=selected_sexes,
    age_groups=selected_age_groups,
    civil_statuses=selected_civil_status,
    education_levels=selected_education,
    household_ids=selected_household_ids,
)
summary = dashboard_summary(filtered_households, filtered_residents)
insights = household_insights(filtered_households, filtered_residents)

if page == "Dashboard overview":
    st.title("Dashboard overview", icon=":material/dashboard:")
    st.caption(
        "Household totals reflect the supplied household register; resident-level "
        "demographics are shown only when individual records are available."
    )
    if len(residents) == 0:
        st.info(
            "No individual resident records are present in the supplied dataset. "
            "Male/female counts and child counts are unavailable. Senior-citizen "
            "and PWD totals below use the dataset's household-level aggregate fields."
        )
    kpi_values = [
        ("Registered households", summary["total_households"], "household"),
        ("Recorded population", summary["total_population"], "population"),
        ("Male residents in registry", summary["male_residents"], "male"),
        ("Female residents in registry", summary["female_residents"], "female"),
        ("Children in resident registry", summary["children"], "children"),
        ("Senior citizens (source count)", summary["senior_citizens"], "senior"),
        ("PWD members (source count)", summary["pwd_residents"], "pwd"),
        ("Registered families", summary["registered_families"], "families"),
        ("Average household size", summary["average_household_size"], "average"),
    ]
    for offset in range(0, len(kpi_values), 3):
        with st.container(horizontal=True):
            for label, value, metric_key in kpi_values[offset : offset + 3]:
                display_value = (
                    "N/A"
                    if value is None
                    else f"{value:,.1f}"
                    if isinstance(value, float) and not value.is_integer()
                    else f"{value:,.0f}"
                    if isinstance(value, (int, float))
                    else str(value)
                )
                st.metric(
                    label,
                    display_value,
                    help=summary.get(f"{metric_key}_help"),
                    border=True,
                )

    if filtered_households.empty:
        st.info("No households match the selected zone and registration-status filters.")
    else:
        charts_left, charts_right = st.columns(2)
        with charts_left:
            household_areas = add_area_label(filtered_households)
            zone_households = (
                household_areas.groupby("area_label", dropna=False)
                .size()
                .rename("Households")
                .reset_index()
                .rename(columns={"area_label": "Purok / barangay"})
                .sort_values("Households", ascending=False)
            )
            with st.container(border=True):
                st.subheader("Households by Purok / zone")
                chart = px.bar(
                    zone_households,
                    x="Purok / barangay",
                    y="Households",
                    text="Households",
                )
                show_plotly_chart(
                    chart,
                    "overview-households-by-zone",
                    "Household record counts by Purok or zone",
                )
        with charts_right:
            profiles = (
                filtered_households["suggested_assistance_category"]
                .fillna("Not recorded")
                .value_counts()
                .rename_axis("Suggested assistance category")
                .reset_index(name="Households")
            )
            with st.container(border=True):
                st.subheader("Suggested assistance categories")
                chart = px.bar(
                    profiles,
                    x="Households",
                    y="Suggested assistance category",
                    orientation="h",
                    text="Households",
                    labels={
                        "Suggested assistance category": "Recorded category",
                    },
                )
                show_plotly_chart(
                    chart,
                    "overview-assistance-categories",
                    "Household counts by the source suggested assistance category",
                )
        st.subheader("Data-based observations")
        if insights:
            for observation in insights:
                st.markdown(f"- {observation}")
        else:
            st.caption("No observations can be calculated from the current filters.")
        st.caption(
            "These are descriptive observations, not eligibility decisions or "
            "causal findings."
        )

elif page == "Household records":
    st.title("Household records", icon=":material/home:")
    search_household = st.text_input(
        "Search by household ID or household head",
        placeholder="Search ID or recorded household-head name",
    )
    household_view = filtered_households.copy()
    search_value = search_household.strip()
    if search_value:
        household_view = household_view[
            household_view["household_id"].astype("string").str.contains(
                search_value, case=False, na=False, regex=False
            )
            | household_view["household_head_name"].astype("string").str.contains(
                search_value, case=False, na=False, regex=False
            )
        ]
    st.caption(
        "The source contains Purok, member counts, income, employment, age-group "
        "profiles, senior/PWD aggregate counts, utilities, housing type, and "
        "suggested assistance. Head name, address, contact, and registration date "
        "remain blank until entered."
    )
    with st.expander("Add a household"):
        new_household, submitted = household_form(
            form_key="add_household",
            submit_label="Add household",
        )
        if submitted:
            errors = validate_household(new_household)
            if errors:
                st.error("Please correct the following: " + "; ".join(errors))
            else:
                try:
                    create_household(db_path, new_household)
                    st.success("Household record added.")
                    st.rerun()
                except sqlite3.IntegrityError as exc:
                    st.error(f"Could not add household: {exc}")

    st.subheader(f"Households in current view: {len(household_view):,}")
    if household_view.empty:
        st.info("No household records match the current search and filters.")
    else:
        display_households(household_view, "Filtered household management records")
        st.download_button(
            "Download household records as CSV",
            data=household_view.to_csv(index=False).encode("utf-8"),
            file_name="barangay_households.csv",
            mime="text/csv",
        )

    if not household_view.empty:
        household_ids = household_view["household_id"].astype(str).tolist()
        st.subheader("Edit household")
        edit_household_id = st.selectbox(
            "Select household to edit",
            household_ids,
            key="edit_household_selector",
        )
        original = household_view.loc[
            household_view["household_id"].astype(str) == edit_household_id
        ].iloc[0].to_dict()
        updated, submitted = household_form(
            original,
            form_key="edit_household",
            submit_label="Save household changes",
        )
        if submitted:
            errors = validate_household(updated)
            if errors:
                st.error("Please correct the following: " + "; ".join(errors))
            else:
                try:
                    update_household(db_path, edit_household_id, updated)
                    st.success("Household record updated.")
                    st.rerun()
                except (sqlite3.IntegrityError, LookupError) as exc:
                    st.error(f"Could not update household: {exc}")

        with st.expander("Delete household"):
            st.warning(
                "Deleting a household is permanent. A household linked to resident "
                "records cannot be deleted until those records are reassigned or removed."
            )
            confirm_delete = st.checkbox(
                f"I confirm deletion of {edit_household_id}",
                key="confirm_delete_household",
            )
            if st.button(
                "Delete selected household",
                type="secondary",
                disabled=not confirm_delete,
            ):
                try:
                    delete_household(db_path, edit_household_id)
                    st.success("Household record deleted.")
                    st.rerun()
                except (sqlite3.IntegrityError, LookupError) as exc:
                    st.error(f"Could not delete household: {exc}")

elif page == "Resident records":
    st.title("Resident records", icon=":material/groups:")
    st.warning(
        "Resident records include personal information. Restrict access to this "
        "page and do not publish identifiable records in a public deployment."
    )
    if residents.empty:
        st.info(
            "No resident records exist in the source dataset. The resident register "
            "starts empty; add only verified information."
        )
    resident_search = st.text_input(
        "Search residents",
        placeholder="Resident ID or full name",
    )
    resident_view = filtered_residents.copy()
    if resident_search.strip():
        term = resident_search.strip()
        resident_view = resident_view[
            resident_view["resident_id"].astype("string").str.contains(
                term, case=False, na=False, regex=False
            )
            | resident_view["full_name"].astype("string").str.contains(
                term, case=False, na=False, regex=False
            )
        ]
    resident_households = sorted(
        filtered_households["household_id"].astype(str).unique().tolist()
    )
    with st.expander("Add a resident"):
        new_resident, submitted = resident_form(
            None,
            resident_households,
            form_key="add_resident",
            submit_label="Add resident",
        )
        if submitted:
            errors = validate_resident(new_resident)
            if errors:
                st.error("Please correct the following: " + "; ".join(errors))
            else:
                try:
                    create_resident(db_path, new_resident)
                    st.success("Resident record added.")
                    st.rerun()
                except sqlite3.IntegrityError as exc:
                    st.error(f"Could not add resident: {exc}")

    st.subheader(f"Residents in current view: {len(resident_view):,}")
    if resident_view.empty:
        st.caption(
            "Resident demographic counts are unavailable for this view until matching "
            "individual records have been entered."
        )
    else:
        display_residents(resident_view, "Filtered resident register")
        st.download_button(
            "Download resident records as CSV",
            data=resident_view.to_csv(index=False).encode("utf-8"),
            file_name="barangay_residents.csv",
            mime="text/csv",
        )

    if not resident_view.empty:
        resident_ids = resident_view["resident_id"].astype(str).tolist()
        selected_resident_id = st.selectbox(
            "Select resident to edit or delete",
            resident_ids,
            key="edit_resident_selector",
        )
        resident_initial = resident_view.loc[
            resident_view["resident_id"].astype(str) == selected_resident_id
        ].iloc[0].to_dict()
        edited_resident, submitted = resident_form(
            resident_initial,
            sorted(households["household_id"].astype(str).tolist()),
            form_key="edit_resident",
            submit_label="Save resident changes",
        )
        if submitted:
            errors = validate_resident(edited_resident)
            if errors:
                st.error("Please correct the following: " + "; ".join(errors))
            else:
                try:
                    update_resident(db_path, selected_resident_id, edited_resident)
                    st.success("Resident record updated.")
                    st.rerun()
                except (sqlite3.IntegrityError, LookupError) as exc:
                    st.error(f"Could not update resident: {exc}")

        with st.expander("Delete resident"):
            st.warning("Deleting a resident record is permanent.")
            confirm = st.checkbox(
                f"I confirm deletion of {selected_resident_id}",
                key="confirm_delete_resident",
            )
            if st.button("Delete selected resident", disabled=not confirm):
                try:
                    delete_resident(db_path, selected_resident_id)
                    st.success("Resident record deleted.")
                    st.rerun()
                except LookupError as exc:
                    st.error(f"Could not delete resident: {exc}")

elif page == "Population analytics":
    st.title("Population analytics", icon=":material/query_stats:")
    st.caption(
        "Household aggregates and individual resident-register counts are shown "
        "separately. Age_Group_Profile is a household category, not a count of people."
    )
    if filtered_residents.empty:
        st.info(
            "There are no individual resident records for sex, exact age, civil "
            "status, education, or occupation analysis. Household-level source "
            "aggregates are available below."
        )
        household_profiles = (
            filtered_households["age_group_profile"]
            .fillna("Not recorded")
            .value_counts()
            .rename_axis("Household age-group profile")
            .reset_index(name="Households")
        )
        profile_chart = px.bar(
            household_profiles,
            x="Household age-group profile",
            y="Households",
            title="Households by recorded age-group profile",
            text="Households",
        )
        show_plotly_chart(
            profile_chart,
            "analytics-household-age-profile",
            "Household counts by the source age-group profile category",
        )
    else:
        resident_charts = [
            (
                "Population by sex",
                filtered_residents["sex"].fillna("Not recorded"),
                "Sex",
                "analytics-sex",
            ),
            (
                "Population by age group",
                filtered_residents["age_group"].fillna("Not recorded"),
                "Age group",
                "analytics-age",
            ),
            (
                "Civil status distribution",
                filtered_residents["civil_status"].fillna("Not recorded"),
                "Civil status",
                "analytics-civil",
            ),
            (
                "Educational attainment",
                filtered_residents["educational_attainment"].fillna("Not recorded"),
                "Educational attainment",
                "analytics-education",
            ),
            (
                "Occupation distribution",
                filtered_residents["occupation"].replace("", pd.NA).fillna("Not recorded"),
                "Occupation",
                "analytics-occupation",
            ),
        ]
        for title, series, label, key in resident_charts:
            counts = (
                series.value_counts()
                .rename_axis(label)
                .reset_index(name="Residents")
            )
            chart = px.bar(
                counts,
                x=label,
                y="Residents",
                color=label,
                title=title,
                text="Residents",
            )
            show_plotly_chart(
                chart,
                key,
                f"Individual resident record counts by {label.casefold()}",
            )

        residents_with_area = add_area_label(filtered_residents)

    if not filtered_households.empty:
        household_left, household_right = st.columns(2)
        with household_left:
            by_zone = (
                add_area_label(filtered_households)
                .groupby("area_label", dropna=False)
                .size()
                .rename("Households")
                .reset_index()
                .rename(columns={"area_label": "Purok / barangay"})
            )
            chart = px.bar(
                by_zone,
                x="Purok / barangay",
                y="Households",
                title="Households by Purok / zone",
                text="Households",
            )
            show_plotly_chart(
                chart,
                "analytics-households-zone",
                "Household records by Purok or zone",
            )
        with household_right:
            by_zone_population = (
                add_area_label(filtered_households)
                .groupby("area_label", dropna=False)[
                    "household_members"
                ]
                .sum()
                .rename("Recorded household members")
                .reset_index()
                .rename(columns={"area_label": "Purok / barangay"})
            )
            chart = px.bar(
                by_zone_population,
                x="Purok / barangay",
                y="Recorded household members",
                title="Recorded household members by Purok / zone",
            )
            show_plotly_chart(
                chart,
                "analytics-population-zone",
                "Sum of household member counts by Purok or zone",
            )
        special_left, special_right = st.columns(2)
        with special_left:
            senior_counts = (
                add_area_label(filtered_households)
                .groupby("area_label", dropna=False)["senior_citizens_count"]
                .sum()
                .rename("Recorded senior citizens")
                .reset_index()
                .rename(columns={"area_label": "Purok / barangay"})
            )
            senior_chart = px.bar(
                senior_counts,
                x="Purok / barangay",
                y="Recorded senior citizens",
                title="Senior-citizen counts by Purok / zone",
            )
            show_plotly_chart(
                senior_chart,
                "analytics-seniors",
                "Source-reported senior-citizen counts by Purok or zone",
            )
        with special_right:
            pwd_counts = (
                add_area_label(filtered_households)
                .groupby("area_label", dropna=False)["pwd_count"]
                .sum()
                .rename("Recorded PWD members")
                .reset_index()
                .rename(columns={"area_label": "Purok / barangay"})
            )
            pwd_chart = px.bar(
                pwd_counts,
                x="Purok / barangay",
                y="Recorded PWD members",
                title="PWD counts by Purok / zone",
            )
            show_plotly_chart(
                pwd_chart,
                "analytics-pwd",
                "Source-reported PWD counts by Purok or zone",
            )
        size_counts = (
            filtered_households["household_members"]
            .value_counts()
            .sort_index()
            .rename_axis("Household members")
            .reset_index(name="Households")
        )
        size_chart = px.bar(
            size_counts,
            x="Household members",
            y="Households",
            title="Household size distribution",
            text="Households",
        )
        show_plotly_chart(
            size_chart,
            "analytics-household-size",
            "Households grouped by recorded household member count",
        )

    st.subheader("Data availability")
    st.write(
        f"Household-level records: **{len(filtered_households):,}**. "
        f"Individual resident records: **{len(filtered_residents):,}**."
    )
    if residents.empty:
        st.caption(
            "Sex, individual age, civil status, education, and occupation charts "
            "require an individual resident register. Senior and PWD totals above "
            "come from the source household aggregate fields."
        )

elif page == "Reports and downloads":
    st.title("Reports and downloads", icon=":material/download:")
    st.caption(
        "Report summaries distinguish household register counts from individual "
        "resident registry counts."
    )
    report_summary(filtered_households, filtered_residents, summary)
    st.download_button(
        "Download household CSV",
        data=filtered_households.to_csv(index=False).encode("utf-8"),
        file_name="barangay_households.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download resident CSV",
        data=filtered_residents.to_csv(index=False).encode("utf-8"),
        file_name="barangay_residents.csv",
        mime="text/csv",
    )
    report = build_pdf_report(
        filtered_households,
        filtered_residents,
        summary=summary,
        insights=insights,
    )
    st.download_button(
        "Download dashboard PDF report",
        data=report,
        file_name="barangay_household_dashboard_report.pdf",
        mime="application/pdf",
        type="primary",
    )
    st.subheader("Household records included")
    display_households(filtered_households, "Household records included in this report")
    st.subheader("Individual resident records included")
    if filtered_residents.empty:
        st.info("No individual resident records are included in this report.")
    else:
        display_residents(
            filtered_residents,
            "Individual resident records included in this report",
        )

elif page == "System information":
    st.title("System information", icon=":material/settings:")
    st.subheader("Data sources and scope")
    st.write(
        "- Household records are initialized from `data/barangay_households.csv` "
        "when the local SQLite database is first created.\n"
        "- The source file contains household-level totals, not individual resident records.\n"
        "- Resident demographic metrics are based only on verified records added "
        "to the resident register.\n"
        "- The source README identifies the included data as fictional demonstration data."
    )
    st.subheader("Database")
    st.code(str(db_path), language="text")
    st.write("Database engine: SQLite with foreign-key enforcement.")
    st.write(
        "Set `BARANGAY_DB_PATH` to choose another writable SQLite file. The database "
        "is seeded from the CSV once; subsequent CRUD changes are not overwritten."
    )
    st.warning(
        "Streamlit Community Cloud's local filesystem is not persistent. CRUD changes "
        "stored in this SQLite file can be lost when the app restarts or redeploys. "
        "Use a persistent hosted database for production records."
    )
    st.warning(
        "This app has no authentication or role-based access control. Do not deploy "
        "real names, dates of birth, addresses, contact numbers, or PWD information "
        "to a public app without a secured access layer and appropriate data governance."
    )
    st.subheader("Data quality")
    st.write(f"Household records loaded: **{len(households):,}**")
    st.write(f"Individual resident records stored: **{len(residents):,}**")
    st.write(f"Duplicate household IDs in the source are rejected during initialization.")
    st.write(f"Source file: `{SOURCE_PATH.name}`")

st.caption(
    "Barangay household dashboard · Descriptive information for planning support; "
    "verify records before official decisions."
)
