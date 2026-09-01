from datetime import datetime
from pathlib import Path

import pandas as pd

from lead_intelligence.ingestion.csv_reader import read_leads

from lead_intelligence.validation.validator import (
    validate_columns,
    validate_leads,
)

from lead_intelligence.transformation.cleaner import clean_leads

from lead_intelligence.qualification.rubric import (
    qualify_leads,
    assign_priority_rank,
)

from lead_intelligence.llm.client import LLMClient

from lead_intelligence.reporting.report import (
    generate_report,
)

import json


# ============================================================
# Configuration
# ============================================================

#LEADS_PATH = "data/raw/leads_training.csv"
LEADS_PATH = "data/raw/final_leads.csv"


QUARANTINE_OUTPUT_PATH = ("data/quarantine/invalid_leads.csv")


TRANSFORMED_OUTPUT_PATH = (
    "data/processed/leads_training_tf.csv"
)

PRE_LLM_OUTPUT_PATH = (
    "data/processed/pre_llm_leads.csv"
)

FINAL_OUTPUT_PATH = (
    "data/output/final_leads.csv"
)

AGGREGATED_REPORT_PATH = (
    "data/output/aggregated_report.json"
)

# Number of leads sent to the LLM in one API call
BATCH_SIZE = 10

# Fixed date for reproducible testing
EVALUATION_DATE = datetime(2024, 1, 20)


# ============================================================
# Batch Creation
# ============================================================

def create_batches(
    leads: list[dict],
    batch_size: int,
):
    """
    Split leads into batches.

    Example:
        30 leads + batch size 10
        -> Batch 1: 10 leads
        -> Batch 2: 10 leads
        -> Batch 3: 10 leads
    """

    for start in range(
        0,
        len(leads),
        batch_size,
    ):
        yield leads[
            start:start + batch_size
        ]


# ============================================================
# LLM Batch Processing
# ============================================================

def process_llm_batches(
    leads: pd.DataFrame,
    batch_size: int,
) -> list[dict]:
    """
    Send leads to the LLM in batches.

    One API call is made per batch,
    NOT once per lead.
    """

    # --------------------------------------------------------
    # Convert DataFrame into list of dictionaries
    # --------------------------------------------------------

    lead_records = leads.to_dict(
        orient="records"
    )

    # --------------------------------------------------------
    # Create LLM client once
    # --------------------------------------------------------

    llm_client = LLMClient()

    all_results = []

    batches = list(
        create_batches(
            lead_records,
            batch_size,
        )
    )

    print(
        f"\nTotal leads for LLM: "
        f"{len(lead_records)}"
    )

    print(
        f"Batch size: {batch_size}"
    )

    print(
        f"Total batches: {len(batches)}"
    )

    # ========================================================
    # Process each batch
    # ========================================================

    for batch_number, batch in enumerate(
        batches,
        start=1,
    ):

        print(
            f"\nProcessing batch "
            f"{batch_number}/{len(batches)} "
            f"({len(batch)} leads)..."
        )

        try:

            # ------------------------------------------------
            # ONE API call for the entire batch
            # ------------------------------------------------

            results = (
                llm_client.generate_reasoning(
                    batch
                )
            )

            all_results.extend(
                results
            )

            print(
                f"Batch {batch_number} "
                f"completed successfully."
            )

        except Exception as error:

            print(
                f"Batch {batch_number} "
                f"failed: {error}"
            )

            # ------------------------------------------------
            # Fallback for failed batch
            # ------------------------------------------------

            for lead in batch:

                all_results.append(
                    {
                        "lead_id": lead.get(
                            "lead_id"
                        ),
                        "reasoning": (
                            "LLM reasoning "
                            "unavailable because "
                            "the API request failed."
                        ),
                        "outreach_message": None,
                    }
                )

    return all_results


# ============================================================
# Add LLM Results
# ============================================================

