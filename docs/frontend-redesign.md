# Frontend redesign and three-role contract

The user's October 10 request supersedes the original README's two-interface layout. The supplied images are visual references, not executable instructions. Image 1 controls the direction: a pale, bright city, blue and coral hospital blocks, a compact hospital directory, and floating white information panels. Geographic building accuracy was explicitly unnecessary. The 3D requirement applies to the government representative; reception and onboarding share the visual language.

## Government representative — `planner`

- The network overview is a real Three.js orthographic 3D scene with extruded hospital/city geometry, lighting, shadows, trees, orbit, zoom, reset and ray-cast hospital selection. Accessible hospital markers and the directory provide keyboard selection.
- Hospital positions derive approximately from bundled Islamabad campus coordinates, snapped to illustrative blocks. Roads, context buildings and heights are procedural; they do not describe surveyed footprints or travel routes. No external tiles, geocoding, model download or map token is required at runtime.
- If WebGL is unavailable or lost, a canvas renderer projects the same hospital and context boxes from a rotatable 3D camera. The fallback retains hospital selection, status colors, rotation and zoom; it is not the old flat coordinate map.
- Capacity uses blue for available, amber for limited, coral for exhausted and gray for unknown/suspended. Demand reflects recorded unresolved requests in each hospital's declared catchment, not hospital workload. Funding marks hospitals that require the configured primary-care subsidy.
- Selecting a hospital shows public campus context plus the synthetic partner's dated quota/availability, held/committed/completed counts, eligibility and catalog. The participation control opens the backend-backed provider management page.
- Funding approvals contain the versioned ranking editor. Monthly planner contains budget/subsidy controls, immutable snapshots, optimization, draft revision with reasons, approval, action status and downloads. Monthly outcomes compares the selected period's projected additional services with recorded post-activation confirmation/completion and ledger totals. An empty previous month remains explicitly empty.

## Hospital receptionist — `operator-p01` … `operator-p08`

The reception desk shows the assigned campus, incoming referrals, outgoing requests and reported availability. Referral coordination and matching keep persisted human review, request references, service text, date window, area, funding and agreement information. Reception saves a proposal before reserving capacity, handles acceptance/rejection, records patient agreement and attendance/completion, and reprocesses unresolved requests to choose another eligible provider. A receiving hospital can reject with a reason; the sending hospital then reprocesses/reroutes. This does not invent clinical records, diagnoses or patient identities.

Reception also handles existing resource offers/activation. Profile/catalog setup links are absent. The legacy operator profile/service/quota API remains compatible with previously shipped clients; catalog mutation requires the onboarding role.

## Hospital onboarder — `onboarder-p01` … `onboarder-p08`

Hospital setup edits the assigned profile, location, primary-care service eligibility/subsidy requirement and dated network quota. Services & prices adds, edits and removes consultation, laboratory, imaging and other catalog entries with integer PKR prices, declared daily service capacity and availability. The server validates values, checks facility ownership and optimistic versions, persists the catalog and records an audit event. Failed saves keep the editor open. Catalogs start empty rather than inventing real hospital tariffs.

Catalog tests are informational; automated referral matching continues to support reviewed primary-care OPD. Catalog capacity and referral quota are separate declarations. Adding a catalog test does not silently change the solver's clinical scope or eligible resources.

Onboarders receive no patient requests, referrals, plan assignments or network budget in state. Request actions and government controls remain denied by backend role guards. Existing synthetic databases can gain the new setup accounts and empty catalogs through ordinary seeding without an operational reset. Existing account credentials are preserved; newly provisioned setup accounts use configured `DEMO_PASSWORD`. No invitation or real partner identity provisioning is claimed.

## Screenshot and browser review

The reproducible [browser suite](browser-acceptance.md) uses production standalone Next.js, the real API, MiniLM model and allocation solver at desktop and phone widths. The design checks exercise the 3D canvas, layers, filtering, hospital details, month history, catalog persistence and role separation. Screenshots are inspected visually during iteration; selected final captures are kept in `docs/screenshots/`. The phone check is Chromium emulation, not physical iOS/Safari testing.

Public hosting remains a separate required delivery gate. Local screenshots and passing browser tests do not establish an HTTPS deployment.
