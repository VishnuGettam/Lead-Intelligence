import pandas as pd

REQUIRED_COLUMNS = [
    "name",
    "company",
    "company_size",
    "industry",
    "source",
    "last_interaction_date",
]

DATE_FORMAT = "%d-%m-%Y"  # matches raw input format (see cleaner.py)


def validate_columns(df: pd.DataFrame) -> list[str]:
    """
    Validate if the required columns are present in the dataframe.
    """
    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]
    return missing_columns


def validate_leads(df: pd.DataFrame) -> pd.DataFrame:
    """Validate individual lead records (vectorized)."""

    df = df.reset_index(drop=True)
    errors_per_row = [[] for _ in range(len(df))]

    # 1. Validate name
    missing_name = df["name"].isna() | (df["name"].astype(str).str.strip() == "")
    for i in df.index[missing_name]:
        errors_per_row[i].append("Missing name")

    # 2. Validate company_size
    missing_company_size = df["company_size"].isna()
    company_size_numeric = pd.to_numeric(df["company_size"], errors="coerce")
    invalid_company_size = ~missing_company_size & (company_size_numeric.isna() | (company_size_numeric <= 0))

    for i in df.index[missing_company_size]:
        errors_per_row[i].append("Missing company_size")
    for i in df.index[invalid_company_size]:
        errors_per_row[i].append("Invalid company_size")

    # 3. Validate industry
    missing_industry = df["industry"].isna() | (df["industry"].astype(str).str.strip() == "")
    for i in df.index[missing_industry]:
        errors_per_row[i].append("Missing industry")

    # 4. Validate source
    missing_source = df["source"].isna() | (df["source"].astype(str).str.strip() == "")
    for i in df.index[missing_source]:
        errors_per_row[i].append("Missing source")

    # 5. Validate last_interaction_date
    missing_date = df["last_interaction_date"].isna()
    parsed_dates = pd.to_datetime(df["last_interaction_date"], format=DATE_FORMAT, errors="coerce")
    invalid_date = ~missing_date & parsed_dates.isna()

    for i in df.index[missing_date]:
        errors_per_row[i].append("Missing last_interaction_date")
    for i in df.index[invalid_date]:
        errors_per_row[i].append("Invalid last_interaction_date")

    validation_results = pd.DataFrame({
        "row_number": df.index + 1,
        "is_valid": [len(e) == 0 for e in errors_per_row],
        "errors": errors_per_row,
    })

    return validation_results
