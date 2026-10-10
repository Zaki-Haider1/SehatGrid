# Browser acceptance

The suite runs real Chromium against a production Next.js standalone server and the actual FastAPI/model/solver. Every case resets only the dedicated `sehat-grid-browser` Compose service. It never resets the normal Compose project or port 8000 demo. Run one suite at a time; its seed and fixed ports are intentionally shared by a single worker.

From the repository root, with Docker running:

```powershell
docker compose -p sehat-grid-browser -f docker-compose.browser.yml up -d --build
# Wait for http://127.0.0.1:18000/health to return {"status":"ok",...}.
cd frontend
npm ci
npx playwright install chromium
$env:API_PROXY_TARGET = 'http://127.0.0.1:18000'
npm run build
npm run test:browser
```

For Linux/macOS, replace the PowerShell environment assignment with `export API_PROXY_TARGET=http://127.0.0.1:18000`; on Linux install browser OS dependencies using `npx playwright install --with-deps chromium`. Dependency/model/browser downloads happen during preparation. The demo case blocks all non-loopback browser requests; the API has `HF_HUB_OFFLINE=1` at runtime. This does not claim full network-disabled container startup, which has a separate CI check.

The suite owns frontend port 13000 and API port 18000, and refuses to reuse an existing frontend server. Synthetic acceptance-only credentials are intentionally public fixtures; they are never production deployment credentials. Build normally again without `API_PROXY_TARGET` before running the normal port 8000 handoff.

The test browser uses software WebGL rendering through [Chromium's documented SwiftShader flags](https://github.com/chromium/chromium/blob/main/docs/gpu/swiftshader.md) so map rendering does not depend on a particular GPU/driver. These flags apply only to the isolated acceptance browser. WebGL-disabled coverage separately verifies the software rendering of the same 3D box geometry. The suite has no automatic retries; failed attempts and their corrections belong in the work log.

Coverage at 1440Ã—1000 and 390Ã—844:

- Login, service paraphrase matching, persisted review/intake, recommendations and ranking version, saved proposal without a hold, reload/reservation, receiving response, patient agreement, arrival and completion; proposal cancellation leaves quota and budget unchanged.
- Exact 8-subsidy/7-quota/5-mobile allocation costing PKR 25,000, approval, separate operators activating quota/mobile, reprocessing B-01, completed quota and funded subsidy referrals.
- Persisted projected/confirmed/completed counts, immutable hash and synthetic labels in real JSON/CSV downloads; no request IDs in aggregate exports.
- Planner ranking updates with observable operator ordering/version changes, concurrent stale-version recovery and operator role denial; bad login, empty review/referral screens, injected temporary API failure and a genuinely invalid session token. A request retargeted to another facility produces a real 403 and a corrective UI message.
- A concurrent onboarding quota change expires an unseen proposal; reservation returns the persisted expired attempt, and reception shows a recovery message with no false hold notice or quota consumption.
- Mobile-resource rejection with a recorded reason and revised persisted cost/coverage.
- Refresh persistence, page JavaScript errors, document width, screenshots and timed demo.
- Three authenticated interfaces: government city search/layers/details and previous-month outcomes; receptionist desk; onboarder catalog create/edit/delete, price and capacity persistence, government catalog visibility, and denied reception/catalog access.
- An eight-subsidy manual revision with reason/validation, persisted original solver output, approval and JSON/CSV exports; concurrent draft-edit recovery and rejection of unseen edits at approval.
- WebGL-disabled 3D geometry, status colors, orbit/zoom/reset and keyboard selection; restart with local model assets retains recorded changes.

`frontend/test-results/browser-results.json` and `frontend/playwright-report/` record pass/failure details. Per-case folders contain screenshots, exports, demo duration/browser/version evidence and failure traces. They are ignored by Git because traces can include session credentials. CI uploads them as a dedicated artifact. Do not publish traces from a real partner session.

To inspect a failure, run `npx playwright show-report` or `npx playwright show-trace <trace.zip>`. To run one viewport, use `npm run test:browser -- --project=phone`. After verification, from the repository root:

```powershell
docker compose -p sehat-grid-browser -f docker-compose.browser.yml down
```

The simulated phone uses Chromium; it does not establish Safari/WebKit or physical-device acceptance. No public hosting is claimed by this suite. Public deployment remains a required V2 gate and needs an identified hosting account/project with access.
