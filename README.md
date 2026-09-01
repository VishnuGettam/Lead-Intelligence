# Lead Intelligence System

## 1. Overview

The **Lead Intelligence System** is a Python-based data pipeline that automatically processes inbound B2B SaaS sales leads, applies a deterministic qualification rubric, ranks leads by priority, uses an LLM for concise evidence-based reasoning and outreach generation, and produces actionable CSV/JSON reports.

The system addresses a common sales bottleneck: a SaaS company receives approximately 1,200 inbound leads per month but manually qualifies and reaches out to only about 60. Each manual decision takes roughly 8–12 minutes, creating a high risk of missed opportunities and wasted sales effort.

### Goal

Turn raw lead data into:

- A qualification score
- A qualification decision: `qualified`, `review`, or `rejected`
- A priority rank
- LLM-generated reasoning
- Outreach messages for qualified leads only
- Aggregated business statistics
- Common rejection reasons
- Sample outreach messages

---

## 2. High-Level Architecture

```text
                    leads_training.csv
                            |
                            v
                    +---------------+
                    |   Ingestion   |
                    +---------------+
                            |
                            v
                    +---------------+
                    |  Validation   |
                    +---------------+
                       /           \
                      /             \
                     v               v
              +-------------+   +---------------+
              |    VALID    |   |   INVALID     |
              +-------------+   +---------------+
                     |               |
                     |               v
                     |        +-------------+
                     |        | Quarantine  |
                     |        | invalid CSV |
                     |        +-------------+
                     |
                     v
              +---------------+
              |Transformation |
              |  + lead_id    |
              +---------------+
                            |
                            v
                    +---------------+
                    | Qualification |
                    |    Rubric     |
                    +---------------+
                            |
                            v
                    +---------------+
                    |Priority Rank  |
                    +---------------+
                            |
                            v
                  pre_llm_leads.csv
                            |
                            v
                +----------------------+
                |   LLM Batch Layer    |
                |  One call per batch  |
                +----------------------+
                            |
                 +----------+----------+
                 |                     |
                 v                     v
             Reasoning            Outreach
                 |              qualified only
                 +----------+----------+
                            |
                            v
                     final_leads.csv
                            |
                            v
                 aggregated_report.json
```

The pipeline deliberately separates **deterministic qualification** from **LLM enrichment**. The LLM does not override the qualification score or decision.

---

## 3. Project Structure

```text
lead-intelligence/
|
+-- data/
|   +-- raw/
|   |   +-- leads_training.csv
|   |
|   +-- processed/
|   |   +-- leads_training_tf.csv
|   |   +-- pre_llm_leads.csv
|   |
|   +-- output/
|       +-- final_leads.csv
|       +-- aggregated_report.json
|
+-- src/
|   +-- lead_intelligence/
|       |
|       +-- ingestion/
|       |   +-- csv_reader.py
|       |
|       +-- validation/
|       |   +-- validator.py
|       |
|       +-- transformation/
|       |   +-- cleaner.py
|       |
|       +-- qualification/
|       |   +-- rubric.py
|       |
|       +-- llm/
|       |   +-- client.py
|       |   +-- prompts.py
|       |
|       +-- reporting/
|           +-- report.py
|       |
|       +-- pipeline.py
|
+-- tests/
|
+-- .env
+-- requirements.txt
+-- README.md
```

---

## 4. Input Data

The system expects a CSV containing lead information such as:

| Column | Description |
|---|---|
| `name` | Lead/contact name |
| `company` | Company name |
| `company_size` | Number of employees |
| `industry` | Company's industry |
| `source` | Lead acquisition source |
| `last_interaction_date` | Most recent interaction date |

Example:

```csv
name,company,company_size,industry,source,last_interaction_date
Alice Chen,CloudScale AI,1200,SaaS,linkedin,15-01-2024
Bob Smith,SmallTech,50,Retail,website,18-01-2024
```

The assignment requires **at least 30 diverse test leads**, including:

- Multiple industries
- Multiple company sizes
- Multiple lead sources
- Obvious high-potential leads
- Obvious low-potential leads
- Ambiguous/review cases

