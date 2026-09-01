import json
import os
import time
from typing import Any, cast

from google import genai

from lead_intelligence.llm.prompts import (
    SYSTEM_PROMPT,
    build_lead_prompt,
)

from lead_intelligence.config.settings import (
    GEMINI_API_KEY
)

class LLMClient:
    """Client for interacting with the Gemini API."""

    def __init__(
        self,
        model: str = "gemini-3.5-flash-lite",
        max_retries: int = 3,
    ):
        self.model = model
        self.max_retries = max_retries

        api_key = GEMINI_API_KEY

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set."
            )

        self.client = genai.Client(
            api_key=api_key
        )

    def generate_reasoning(
        self,
        leads: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Send a batch of leads to the LLM and return
        reasoning and outreach messages.

        One API call is made for the entire batch.
        """

        prompt = build_lead_prompt(leads)

        for attempt in range(
            1,
            self.max_retries + 1,
        ):

            try:

                response = (
                    self.client.models.generate_content(
                        model=self.model,
                        contents=[
                            SYSTEM_PROMPT,
                            prompt,
                        ],
                        config={
                            "response_mime_type": "application/json",
                        },
                    )
                )

                return self._parse_response(
                    cast(
                        str,
                        response.text,
                    )
                )

            except Exception as error:

                print(
                    f"LLM API attempt "
                    f"{attempt} failed: {error}"
                )

                # --------------------------------------------
                # Maximum retry reached
                # --------------------------------------------

                if attempt == self.max_retries:

                    raise RuntimeError(
                        "LLM API failed after "
                        "maximum retries."
                    ) from error

                # --------------------------------------------
                # Exponential backoff
                # --------------------------------------------

                wait_time = 2 ** attempt

                print(
                    f"Retrying in "
                    f"{wait_time} seconds..."
                )

                time.sleep(
                    wait_time
                )

        return []

    @staticmethod
    def _parse_response(
        response_text: str,
    ) -> list[dict[str, Any]]:
        """
        Parse and validate the LLM JSON response.

        Expected structure:

        {
            "results": [
                {
                    "lead_id": "L001",
                    "reasoning": "...",
                    "outreach_message": "..."
                }
            ]
        }
        """

        # ====================================================
        # 1. Parse JSON
        # ====================================================

        try:

            data = json.loads(
                response_text
            )

        except json.JSONDecodeError as error:

            raise ValueError(
                "LLM returned invalid JSON."
            ) from error

        # ====================================================
        # 2. Validate top-level structure
        # ====================================================

        if "results" not in data:

            raise ValueError(
                "LLM response does not contain "
                "'results'."
            )

        if not isinstance(
            data["results"],
            list,
        ):

            raise ValueError(
                "'results' must be a list."
            )

        # ====================================================
        # 3. Validate every lead result
        # ====================================================

        for result in data["results"]:

            # ----------------------------------------------
            # lead_id
            # ----------------------------------------------

            if "lead_id" not in result:

                raise ValueError(
                    "LLM result missing "
                    "'lead_id'."
                )

            if not result["lead_id"]:

                raise ValueError(
                    "LLM result contains "
                    "an empty 'lead_id'."
                )

            # ----------------------------------------------
            # reasoning
            # ----------------------------------------------

            if "reasoning" not in result:

                raise ValueError(
                    "LLM result missing "
                    "'reasoning'."
                )

            if not isinstance(
                result["reasoning"],
                str,
            ):

                raise ValueError(
                    "'reasoning' must be a string."
                )

            # ----------------------------------------------
            # outreach_message
            # ----------------------------------------------

            if "outreach_message" not in result:

                raise ValueError(
                    "LLM result missing "
                    "'outreach_message'."
                )

            # outreach_message can be:
            #   - a string for qualified leads
            #   - None for review/rejected leads

            if (
                result["outreach_message"] is not None
                and not isinstance(
                    result["outreach_message"],
                    str,
                )
            ):

                raise ValueError(
                    "'outreach_message' must be "
                    "a string or null."
                )

        # ====================================================
        # 4. Return validated results
        # ====================================================

        return data["results"]