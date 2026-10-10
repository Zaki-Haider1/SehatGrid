# Planned government, hospital and patient portals

The final design has three user-facing interfaces, sharing one FastAPI backend and PostgreSQL database. They can live in a single Next.js application with separate routes and navigation. Backend authorization must enforce the same boundaries as the interface.

| Portal | Primary actions | Access boundary |
|---|---|---|
| Government representative (`/government`, planned) | View citywide capacity and unmet demand, compare catchments, review funding proposals, approve allocations and monitor outcomes | Aggregate network information and authorized funding; patient-identifying information requires a separate justified permission |
| Hospital representative (`/hospital`, planned) | Manage the hospital's verified profile, publish dated service capacity, receive referrals, confirm or decline them and record completion | Only assigned facilities and their authorized referrals |
| Patient (`/patient`, planned) | Browse the hospital map and directory, request a service, see referral/appointment status, receive instructions and cancel a request | Public directory plus the signed-in patient's own requests |

A patient submits a care request. An authorized hospital/operator reviews the service and offers a referral or appointment. The receiving hospital confirms it and records completion. Unmet requests contribute to anonymized government planning; approved resources become available through hospital operations. Clinical triage and emergency decisions require qualified staff. Directory pins never imply that a hospital has joined the platform.

The current implementation has **operator and planner view modes in a shared demo dashboard**. These are not authenticated portals. Operator mode demonstrates much of the hospital workflow, while planner mode demonstrates the government funding workflow. The patient portal, hospital-specific access, role-based login, patient ownership checks, invitation/verification flow, notifications and audit trail remain to be implemented before real onboarding.

The development sequence is authentication and backend permission checks, government/hospital route separation, facility onboarding, then patient intake and status tracking with appropriate privacy controls. The demo continues to use generated references and no personal patient data during that work.
