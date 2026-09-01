import os
from dotenv import load_dotenv

load_dotenv()


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value or not value.strip():
        raise ValueError(
            f"Required environment variable '{name}' is not set."
        )

    return value.strip()


LEADS_PATH = get_required_env("LEADS_PATH")

QUARANTINE_OUTPUT_PATH = get_required_env("QUARANTINE_OUTPUT_PATH")

TRANSFORMED_OUTPUT_PATH = get_required_env("TRANSFORMED_OUTPUT_PATH")

PRE_LLM_OUTPUT_PATH = get_required_env("PRE_LLM_OUTPUT_PATH")

FINAL_OUTPUT_PATH = get_required_env("FINAL_OUTPUT_PATH")

AGGREGATED_REPORT_PATH = get_required_env("AGGREGATED_REPORT_PATH") 

GEMINI_API_KEY = get_required_env("GEMINI_API_KEY")