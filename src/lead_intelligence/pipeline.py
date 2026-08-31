from lead_intelligence.ingestion.csv_reader import read_leads
from lead_intelligence.validation.validator import (
    validate_columns,
    validate_leads
)

def main():

    leads_path = "data/raw/leads_training.csv"

    # 1.Ingestion
    leads = read_leads(leads_path)
    print(leads.head())
    print(f"Shape of the data -[rows,columns] :  {leads.shape} ")

    # 2.Schema Validation 
    missing_columns = validate_columns(leads)

    if missing_columns:
        print(f"Missing Columns : {missing_columns}")
        return

    # 3.Record Validation

    validation_results = validate_leads(leads)

    print("\nValidation Results:")
    print(validation_results)

    print(
        f"\nValid leads: "
        f"{validation_results['is_valid'].sum()}"
    )

    print(
        f"Invalid leads: "
        f"{(~validation_results['is_valid']).sum()}"
    )




if __name__ == "__main__":
    main()