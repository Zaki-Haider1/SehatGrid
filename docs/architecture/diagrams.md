# SEHAT GRID architecture diagrams

The diagrams use Mermaid and render in GitHub Markdown.

## Components

```mermaid
flowchart LR
  Staff[Planner, reception, onboarder] --> UI[Next.js role workspaces]
  UI -->|same-origin API proxy| API[FastAPI]
  API --> Auth[JWT and role scope]
  API --> Store[(SQLAlchemy pilot state)]
  API --> Match[MiniLM and fuzzy matching]
  API --> Solver[OR-Tools allocation]
  API -->|optional scoped advice| Groq[Groq Qwen]
  Solver --> Store
  Groq -->|structured proposal| API
```

## Core domain relationships

```mermaid
classDiagram
  class Facility { id; ownership; participation; zone; version }
  class Service { id; name; category }
  class Capacity { facility_id; date; quota; version }
  class Request { id; source_facility_id; zone; status }
  class Referral { request_id; facility_id; status; patient_agreed }
  class Snapshot { month; input_hash; immutable_evidence }
  class Plan { snapshot_id; status; decision_source; version }
  class Assignment { request_id; resource_id; cost }
  Facility "1" --> "many" Capacity
  Facility "many" --> "many" Service
  Facility "1" --> "many" Request : originates
  Request "1" --> "many" Referral : attempts
  Snapshot "1" --> "many" Plan : plans from
  Plan "1" --> "many" Assignment
```

## Referral lifecycle

```mermaid
stateDiagram-v2
  [*] --> PROPOSED
  PROPOSED --> CANCELLED: sender cancels
  PROPOSED --> EXPIRED: inputs stale
  PROPOSED --> AWAITING_CONFIRMATIONS: sender reserves
  AWAITING_CONFIRMATIONS --> CONFIRMED: partner + patient + required funding
  AWAITING_CONFIRMATIONS --> REJECTED: partner rejects
  AWAITING_CONFIRMATIONS --> CANCELLED: cancellation
  CONFIRMED --> ARRIVED
  ARRIVED --> COMPLETED
```

## AI allocation sequence

```mermaid
sequenceDiagram
  actor Planner
  participant API as FastAPI
  participant Model as Groq Qwen
  participant Solver as OR-Tools
  Planner->>API: goal and month
  API->>API: capture immutable aggregate snapshot
  API->>Model: scoped evidence and supported objective
  Model-->>API: structured scenario constraints
  API->>API: validate offer IDs and clamp budget
  API->>Solver: solve scenario and full-budget comparison
  Solver-->>API: checked coverage, cost and unresolved demand
  API-->>Planner: preview, trace and snapshot ID
  Planner->>API: create draft, review, revise, approve
  API->>Solver: revalidate current operational inputs
```

See [AI contracts](../reference/ai-contracts.md), [API contracts](../reference/api-contracts.md), and [operational assumptions](../reference/assumptions.md).
