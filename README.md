# Barangay Household Dashboard

Streamlit dashboard for reviewing the supplied household register, maintaining
household and resident records in SQLite, exploring available population data,
and exporting filtered CSV/PDF reports.

## Data scope and limitations

The bundled `data/barangay_households.csv` is identified by the original project
README as fictional demonstration data. It contains 300 household-level rows
with the actual columns `Household_ID`, `Purok`, `Family_Members`,
`Monthly_Household_Income_PHP`, `Employment_Status`, `Age_Group_Profile`,
`Senior_Citizens_Count`, `PWD_Count`, `Access_to_Water`,
`Access_to_Electricity`, `Housing_Type`, and
`Suggested_Assistance_Category`.

The source does **not** contain individual resident records, names, sex, dates
of birth, civil status, education, occupation, addresses, contact numbers,
barangay names, exact ages, child counts, or registered-family identifiers. As
a result:

- Recorded population and average household size use the source's
  `Family_Members` count.
- Senior citizen and PWD totals use the supplied household-level aggregate
  fields `Senior_Citizens_Count` and `PWD_Count`.
- Male/female counts, exact children counts, and registered-family totals are
  unavailable until corresponding verified data is entered or provided.
- `Age_Group_Profile` is a household category, not an individual age
  distribution; its chart counts households by profile and does not infer
  residents in each age group.
- New resident records are only created from information entered by an
  authorized user; the application does not fabricate records.

Household-level filters use Purok, household age-group profile, and registration
status. Resident demographic filters apply only to individually registered
resident records. Resident counts may not represent every person in the Purok.

## Project structure

```text
Project_2_Barangay_Household/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml
├── data/
│   └── barangay_households.csv
├── database/
│   ├── __init__.py
│   └── database.py
├── utils/
│   ├── __init__.py
│   ├── analytics.py
│   ├── data_processing.py
│   ├── reports.py
│   └── validation.py
└── tests/
    └── test_dashboard.py
```

The SQLite file is created automatically at `instance/barangay_households.sqlite3`.
The bundled CSV is imported once when the database is first initialized. Later
CRUD changes are kept in SQLite and are not overwritten from the CSV on reruns.

## Local setup (Windows PowerShell)

From this project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If PowerShell blocks environment activation, invoke the environment directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The application uses paths relative to its own files. To put the SQLite file
elsewhere, set `BARANGAY_DB_PATH` before starting Streamlit:

```powershell
$env:BARANGAY_DB_PATH = "C:\data\barangay_households.sqlite3"
python -m streamlit run app.py
```

## Run tests

```powershell
python -m unittest discover -s tests -v
```

Tests use a temporary SQLite database and do not alter the bundled dataset or
the app's normal database.

## Household and resident records

Household records retain the source CSV fields and add optional fields for
household-head name, address, purok, contact number, registration date, and
registration status. Imported records leave unavailable fields blank.

Resident records are stored in SQLite and linked to households with a foreign
key. Deleting a household with linked residents is blocked to prevent orphaned
records. Age is derived from date of birth when the record is read; age is not
stored as a value that can go stale.

## Reports and exports

The reports page exports filtered household and resident records as CSV and
generates a PDF report in memory using FPDF2. The report labels household-member
totals separately from individual resident-register counts and marks unavailable
statistics explicitly.

## GitHub

1. Keep `data/barangay_households.csv` only if you have the right to publish it
   and it contains no confidential personal information. The currently bundled
   data is labeled fictional demonstration data.
2. Do not upload `.env` files, passwords, private resident data, or
   `instance/*.sqlite3`. The project `.gitignore` excludes the local database.
3. Create or select a GitHub repository and upload the project files, including
   `requirements.txt`, `app.py`, `data/`, `database/`, and `utils/`.
4. If the repository is new, one option is to initialize Git in this project
   folder, add the reviewed files, commit them, and push to the GitHub
   repository you created.

## Streamlit Community Cloud

1. Push the project to GitHub with `requirements.txt` beside `app.py`.
2. In Community Cloud, create an app from the repository and select
   `Project_2_Barangay_Household/app.py` as the entry point when deploying from
   the capstone monorepo.
3. The included CSV is deployed with the repository and seeds a fresh SQLite
   database on first startup.
4. **Local SQLite on Community Cloud is ephemeral.** CRUD changes may be lost
   after restarts, rebuilds, or redeployments. Use a persistent managed database
   for production. No MySQL connection or credentials were present in this
   project.
5. The app does not implement login or role-based access control. Do not deploy
   real resident names, dates of birth, addresses, phone numbers, or PWD
   information to a public app. Restrict access and establish appropriate
   authorization and data-governance controls first.

## Known limitations

- The bundled source is fictional household-level demonstration data, not a
  verified resident census.
- Resident-level charts are empty/unavailable until authorized users enter
  records.
- SQLite is suitable for local development and single-instance demonstrations,
  but not persistent production storage on Community Cloud.
- Authentication, multi-user authorization, audit logs, and a hosted persistent
  database are not configured.
