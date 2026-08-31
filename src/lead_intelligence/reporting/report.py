from collections import Counter
from typing import Any

import pandas as pd


def calculate_aggregated_stats(
    leads: pd.DataFrame,
) -> dict[str, Any]:
    """
    Calculate high-level statistics for the processed leads.

    Returns:
        total_processed
        qualified_count
        rejected_count
        review_count
        qualified_percentage
    """

    total_processed = len(leads)

    qualified_count = int(
        (leads["decision"] == "qualified").sum()
    )

    rejected_count = int(
        (leads["decision"] == "rejected").sum()
    )

    review_count = int(
        (leads["decision"] == "review").sum()
    )

    qualified_percentage = (
        (qualified_count / total_processed) * 100
        if total_processed > 0
        else 0
    )

    return {
        "total_processed": total_processed,
        "qualified_count": qualified_count,
        "rejected_count": rejected_count,
        "review_count": review_count,
        "qualified_percentage": round(
            qualified_percentage,
            2,
        ),
    }


def find_common_rejection_reasons(
    leads: pd.DataFrame,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """
    Identify the most common reasons for rejected leads.

    This uses the score breakdown rather than trying to
    extract reasons from free-form LLM text.

    A factor receiving zero points is treated as a
    potential rejection reason.
    """

    rejection_reasons = []

    rejected_leads = leads[
        leads["decision"] == "rejected"
    ]

    for _, lead in rejected_leads.iterrows():

        breakdown = lead.get(
            "score_breakdown"
        )

        if not isinstance(breakdown, dict):
            continue

        for factor, score in breakdown.items():

            if score == 0:
                rejection_reasons.append(
                    factor
                )

    reason_counts = Counter(
        rejection_reasons
    )

    return [
        {
            "reason": reason,
            "count": count,
        }
        for reason, count in reason_counts.most_common(
            top_n
        )
    ]


def get_outreach_examples(
    leads: pd.DataFrame,
    number_of_examples: int = 5,
) -> list[dict[str, Any]]:
    """
    Select high-priority qualified leads as
    outreach examples.

    Returns up to 5 examples.
    """

    qualified_leads = leads[
        leads["decision"] == "qualified"
    ].sort_values(
        by="priority_rank",
        ascending=True,
    )

    examples = []

    for _, lead in qualified_leads.head(
        number_of_examples
    ).iterrows():

        examples.append(
            {
                "name": lead["name"],
                "company": lead["company"],
                "priority_rank": int(
                    lead["priority_rank"]
                ),
                "reasoning": lead.get(
                    "reasoning",
                    "",
                ),
            }
        )

    return examples


def generate_report(
    leads: pd.DataFrame,
) -> dict[str, Any]:
    """
    Generate the complete aggregated report.
    """

    stats = calculate_aggregated_stats(
        leads
    )

    rejection_reasons = (
        find_common_rejection_reasons(
            leads
        )
    )

    outreach_examples = (
        get_outreach_examples(
            leads
        )
    )

    return {
        "statistics": stats,
        "common_rejection_reasons": (
            rejection_reasons
        ),
        "outreach_examples": (
            outreach_examples
        ),
    }