---

## 5. Pipeline Stages

### 5.1 Ingestion

`csv_reader.py` reads the raw CSV into a Pandas DataFrame.

Responsibilities:

- Load the input file
- Return a DataFrame
- Keep ingestion separate from transformation and business logic

---

### 5.2 Validation

`validator.py` performs two levels of validation and determines whether each
record is suitable to continue through the main lead-intelligence pipeline.

#### Schema validation

Checks that required columns exist.

Expected fields include:

```text
name
company
company_size
industry
source
last_interaction_date
```

#### Record validation

Checks individual records for invalid or missing values.

Examples:

- Missing name
- Missing company
- Invalid company size
- Invalid industry
- Invalid source
- Invalid interaction date

Each record receives a validation result containing:

- `row_number`
- `is_valid`
- `status` — `valid` or `invalid`
- `errors` — one or more validation errors associated with the record

A record with no validation errors is marked `valid`. A record with one or more
validation errors is marked `invalid`.

#### Quarantine Layer

Invalid records are **not sent to transformation, qualification, priority
ranking, or the LLM**. They are separated from the valid records and written
to:

```text
data/quarantine/invalid_leads.csv
```

The quarantine dataset preserves the invalid lead information and adds the
validation errors identified for each row.

Example:

```text
name       company       company_size   industry   status    errors
---------------------------------------------------------------------------
John Doe   ABC Corp      NaN            SaaS       invalid   Missing company_size
Jane Doe   XYZ Ltd       500            NaN        invalid   Missing industry
```

Multiple validation errors for the same record are retained together.

This creates a clear distinction between **data quality status** and
**business qualification decision**:

```text
Validation Status       Qualification Decision
-----------------       ----------------------
valid                   qualified
valid                   review
valid                   rejected
invalid                 not evaluated
```

`review` is therefore a business qualification outcome and is not used as a
substitute for invalid data.

The valid subset alone continues through the main pipeline:

```text
Validation
    |
    +--> valid records   --> Transformation --> Qualification --> LLM
    |
    +--> invalid records --> Quarantine
```

This prevents incomplete or invalid input data from affecting the qualification
rubric while retaining the records for audit, correction, and possible
reprocessing.

### 5.3 Transformation

`cleaner.py` standardizes the raw data.

Current transformations include:

```text
name                  → strip whitespace + title case
company               → strip whitespace + title case
company_size          → numeric conversion
industry              → strip whitespace + title case
source                → strip whitespace + lowercase
last_interaction_date → YYYY-MM-DD
```

The transformation layer also creates a unique identifier:

```text
L001
L002
L003
...
```

This `lead_id` is used throughout the remaining pipeline.

Using `lead_id` is preferable to using `company` as the join key because multiple contacts can belong to the same company.

---

## 6. Qualification Rubric

The qualification rubric is the **deterministic business decision layer**.

It uses the available lead attributes to calculate a qualification score and assign a decision.

The LLM does **not** calculate or modify this score.

The general model is:

```text
Raw Lead
   |
   v
Qualification Factors
   |
   v
Score
   |
   v
Decision
   |
   v
Priority Rank
```

### Decision categories

#### Qualified

The lead has sufficient evidence of being a strong sales opportunity and should receive sales attention.

#### Review

The lead contains some positive signals but does not provide enough evidence for an automatic qualified/rejected decision.

#### Rejected

The lead does not meet the qualification criteria and should not receive standard sales outreach.

The exact scoring thresholds and factor weights are implemented in:

```text
src/lead_intelligence/qualification/rubric.py
```

---

## 7. Priority Ranking

After qualification, leads are ranked according to their qualification results.

The priority rank allows the sales team to focus first on the strongest opportunities.

Example:

```text
priority_rank = 1  → highest priority
priority_rank = 2
priority_rank = 3
...
```

The rank is generated by the deterministic qualification/ranking layer, not by the LLM.

---

## 8. Pre-LLM Checkpoint

Before any LLM processing, the pipeline writes:

