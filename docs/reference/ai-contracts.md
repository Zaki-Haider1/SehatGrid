# AI contracts

AI runs in the backend. Configure `AI_API_KEY` with a Groq key and `AI_MODEL` (default `qwen/qwen3.8-27b`). If no key is configured, standard matching, referral and allocation workflows remain usable.

## Planner scenario advice

`POST /api/v1/ai/planning-advice` is planner-only. It takes an optional month and a goal (`question`, 1–1,500 characters). The backend captures an immutable aggregate snapshot, then asks Qwen to propose a title, optional `budget_limit_pkr`, known `excluded_offer_ids`, `allow_subsidies`, rationale and clarification when the goal is unsupported or ambiguous.

The objective remains maximum eligible coverage followed by minimum cost. OR-Tools checks the proposed scenario against actual eligibility, capacity, dates and funds. The response includes the snapshot and input hash, proposal, checked coverage/cost/unresolved count, and comparison with the full remaining budget. A clarification does not produce a solved plan. AI advice is preview-only: staff must create, review, revise and approve the plan. Approval revalidates inputs; AI cannot reserve or activate resources.

## Hospital workflow guidance

`POST /api/v1/ai/workflow-help` is available to assigned operators and onboarders. Reception guidance uses scoped request status, reasons, referral flags and up to three ranked eligible destinations. Onboarding guidance uses only the assigned facility, reviewed eligibility, current quota and catalog. The response has `advice.summary`, `next_steps`, `cautions`, and `preview_only: true`; it never changes records.

Advisor payloads exclude phone numbers and free clinical descriptions. Reception advice can include synthetic request references and operational facts. Semantic matching uses the locally loaded MiniLM model; a staff member must review each match. See the [API contract](api-contracts.md) and [UML sequence](../architecture/diagrams.md).
