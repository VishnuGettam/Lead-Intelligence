So our development phases should be
Phase 1 — Pipeline foundation

Build:

CSV
 ↓
Ingestion
 ↓
Validation
 ↓
Cleaning
 ↓
Processed CSV
Phase 2 — Qualification
Processed leads
 ↓
Rubric
 ↓
Score
 ↓
Qualified / Review / Rejected
Phase 3 — LLM
Leads
 ↓
Batching
 ↓
LLM API
 ↓
Reasoning
 ↓
Structured JSON
Phase 4 — Reporting
Individual results
+
Aggregations
+
Priority ranking
+
Rejection reasons
+
Outreach examples
Phase 5 — Production hardening
Error handling
Retries
Rate limits
Logging
Configuration
Tests

That gives you a project that starts as a clean Python data pipeline architecture and naturally evolves into the required Lead Intelligence System, rather than us writing a bunch of lead-specific code from day one.