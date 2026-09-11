# Westford, MA

This folder contains Westford-specific configuration and overrides.

- `town.yaml`: primary configuration, including source URLs and parser plugin paths.
- `street_aliases.yaml`: alias mappings for street normalization.
- `route_overrides.yaml`: add/delete/patch route entries when parsing is brittle.
- `holiday_rules.yaml`: visually reviewed holiday behavior, PDF SHA256, and coverage dates.

Update cadence: review annually or when the town publishes a new guide.
Daily DB refreshes extract PDF text, not holiday circles. A changed PDF requires
manual review before its fingerprint is accepted. Calendar output ends at the
reviewed coverage date (currently June 30, 2027).

See [the 2026-2027 review](../../docs/WESTFORD_2026_2027_REVIEW.md) and
[the update procedure](../../docs/PARSING.md#when-westford-publishes-a-new-guide).