```text
data/processed/pre_llm_leads.csv
```

This is an important checkpoint.

It contains the deterministic results before LLM enrichment, including fields such as:

```text
lead_id
name
company
company_size
industry
source
last_interaction_date
qualification_score
decision
priority_rank
score_breakdown
```

This makes the pipeline easier to:

- Debug
- Audit
- Re-run
- Compare before/after LLM processing
- Recover from LLM failures

---

## 9. LLM Enrichment

The LLM is used for **reasoning and outreach generation**, not for the core qualification decision.

The current implementation uses the Google Gemini API.

### LLM responsibilities

For every lead:

- Explain the existing qualification result
- Use only supplied information
- Acknowledge missing information
- Preserve the existing score and decision

For qualified leads only:

- Generate a concise B2B SaaS outreach message

For rejected/review leads:

```json
"outreach_message": null
```

This prevents the system from generating sales outreach for leads that should not currently be pursued.

---

## 10. Batch Processing

The system does not call the LLM once per lead.

Instead, leads are grouped into batches.

Current configuration:

```python
BATCH_SIZE = 10
```

For example, 30 leads become:

```text
Batch 1 → 10 leads → 1 API call
Batch 2 → 10 leads → 1 API call
Batch 3 → 10 leads → 1 API call
```

Therefore:

```text
30 leads → 3 API calls
```

instead of:

```text
30 leads → 30 API calls
```

This reduces API overhead and is explicitly required by the assignment.

---

## 11. LLM Prompt Contract

The LLM is instructed to return JSON in the following structure:

```json
{
    "results": [
        {
            "lead_id": "L001",
            "reasoning": "Concise evidence-based explanation.",
            "outreach_message": "Professional sales message."
        }
    ]
}
```

For a rejected or review lead:

```json
{
    "lead_id": "L002",
    "reasoning": "The lead does not currently meet the qualification criteria.",
    "outreach_message": null
}
```

The client validates:

- `results` exists
- `results` is a list
- Every result has `lead_id`
- Every result has `reasoning`
- Every result has `outreach_message`
- `outreach_message` is either a string or `null`
- The returned lead IDs correspond to the input batch

---

## 12. Error Handling

The LLM client includes retry handling.

Current configuration:

```python
max_retries = 3
```

The retry mechanism uses exponential backoff:

```text
Attempt 1 fails
    ↓
wait 2 seconds

Attempt 2 fails
    ↓
wait 4 seconds

Attempt 3 fails
    ↓
raise error
```

The batch pipeline also handles a failed batch without silently losing its records.

A failed lead receives fallback reasoning such as:

```text
LLM reasoning unavailable because the API request failed.
```

and:

```text
outreach_message = null
```

---

## 13. Final Output

The main final output is:

```text
data/output/final_leads.csv
```

Expected columns include:

```text
lead_id
name
company
company_size
industry
source
last_interaction_date
qualification_score
decision
priority_rank
score_breakdown
reasoning
outreach_message
```

Example:

```csv
lead_id,name,company,qualification_score,decision,priority_rank,reasoning,outreach_message
L001,Alice Chen,CloudScale Ai,92,qualified,1,"Strong fit based on available signals.","Hi Alice,..."
L002,Bob Smith,Smalltech,35,rejected,18,"The lead does not meet the qualification criteria.",null
```

---

## 14. Aggregated Reporting

The reporting layer produces:

```text
data/output/aggregated_report.json
```

The report includes:

### Total processed

Number of leads processed by the pipeline.

### Qualified percentage

```text
qualified leads / total processed × 100
```

### Common rejection reasons

The system identifies recurring rejection factors from the deterministic qualification data.

This is preferable to deriving business statistics from free-form LLM prose because the result remains reproducible.

### Sample outreach messages

Up to 5 outreach messages are selected from qualified leads, prioritizing the highest-ranked leads.

Example structure:

