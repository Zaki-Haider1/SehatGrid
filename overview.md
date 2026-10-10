# Implementation decisions — scope v1

The supplied [MVP specification](docs/mvp-scope-v1.md) controls product scope. Earlier optional patient-portal and broad service proposals are superseded.

## One operational loop

Next.js renders role-specific screens from persisted FastAPI outputs. Operators review semantic suggestions and publish dated primary-care quota. A sending operator reserves capacity; the receiver accepts; an operator records patient agreement; a planner authorizes any unfunded subsidy. Confirmation requires all three conditions. Receiving operators record arrival then completion. Every action has an actor and UTC audit event.

Intelligence aggregates unique unresolved requests, never referral-attempt counts. An immutable snapshot contains eligibility records, excluded reasons, dated capacity/offer versions and a hash. The monthly optimizer assigns request units to compatible base/quota/mobile resources, maximizes coverage, minimizes cost, then uses stable ordered decisions. One worker and a fixed seed make runs reproducible. A draft is revalidated transactionally at approval. A resource operator must activate purchased/mobile resources. Subsidy-pool commitments transfer into referral holds/commitments and settlements without additional charges.

## Database choice and concurrency

PostgreSQL is the deployment database; SQLite is the single-machine demo option. The justification for judges is: **database transactions reserve capacity and monthly funds together, preventing concurrent requests from overbooking or overspending.**

This small 5–10-provider implementation persists the canonical entity collections in one versioned JSON aggregate (`pilot_state`) through SQLAlchemy. PostgreSQL `SELECT FOR UPDATE` serializes aggregate writes; SQLite `BEGIN IMMEDIATE` provides the equivalent writer exclusion. This includes reads that lazily expire holds. Database locks, not a Python mutex, protect multiple workers. The aggregate contains users, facilities/services, capacity records, requests, attempts/reservations, offers, snapshots, plans/actions, ledger entries, reviews, audit history and idempotency receipts. Invariants are checked before commit.

This is an explicit pilot-scale tradeoff: transaction correctness and a single coherent snapshot over write throughput. It is **not** a high-throughput normalized relational deployment. Growth would require separating these entities into indexed tables while preserving the same cross-resource locking rules. The JSON objects retain all contract fields; the proposed README table names are not falsely represented as individual SQL tables.

Alembic adds the new pilot state without dropping the earlier demo tables. Legacy tables are historical data only; their unauthenticated endpoints and daily slot-purchase code have been removed. A reset touches only the new synthetic state.

## Machine learning

The actual model is `sentence-transformers/all-MiniLM-L6-v2`, pinned at revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. ONNX Runtime executes its pretrained transformer; the tokenizer, attention-mask mean pooling and L2 normalization reproduce the model's sentence-embedding pipeline. This avoids shipping a separate PyTorch runtime. The preload manifest records artifact SHA-256 checksums and model card/license metadata.

Suggestions combine embedding cosine similarity (80%) and fuzzy string similarity (20%), with exact reviewed aliases preferred. Facility candidates include locality/type evidence. Scores are not probabilities. A threshold of 0.69 was selected using six development cases; 14 separate evaluation cases contain paraphrases, duplicates, ambiguous names and unsupported text. Near-tied facility candidates are marked ambiguous. Every final service assignment or identity link requires a stored human decision. Identity links preserve original IDs and do not move quotas or requests.

## Geography and frontend

Eight public hospital coordinate records provide attributed context for clearly labelled synthetic partners. Demo catchments are not legal boundaries or road-access estimates. MapLibre's bundled coordinate layer works offline; an optional OSM raster layer is an enhancement. A basic SVG pin fallback remains if WebGL fails. Provider pins use backend current/limited/exhausted/unknown status; planner zone labels show aggregate unresolved units. Mobile sites have separate synthetic pins.

Two authenticated roles share one Next.js app. There is no client-side role switch granting authority. JWTs are signed with an external secret, passwords use salted PBKDF2, tokens expire, and every operation enforces role/facility scope on the server. Demo accounts intentionally share a configured presentation password; this is not a real-provider onboarding scheme.

## Deployment

The combined root container serves Next.js and proxies API requests internally to FastAPI. PostgreSQL stays external. A backend-only container is also included for split hosting. Model downloads happen during preparation/build, never during startup or the demonstration. Runtime secrets are excluded from Git and build context. Local and container startup validate configuration and fail visibly when model assets are missing.
