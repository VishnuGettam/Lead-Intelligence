import os

from dotenv import load_dotenv


# ============================================================
# Load .env file
# ============================================================

load_dotenv()


# ============================================================
# Helper: Get required environment variable
# ============================================================

def get_required_env(name: str) -> str:
    """
    Return a required environment variable.

    Raises:
        ValueError: If the variable is missing or empty.
    """

    value = os.getenv(name)

    if not value or not value.strip():
        raise ValueError(
            f"Required environment variable "
            f"'{name}' is not set."
        )

    return value.strip()


# ============================================================
# Application Configuration
# ============================================================

LEADS_PATH = get_required_env(
    "LEADS_PATH"
)

QUARANTINE_OUTPUT_PATH = get_required_env(
    "QUARANTINE_OUTPUT_PATH"
)

TRANSFORMED_OUTPUT_PATH = get_required_env(
    "TRANSFORMED_OUTPUT_PATH"
)

PRE_LLM_OUTPUT_PATH = get_required_env(
    "PRE_LLM_OUTPUT_PATH"
)

FINAL_OUTPUT_PATH = get_required_env(
    "FINAL_OUTPUT_PATH"
)

AGGREGATED_REPORT_PATH = get_required_env(
    "AGGREGATED_REPORT_PATH"
)

GEMINI_API_KEY = get_required_env(
    "GEMINI_API_KEY"
)