```json
{
    "statistics": {
        "total_processed": 30,
        "qualified_count": 12,
        "rejected_count": 10,
        "review_count": 8,
        "qualified_percentage": 40.0
    },
    "common_rejection_reasons": [
        {
            "reason": "company_size",
            "count": 6
        }
    ],
    "sample_outreach_messages": [
        {
            "lead_id": "L001",
            "company": "CloudScale AI",
            "message": "Hi Alice..."
        }
    ]
}
```

---

## 15. Environment Setup

The project uses **uv** for Python environment and dependency management.

### Prerequisites

- Python 3.10+
- `uv`
- Internet connectivity for Gemini API calls
- A Gemini API key

### Create the virtual environment

From the project root:

```bash
uv venv
```

Activate the environment.

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### Install dependencies

If the project uses `requirements.txt`:

```bash
uv pip install -r requirements.txt
```

If the project is configured with `pyproject.toml`:

```bash
uv sync
```

### Run the pipeline with uv

The pipeline can be executed directly through uv:

```bash
uv run python -m lead_intelligence.pipeline
```

Using `uv run` ensures the command executes with the project's managed
environment and dependencies.

## 16. Gemini API Configuration

Set the environment variable:

```text
GEMINI_API_KEY
```

For local development, it can be loaded through a `.env` file if the project configuration supports it.

Example:

```text
GEMINI_API_KEY=your_api_key_here
```

Do **not** commit API keys to Git.

Recommended `.gitignore` entries:

```text
.env
.venv/
__pycache__/
*.pyc
```

---

## 17. Running the Pipeline

The main orchestration entry point is:

```text
src/lead_intelligence/pipeline.py
```

Run it from the project root:

```bash
python -m lead_intelligence.pipeline
```

If the package is configured differently, run the project's configured entry point accordingly.

The pipeline executes:

```text
1. Ingestion
2. Validation
3. Separate valid and invalid records
4. Quarantine invalid records
5. Transformation of valid records
6. Qualification
7. Priority ranking
8. Pre-LLM checkpoint
9. Batched LLM processing
10. LLM result merge
11. Final CSV generation
12. Aggregated reporting
```

---

## 18. Debugging

The pipeline can also be run through an IDE debugger.

Set a breakpoint in:

```text
pipeline.py
```

Useful breakpoint locations include:

```python
leads = read_leads(LEADS_PATH)
```

```python
transformed_leads = clean_leads(leads)
```

```python
qualified_leads = qualify_leads(
    transformed_leads,
    EVALUATION_DATE,
)
```

```python
results = llm_client.generate_reasoning(batch)
```

```python
final_leads = add_llm_results(
    ranked_leads,
    llm_results,
)
```

This makes it possible to inspect the DataFrame at each pipeline stage.

---

## 19. Testing Strategy

The project should include tests covering at least:

### Ingestion

- Valid CSV loads successfully
- Missing file raises an appropriate error

### Validation

- Missing required column is detected
- Invalid company size is detected
- Invalid date is detected
- Valid records pass validation
- Missing `name` is detected
- Missing `company_size` is detected
- Missing `industry` is detected
- Missing `source` is detected
- Missing `last_interaction_date` is detected
- Invalid records receive `status = invalid`
- Valid records receive `status = valid`
- Validation errors are captured against the correct source row
- Multiple validation errors for the same row are retained
- Invalid records are separated from valid records
- Invalid records are written to `data/quarantine/invalid_leads.csv`
- Quarantine records contain the original lead data plus the `errors` field
- Invalid records do not proceed to transformation, qualification, ranking, or LLM processing
- Valid records continue to the main pipeline

### Transformation

- Names are normalized
- Companies are normalized
- Sources are normalized
- Dates are converted correctly
- `lead_id` is generated
- IDs are unique

### Qualification

- Obvious high-quality lead is qualified
- Obvious low-quality lead is rejected
- Ambiguous lead goes to review
- Score is within the expected range

### Ranking

- Highest-priority leads receive the appropriate ranks
- Ranking is deterministic

### LLM parsing

- Valid JSON is accepted
- Invalid JSON raises an error
- Missing `results` raises an error
- Missing `lead_id` raises an error
- Missing `reasoning` raises an error
- Missing `outreach_message` raises an error
- Returned IDs match the input batch

