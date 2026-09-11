# Westford 2026-2027 calendar review

Reviewed September 10, 2026, against page 5 of the town's
[2026-2027 Recycling Guide](https://westfordma.gov/DocumentCenter/View/16672/Recycling-Guide-2026-2027).
The PDF was downloaded, its text extracted, and the complete calendar page rendered
and inspected visually.

- Source SHA256: `25dd585ca4f594307f11246f0de065c10ee866cc2c42ed7407b9bb241f02a4c0`
- Coverage: July 1, 2026 through June 30, 2027.
- Printed anchor: July 1-3 BLUE; July 6-10 GREEN. Anchor Sunday: June 28, 2026.
- Circles designate holiday delays; triangles designate special events.
- July 4 is Saturday and is not circled. July 3 remains a normal pickup.

| Holiday | Date | Affected routes |
| --- | --- | --- |
| Labor Day | 2026-09-07 | Monday-Friday, each delayed one day |
| Thanksgiving | 2026-11-26 | Thursday-Friday, each delayed one day |
| Christmas | 2026-12-25 | Friday delayed to Saturday |
| New Year's Day | 2027-01-01 | Friday delayed to Saturday |
| Memorial Day | 2027-05-31 | Monday-Friday, each delayed one day |

The Thursday BLUE pickup for September 10 therefore belongs on September 11.
The 52 Thursday trash dates and their recycling colors were transcribed into
`tests/fixtures/westford_thursday_2026_2027.csv` from the rendered calendar.
`tests/test_westford_review.py` checks all those dates for both colors, holiday
cutoffs on other weekdays, Saturday pickups, and the final coverage boundary.
The parser text fixture includes an unrelated 2020 reference to verify that the
guide year comes from its title rather than arbitrary document text.

## Why the holiday shift was missed

The previous holiday file ended at May 25, 2026. The parser extracted only the
alternating-week anchor and returned an empty holiday policy. A daily rebuild
with that configuration therefore could not learn Labor Day from the PDF.

The downloader also needed the request-header/retry fix to handle municipal PDF
requests reliably. A failed updater preserves the previous database, so a working
API alone does not establish that its schedule data is current.

## Repair and operational limits

The reviewed holiday file now binds dates and coverage to the exact PDF bytes.
Changed PDFs and expired reviews fail the build without replacing the previous DB.
The service emits no pickups beyond reviewed coverage and reports an unhealthy
status after coverage expires. Calendar subscriptions therefore currently end
June 30, 2027 even when requesting 365 days; a later reviewed guide extends them.

This retains manual holiday review. It does not implement automatic OCR or infer
observed federal holidays. Follow `docs/PARSING.md` when the source changes.
Even a non-calendar edit to the PDF requires reviewing and updating its fingerprint.

## Validation

- All 52 Thursday pickup dates and both recycling colors matched the reviewed PDF.
- The route set remained unchanged: 543 records.
- All 38 tests passed locally and in a Linux container.
- API and ICS checks placed the affected Thursday BLUE pickup on September 11,
  with September 17 trash and September 24 recycling plus trash.
- A 365-day request emitted no pickups beyond the reviewed coverage period.

Deploy both the application and the reviewed town configuration, then verify the
calendar output and updater success. See [Deployment](DEPLOYMENT_VPS.md) for the
general procedure. Host-mounted town configuration overrides files in the image.

Calendar clients need to refresh their subscription to see moved events; a
previously imported static `.ics` file does not update automatically. Updater
failures require monitoring the job status and DB timestamp; `/healthz` detects
expired review coverage but does not currently alert on a failed daily refresh
within coverage.
