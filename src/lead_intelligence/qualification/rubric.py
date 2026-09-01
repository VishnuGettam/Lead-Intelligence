from datetime import datetime
from typing import Any,Hashable
import pandas as pd 


# ============================================================
# Qualification thresholds
# ============================================================

QUALIFIED_THRESHOLD = 70
REVIEW_THRESHOLD = 40


# ============================================================
# Scoring configuration
# ============================================================

# Maximum points available for each qualification factor.
SCORE_WEIGHTS = {
    "company_size": 30,
    "industry": 25,
    "source": 25,
    "recency": 20,
}


# ------------------------------------------------------------
# Company size scoring
# ------------------------------------------------------------

def score_company_size(company_size: Any) -> int:
    """
    Calculate the score based on company size.

    Scoring:
        1000+ employees  -> 30 points
        500-999          -> 25 points
        100-499          -> 20 points
        50-99            -> 10 points
        <50              -> 5 points
        Missing/invalid  -> 0 points
    """

    if company_size is None:
        return 0

    try:
        size = float(company_size)
    except (ValueError, TypeError):
        return 0

    if size <= 0:
        return 0

    if size >= 1000:
        return 30
    elif size >= 500:
        return 25
    elif size >= 100:
        return 20
    elif size >= 50:
        return 10
    else:
        return 5


# ------------------------------------------------------------
# Industry scoring
# ------------------------------------------------------------

def score_industry(industry: Any) -> int:
    """
    Calculate the score based on industry.

    Target industries for this initial rubric:
        SaaS
        Technology
        Finance
        Healthcare

    Scoring:
        Target industry     -> 25 points
        Adjacent industry   -> 15 points
        Unknown              -> 5 points
        Clearly unsuitable  -> 0 points
    """

    if industry is None:
        return 0

    industry = str(industry).strip().lower()

    if not industry:
        return 0

    target_industries = {
        "saas",
        "technology",
        "finance",
        "healthcare",
    }

    adjacent_industries = {
        "fintech",
        "software",
        "information technology",
        "retail",
        "e-commerce",
    }

    unsuitable_industries = {
        "government",
        "non-profit",
        "nonprofit",
    }

    if industry in target_industries:
        return 25

    if industry in adjacent_industries:
        return 15

    if industry in unsuitable_industries:
        return 0

    return 5


# ------------------------------------------------------------
# Lead source scoring
# ------------------------------------------------------------

def score_source(source: Any) -> int:
    """
    Calculate the score based on the lead source.

    Scoring:
        Inbound demo request -> 25
        Referral             -> 22
        Content download     -> 15
        LinkedIn outreach    -> 10
        Other                -> 5
        Missing              -> 0
    """

    if source is None:
        return 0

    source = str(source).strip().lower()

    if not source:
        return 0

    source_scores = {
        "inbound demo request": 25,
        "referral": 22,
        "content download": 15,
        "linkedin outreach": 10,
    }

    return source_scores.get(source, 5)


# ------------------------------------------------------------
# Interaction recency scoring
# ------------------------------------------------------------

def score_recency(
    last_interaction_date: Any,
    evaluation_date: datetime,
) -> int:
    """
    Calculate the score based on how recently the lead interacted.

    Scoring:
        0-7 days      -> 20 points
        8-30 days     -> 15 points
        31-90 days    -> 10 points
        91-180 days   -> 5 points
        180+ days     -> 0 points
        Missing/invalid -> 0 points
    """

    if last_interaction_date is None:
        return 0

    try:
        if isinstance(last_interaction_date, datetime):
            interaction_date = last_interaction_date
        else:
            interaction_date = datetime.strptime(
                str(last_interaction_date).strip(),
                "%d-%m-%Y",
            )
    except (ValueError, TypeError):
        return 0

    days_since_interaction = (
        evaluation_date.date() - interaction_date.date()
    ).days

    # Future interaction dates should not receive a recency score.
    if days_since_interaction < 0:
        return 0

    if days_since_interaction <= 7:
        return 20
    elif days_since_interaction <= 30:
        return 15
    elif days_since_interaction <= 90:
        return 10
    elif days_since_interaction <= 180:
        return 5
    else:
        return 0


# ============================================================
# Decision logic
# ============================================================

def get_decision(score: int) -> str:
    """
    Convert the numerical score into a qualification decision.

        80-100 -> qualified
        50-79  -> review
        0-49   -> rejected
    """

    if score >= QUALIFIED_THRESHOLD:
        return "qualified"

    if score >= REVIEW_THRESHOLD:
        return "review"

    return "rejected"


# ============================================================
# Main qualification function
# ============================================================

def qualify_lead(
    lead: dict[Hashable, Any],
    evaluation_date: datetime,
) -> dict[str, Any]:
    """
    Qualify a single lead using the qualification rubric.

    Parameters
    ----------
    lead:
        Dictionary containing the lead information.

    evaluation_date:
        Date against which interaction recency is calculated.

    Returns
    -------
    dict:
        Qualification result containing:
        - score
        - decision
        - score breakdown
    """

    company_size_score = score_company_size(
        lead.get("company_size")
    )

    industry_score = score_industry(
        lead.get("industry")
    )

    source_score = score_source(
        lead.get("source")
    )

    recency_score = score_recency(
        lead.get("last_interaction_date"),
        evaluation_date,
    )

    total_score = (
        company_size_score
        + industry_score
        + source_score
        + recency_score
    )

    decision = get_decision(total_score)

    return {
        "score": total_score,
        "decision": decision,
        "breakdown": {
            "company_size": company_size_score,
            "industry": industry_score,
            "source": source_score,
            "recency": recency_score,
        },
    }

def qualify_leads(
    leads: pd.DataFrame,
    evaluation_date: datetime,
) -> pd.DataFrame:
    """
    Apply the qualification rubric to all leads.

    Returns the original lead data with:
        - qualification_score
        - decision
        - score_breakdown
    """

    qualification_results = []

    for _, lead in leads.iterrows():

        result = qualify_lead(
            lead.to_dict(),
            evaluation_date,
        )

        qualification_results.append(result)

    results_df = pd.DataFrame(qualification_results)

    # Add qualification results to the original lead data
    qualified_leads = leads.reset_index(drop=True).copy()

    qualified_leads["qualification_score"] = (
        results_df["score"]
    )

    qualified_leads["decision"] = (
        results_df["decision"]
    )

    qualified_leads["score_breakdown"] = (
        results_df["breakdown"]
    )

    return qualified_leads



def assign_priority_rank(
    qualified_leads: pd.DataFrame,
) -> pd.DataFrame:
    """
    Assign priority rank based on qualification score.

    Highest score gets rank 1.
    """

    ranked_leads = qualified_leads.copy()

    ranked_leads = ranked_leads.sort_values(
        by="qualification_score",
        ascending=False,
    ).reset_index(drop=True)

    ranked_leads["priority_rank"] = (
        ranked_leads.index + 1
    )

    return ranked_leads