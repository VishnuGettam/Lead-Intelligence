import pandas as pd


def clean_leads(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize lead data.

    Transformations:
        - Generate unique lead_id
        - Trim and standardize names
        - Trim and standardize company names
        - Convert company_size to numeric
        - Standardize industry
        - Standardize source
        - Convert interaction date to YYYY-MM-DD
    """

    # Work on a copy so the original DataFrame is not modified
    df = df.copy()

    # Reset index so lead IDs are deterministic
    df = df.reset_index(drop=True)

    # --------------------------------------------------------
    # Generate unique Lead ID
    # --------------------------------------------------------

    df.insert(
        0,
        "lead_id",
        [
            f"L{index:03d}"
            for index in range(1, len(df) + 1)
        ],
    )

    # --------------------------------------------------------
    # Clean name
    # --------------------------------------------------------

    df["name"] = (
        df["name"]
        .str.strip()
        .str.title()
    )

    # --------------------------------------------------------
    # Clean company
    # --------------------------------------------------------

    df["company"] = (
        df["company"]
        .str.strip()
        .str.title()
    )

    # --------------------------------------------------------
    # Convert company size to numeric
    # --------------------------------------------------------

    df["company_size"] = (
        pd.to_numeric(
            df["company_size"],
            errors="coerce",
        )
        .astype("Int64")
    )

    # --------------------------------------------------------
    # Clean industry
    # --------------------------------------------------------

    df["industry"] = (
        df["industry"]
        .str.strip()
        .str.title()
    )

    # --------------------------------------------------------
    # Clean source
    # --------------------------------------------------------

    df["source"] = (
        df["source"]
        .str.strip()
        .str.lower()
    )

    # --------------------------------------------------------
    # Standardize interaction date
    # --------------------------------------------------------

    df["last_interaction_date"] = (
        pd.to_datetime(
            df["last_interaction_date"],
            format="%d-%m-%Y",
            errors="coerce",
        )
        .dt.strftime("%Y-%m-%d")
    )

    return df