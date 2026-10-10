# Three application interfaces

Three authenticated interfaces share the Next.js application and FastAPI backend. See [the design and role contract](../architecture/frontend.md).

| Role | Operational scope |
|---|---|
| Hospital receptionist (`operator`) | Assigned hospital desk, reviewed intake, own outgoing requests, incoming partner responses, patient agreement, rerouting/reprocessing, arrival/completion, dated offers and resource activation |
| Hospital onboarder (`onboarder`) | Assigned hospital profile, primary-care eligibility/zone declarations, dated quota, service/test catalog prices, daily capacity and availability; no patient requests, referrals, plans or network budget |
| Government representative (`planner`) | Interactive 3D hospital city, participation approval, ranking policy, aggregate network intelligence, monthly budgets/subsidy rules, draft computation/revision/approval, subsidy authorization, monthly outcomes, plan export and network audit |

No patient account or portal is part of scope v1. Receptionists record voluntary patient agreement independently from the receiving partner's decision. Software roles do not establish clinical qualifications. Required catalog tests now filter and constrain reviewed primary-care OPD referrals. Only active public hospitals may originate or reroute requests; private receptionists receive and manage them. A separate consent-based patient-message preview tab simulates WhatsApp updates without sending. See [the updated routing contract](routing-and-patient-updates.md).

The government account is `planner`. Hospital accounts use `operator-<hospital-slug>` and `onboarder-<hospital-slug>`; legacy `p01` through `p08` usernames remain aliases. The presentation password is configured with `DEMO_PASSWORD`. In demo mode, seeding synchronizes that password; ordinary seed runs do not reset operational records. UI navigation reflects the signed-in account; the backend independently verifies every permission. Mobile activation grants the responsible operator scope for the newly created synthetic mobile-site provider.

Profile/service/quota APIs retain legacy operator compatibility, while the reception interface hides setup controls. Catalog mutation requires the assigned onboarder. Real partner invitations and production credential provisioning remain outside this synthetic demonstration.