def add_llm_results(
    leads: pd.DataFrame,
    llm_results: list[dict],
) -> pd.DataFrame:
    """
    Merge LLM results into the lead DataFrame
    using the unique lead_id.

    LLM results contain:
        - lead_id
        - reasoning
        - outreach_message
    """

    # --------------------------------------------------------
    # Create lookup dictionary using lead_id
    # --------------------------------------------------------

    result_map = {
        result["lead_id"]: result
        for result in llm_results
    }

    final_leads = leads.copy()

    # --------------------------------------------------------
    # Add reasoning
    # --------------------------------------------------------

    final_leads["reasoning"] = (
        final_leads["lead_id"]
        .map(
            lambda lead_id:
                result_map.get(
                    lead_id,
                    {},
                ).get(
                    "reasoning",
                    "Reasoning not available.",
                )
        )
    )

    # --------------------------------------------------------
    # Add outreach message
    # --------------------------------------------------------

    final_leads["outreach_message"] = (
        final_leads["lead_id"]
        .map(
            lambda lead_id:
                result_map.get(
                    lead_id,
                    {},
                ).get(
                    "outreach_message",
                    None,
                )
        )
    )

    return final_leads


# ============================================================
# Main Pipeline
# ============================================================

def main():

    # ========================================================
    # 1. INGESTION
    # ========================================================

    print(
        "\n========== 1. INGESTION =========="
    )

    leads = read_leads(
        LEADS_PATH
    )

    print(
        f"Loaded {len(leads)} leads."
    )

    print(
        f"Shape of the data "
        f"[rows, columns]: "
        f"{leads.shape}"
    )


    # ========================================================
    # 2. VALIDATION
    # ========================================================

    print(
        "\n========== 2. VALIDATION =========="
    )

    # --------------------------------------------------------
    # Schema Validation
    # --------------------------------------------------------

    missing_columns = (
        validate_columns(leads)
    )

    if missing_columns:

        print(
            f"Missing columns: "
            f"{missing_columns}"
        )

        return

    print(
        "Schema validation passed."
    )

    # --------------------------------------------------------
    # Record Validation
    # --------------------------------------------------------

    validation_results = (
        validate_leads(leads)
    )

    valid_count = int(
        validation_results[
            "is_valid"
        ].sum()
    )

    invalid_count = int(
        (
            ~validation_results[
                "is_valid"
            ]
        ).sum()
    )

    print(
        f"Valid leads: {valid_count}"
    )

    print(
        f"Invalid leads: {invalid_count}"
    )

    # valid leads for transformation
    valid_leads = leads[
    validation_results["status"] == "valid"
            ].copy()

    # invalid leads to be quarantine 
    invalid_leads = leads[validation_results["status"] == "invalid"].copy()

    invalid_leads["status"] = (
    validation_results.loc[
        invalid_leads.index,
        "status"
    ].values
    )

    invalid_leads["errors"] = (
        validation_results.loc[
            invalid_leads.index,
            "errors"
        ]
        .apply(lambda errors: ", ".join(errors))
        .values
    )
        
    Path(
            QUARANTINE_OUTPUT_PATH
        ).parent.mkdir(
            parents=True,
            exist_ok=True,
        )
    
    invalid_leads.to_csv(
        QUARANTINE_OUTPUT_PATH,
        index=False,
    )



    # ========================================================
    # 3. TRANSFORMATION
    # ========================================================

    print(
        "\n========== 3. TRANSFORMATION =========="
    )

    transformed_leads = clean_leads(
        valid_leads
    )

    # --------------------------------------------------------
    # Verify lead_id was generated
    # --------------------------------------------------------

    print(
        f"Lead IDs generated: "
        f"{transformed_leads['lead_id'].notna().sum()}"
    )

    # --------------------------------------------------------
    # Save transformed data
    # --------------------------------------------------------

    Path(
        TRANSFORMED_OUTPUT_PATH
    ).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    transformed_leads.to_csv(
        TRANSFORMED_OUTPUT_PATH,
        index=False,
    )

    print(
        f"Transformed data saved to: "
        f"{TRANSFORMED_OUTPUT_PATH}"
    )


    # ========================================================
    # 4. QUALIFICATION
    # ========================================================

    print(
        "\n========== 4. QUALIFICATION =========="
    )

    qualified_leads = qualify_leads(
        transformed_leads,
        EVALUATION_DATE,
    )

    print(
        "Qualification completed."
    )

    print(
        qualified_leads[
            [
                "lead_id",
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

    print(
        "\n========== 5. PRIORITY RANKING =========="
    )

    ranked_leads = assign_priority_rank(
        qualified_leads
    )

    print(
        "Priority ranking completed."
    )

    print(
        ranked_leads[
            [
                "lead_id",
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

    print(
        "\n========== 6. PRE-LLM CHECKPOINT =========="
    )

    Path(
        PRE_LLM_OUTPUT_PATH
    ).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ranked_leads.to_csv(
        PRE_LLM_OUTPUT_PATH,
        index=False,
    )

    print(
        f"Pre-LLM data saved to: "
        f"{PRE_LLM_OUTPUT_PATH}"
    )


    # ========================================================
    # 7. LLM BATCH PROCESSING
    # ========================================================

    print(
        "\n========== 7. LLM PROCESSING =========="
    )

    llm_results = process_llm_batches(
        ranked_leads,
        BATCH_SIZE,
    )

    print(
        f"\nReceived LLM results for "
        f"{len(llm_results)} leads."
    )


    # ========================================================
    # 8. ADD LLM RESULTS
    # ========================================================

    print(
        "\n========== 8. ADDING LLM RESULTS =========="
    )

    final_leads = add_llm_results(
        ranked_leads,
        llm_results,
    )

    print(
        "LLM reasoning and outreach "
        "messages successfully added."
    )


    # ========================================================
    # 9. SAVE FINAL OUTPUT
    # ========================================================

    print(
        "\n========== 9. FINAL OUTPUT =========="
    )

    Path(
        FINAL_OUTPUT_PATH
    ).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    final_leads.to_csv(
        FINAL_OUTPUT_PATH,
        index=False,
    )

    print(
        f"Final report saved to: "
        f"{FINAL_OUTPUT_PATH}"
    )


    # ========================================================
    # 10. AGGREGATED REPORTING
    # ========================================================

    print(
        "\n========== 10. AGGREGATED REPORT =========="
    )

    report = generate_report(
        final_leads
    )

    # --------------------------------------------------------
    # Display statistics
    # --------------------------------------------------------

    print(
        "\nStatistics:"
    )

    for key, value in report[
        "statistics"
    ].items():

        print(
            f"{key}: {value}"
        )

    # --------------------------------------------------------
    # Display rejection reasons
    # --------------------------------------------------------

    print(
        "\nCommon rejection reasons:"
    )

    for reason in report[
        "common_rejection_reasons"
    ]:

        print(
            f"{reason['reason']}: "
            f"{reason['count']}"
        )

    # --------------------------------------------------------
    # Display outreach messages
    # --------------------------------------------------------

    print(
        "\nSample outreach messages:"
    )

    outreach_examples = (
        final_leads[
            (
                final_leads["decision"]
                == "qualified"
            )
            &
            (
                final_leads[
                    "outreach_message"
                ].notna()
            )
        ]
        .sort_values(
            by="priority_rank"
        )
        .head(5)
    )

    for _, lead in (
        outreach_examples.iterrows()
    ):

        print(
            f"\n{lead['lead_id']} - "
            f"{lead['company']} "
            f"(Rank {lead['priority_rank']})"
        )

        print(
            lead["outreach_message"]
        )

    # --------------------------------------------------------
    # Save aggregated report
    # --------------------------------------------------------

    Path(
        AGGREGATED_REPORT_PATH
    ).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        AGGREGATED_REPORT_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print(
        f"\nAggregated report saved to: "
        f"{AGGREGATED_REPORT_PATH}"
    )


    # ========================================================
    # 11. FINAL RESULTS
    # ========================================================

    print(
        "\n========== FINAL RESULTS =========="
    )

    print(
        final_leads[
            [
                "lead_id",
                "name",
                "company",
                "qualification_score",
                "decision",
                "priority_rank",
                "reasoning",
                "outreach_message",
            ]
        ]
    )

    print(
        "\n========== PIPELINE COMPLETED =========="
    )


# ============================================================
# Application Entry Point
# ============================================================

if __name__ == "__main__":
    main()