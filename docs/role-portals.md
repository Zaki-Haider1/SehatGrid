# Two MVP interfaces

The MVP has exactly two authenticated application roles in a shared Next.js application and FastAPI backend.

| Role | Operational scope |
|---|---|
| Hospital operator | Assigned providers; profiles, reviewed primary-care service and zone declarations, dated quota, own outgoing requests, incoming partner responses, patient agreement, arrival/completion, dated offers and resource activation |
| Network planner / government representative | Participation approval, aggregate network intelligence, monthly budgets/subsidy rules, draft computation, approval, subsidy authorization, plan export and network audit |

No patient account or portal is part of scope v1. Operators record voluntary patient agreement independently from the receiving partner's decision. Software roles do not establish clinical qualifications. The earlier three-portal proposal has been removed.

The seeded hospital accounts are `operator-p01` through `operator-p08`; `planner` is the planner account. Passwords come from `DEMO_PASSWORD` on initial seed/reset. UI navigation reflects the signed-in account; the backend independently verifies every permission. Mobile activation grants the responsible operator scope for the newly created synthetic mobile-site provider.
