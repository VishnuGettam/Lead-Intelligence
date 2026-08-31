import pandas as pd 

REQUIRED_COLUMNS = [
    "name",
    "company",
    "company_size",
    "industry",
    "source",
    "last_interaction_date"
]

def validate_columns(df:pd.DataFrame) -> list[str]:
    """
    Validate if the required columns are present in the dataframe.
    """

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    return missing_columns



def validate_leads(df:pd.DataFrame) -> pd.DataFrame:
    """ Validate individual lead records  """ 

    validation_results = []

    for index,row in df.iterrows():

        errors = []

        # validate name
        if pd.isna(row["name"]) or str(row["name"]).strip() == "":
            errors.append("Missing name")

        # 3. Validate company_size
        if pd.isna(row["company_size"]):
            errors.append("Missing company_size")
        else:
            try:
                size = float(row["company_size"])

                if size <= 0:
                    errors.append("Invalid company_size")

            except (ValueError, TypeError):
                errors.append("Invalid company_size")

        # 4. Validate industry
        if pd.isna(row["industry"]) or str(row["industry"]).strip() == "":
            errors.append("Missing industry")

        # 5. Validate source
        if pd.isna(row["source"]) or str(row["source"]).strip() == "":
            errors.append("Missing source")

        # 6. Validate last_interaction_date
        if pd.isna(row["last_interaction_date"]):
            errors.append("Missing last_interaction_date")
        else:
            parsed_date = pd.to_datetime(
                row["last_interaction_date"],
                errors="coerce",
                dayfirst=True,
            )

            if pd.isna(parsed_date):
                errors.append("Invalid last_interaction_date")

        validation_results.append({
            "row_number": index + 1,
            "is_valid": len(errors) == 0,
            "errors": errors,
        })

    return pd.DataFrame(validation_results)