### Reporting

- Total processed is correct
- Qualified percentage is correct
- Rejection reasons are aggregated
- Maximum 5 outreach examples are returned
- Rejected/review leads do not receive outreach messages

---

## 20. Known Limitations and Edge Cases

### 1. Lead ID generation

The current `lead_id` is generated from the row order:

```text
L001
L002
L003
```

If the source CSV is reordered, IDs can change. For a production system, a persistent source-system lead identifier should be preferred.

### 2. Limited input attributes

The system currently works with a relatively small set of lead attributes:

```text
name
company
company_size
industry
source
last_interaction_date
```

A production sales intelligence platform could use additional signals such as:

- Job title
- Website activity
- Product usage
- Email engagement
- Firmographic enrichment
- Intent data
- CRM history
- Revenue
- Technology stack

### 3. LLM dependency

LLM-generated reasoning and outreach depend on API availability, rate limits, response quality, and model behavior.

The deterministic qualification result remains the source of truth.

### 4. LLM output validation

JSON schema validation can be strengthened further using a typed schema such as Pydantic.

### 5. Duplicate companies

Multiple leads can belong to the same company. This is why the system uses `lead_id` rather than `company` as the merge key.

### 6. Outreach personalization

Outreach messages are limited to information available in the input dataset. The LLM must not invent facts about a company or contact.

### 7. Validation versus filtering

Invalid records are separated into the quarantine layer before qualification.
They are not silently discarded: `data/quarantine/invalid_leads.csv` retains
the source record together with its validation errors so the data can be
corrected and potentially reprocessed.

---

## 21. Design Principles

The project follows several important engineering principles:

### Deterministic decisions before generative enrichment

Qualification and ranking are handled by Python logic.

```text
Python → Score → Decision → Rank
```

The LLM enriches the result:

```text
LLM → Reasoning → Outreach
```

This makes the core business decision reproducible.

### Checkpointing

The pipeline persists:

```text
raw
  ↓
validation
  ├── invalid → quarantine
  ↓
transformed valid data
  ↓
pre-LLM
  ↓
final
```

This improves observability and debugging.

### Batch processing

LLM calls are made per batch instead of per lead.

### Stable identifiers

`lead_id` is used as the unique record key for LLM result merging.

### Fail-safe behavior

LLM failures should not corrupt deterministic qualification results.

---

## 22. Assignment Requirement Mapping

| Assignment Requirement | Implementation |
|---|---|
| Python source code | Python pipeline |
| LLM API | Gemini API |
| Batch processing | `BATCH_SIZE` and `create_batches()` |
| API error handling | Retry + exponential backoff |
| 30+ diverse test leads | `data/raw/leads_training.csv` |
| Qualification score | `qualification/rubric.py` |
| Decision | `qualification/rubric.py` |
| Reasoning | Gemini LLM |
| Priority rank | `qualification/rubric.py` |
| Validation and quarantine | `validator.py` + `data/quarantine/invalid_leads.csv` |
| Pre-LLM checkpoint | `pre_llm_leads.csv` |
| Total processed | Reporting layer |
| Qualified percentage | Reporting layer |
| Common rejection reasons | Reporting layer |
| 3–5 outreach messages | LLM + reporting layer |
| Final output | `final_leads.csv` |
| Aggregated report | `aggregated_report.json` |

---

## 23. Expected End State

After a successful run, the system should provide the following primary
datasets/reports:

```text
data/quarantine/invalid_leads.csv
```

Contains invalid records that failed data-quality validation, together with
their validation errors.

```text
data/output/final_leads.csv
```

A lead-level actionable dataset containing:

```text
lead_id
qualification_score
decision
priority_rank
reasoning
outreach_message
```

and:

```text
data/output/aggregated_report.json
```

A management-level summary containing:

```text
total processed
qualified percentage
common rejection reasons
sample outreach messages
```

The resulting workflow converts a large inbound lead volume into a prioritized sales queue that can be acted on immediately, while preserving deterministic qualification logic and using the LLM only where generative intelligence adds value.
