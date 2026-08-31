import pandas as pd


def clean_leads(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["name"] = df["name"].str.strip().str.title()
    df["company"] = df["company"].str.strip().str.title()
    df["company_size"] = pd.to_numeric(df["company_size"], errors="coerce").astype("Int64")
    df["industry"] = df["industry"].str.strip().str.title()
    df["source"] = df["source"].str.strip().str.lower()

    df["last_interaction_date"] = pd.to_datetime(
        df["last_interaction_date"], format="%d-%m-%Y", errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    return df