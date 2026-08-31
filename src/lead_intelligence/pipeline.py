from lead_intelligence.ingestion.csv_reader import read_leads
from lead_intelligence.validation.validator import (
    validate_columns,
    validate_leads
)

from lead_intelligence.transformation.cleaner import clean_leads
from lead_intelligence.qualification.rubric import (
    qualify_leads,
    assign_priority_rank
)
import datetime



def main():

    leads_path = "data/raw/leads_training.csv"

    # ========================================================
    # 1. INGESTION
    # ========================================================

    # 1.Ingestion
    leads = read_leads(leads_path)
    print(leads.head())
    print(f"Shape of the data -[rows,columns] :  {leads.shape} ")

    # ========================================================
    # 2. VALIDATION
    # ========================================================


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

    # ========================================================
    # 3. TRANSFORMATION
    # ========================================================

    # 4.Data transformations
    transformed_leads = clean_leads(leads)
    transformed_leads.to_csv("./data/processed/leads_training_tf.csv",index=False)

    # ========================================================
    # 4. QUALIFICATION
    # ========================================================

    evaluation_date = datetime.datetime(2024, 1, 20)

    qualified_leads = qualify_leads(
        transformed_leads,
        evaluation_date,
    )

    print("\nQualification completed.")

    print(
        qualified_leads[
            [
                "name",
                "company",
                "qualification_score",
                "decision",
            ]
        ]
    )


    # ========================================================
    # 5. PRIORITY RANKING
    # ========================================================

    ranked_leads = assign_priority_rank(
        qualified_leads
    )

    print("\nPriority ranking completed.")

    print(
        ranked_leads[
            [
                "name",
                "company",
                "qualification_score",
                "decision",
                "priority_rank",
            ]
        ]
    )

     # ========================================================
    # 6. SAVE PRE-LLM CHECKPOINT
    # ========================================================

    output_path = "data/processed/pre_llm_leads.csv"

    ranked_leads.to_csv(
        output_path,
        index=False,
    )

    print(
        f"\nPre-LLM data saved to: {output_path}"
    )





if __name__ == "__main__":
    main()