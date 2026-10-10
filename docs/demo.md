# Five-minute demo

1. Open Overview on the date of the seeded requests. Explain the four counters and select a provider on the schematic.
2. Open Providers and update Central Care Hospital's General consultation daily total. The overview counters update from the database.
3. Add a General consultation request in Central. Optionally type `blood test` and show the suggestions, then deliberately choose the desired canonical service. Explain that the operator reviews the suggestion.
4. Select a recommended provider. Show reserved → confirmed → completed. A completed slot stays consumed for that day. Create another request and cancel its reservation to demonstrate released capacity.
5. Open Demand insights. The six seeded requests expose exhausted local dialysis, maternal-care, and general-consultation capacity in South, East, and West.
6. Switch to Planner. With the default PKR 50,000 budget, generate a plan and review quantities and costs. Approve it. Additional capacity activates, budget is committed, and pending requests become reserved referrals. Return to Referrals for partner confirmation.
7. Refresh and export the day's JSON snapshot to demonstrate persisted state.

The Overview map uses sourced Islamabad hospital coordinates. Select a pin to view its address, phone, website and evidence; expand “Hospital information & sources” for services, published hours and coordinate provenance. Providers supports hospital/sector/address search and public/private filtering. Extra directory hospitals show “No demo capacity reported”; this is unknown availability, not a claim that they are full.

The five cardinal planning catchments remain demonstration groups and are not official Islamabad administrative zones. Hospital sectors and physical coordinates are recorded separately. Capacity values are simulated and do not indicate a hospital's actual beds, appointments, prices or participation.

For repeat rehearsals, enable reset only on a disposable local demo and confirm it through the dashboard. Reset removes every workflow change and recreates the Islamabad directory and synthetic workflow seed.

Judge explanation: PostgreSQL gives us transactional capacity and funding updates. The concurrent test suite shows only one reservation succeeds for the last slot and that competing plans cannot spend the same remaining funds.

Current scope: text matching is RapidFuzz, optimization is OR-Tools, and the map is a schematic. Clinical matching, real patient records, travel-distance scoring, notifications, and real procurement are outside this MVP.
