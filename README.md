# Langley Changes

Search Langley development applications and track when Township building permits appear and disappear from the public active list.

**[Open the live browser tool](https://coolcode.ca/langleychanges/)** · [CoolCode catalogue](https://coolcode.ca/)

No installation or account is needed to use the tool. This repository contains its independent source, tests and GitHub Pages publishing workflow.

<!-- coolcode:guide -->
Search a street to see which permit folders were listed there, then open a folder to compare its issue date with the first and last times CoolCode saw it.
<!-- /coolcode:guide -->

## What you can do

- Search addresses, application numbers and descriptions across Township and City records.
- Filter by community and published status group; open original plans and documents.
- Inspect Township application outlines; City records remain in the list without guessed locations.
- Save application IDs in your browser, share a record, or export filtered results as CSV.
- See differences observed between daily snapshots, including records no longer listed.
- Search Township permit folders by street, folder number, permit type or description. Inspect a shared folder link or export the filtered results as CSV.

The first development application snapshot contains **644 listed applications**: 615 Township and 29 City records. One development project can have several applications; these are not building or housing-unit counts.

## Development application sources and change history

- [Township development activity](https://www.tol.ca/en/building-development/development-activity.aspx), including its public ArcGIS application layer and source document links.
- [City development application portal](https://www.langleycity.ca/business-development/development/development-application-portal). This features selected applications; monthly reports linked there provide the full active list. The app does not claim complete City coverage.

Tracking began **2026-11-18**. The first snapshot is a baseline: older applications are not falsely marked new. Subsequent snapshots record changed fields, first appearances, disappearance and reappearance. Source milestones are shown separately from changes observed by this tool. A disappearance is not evidence of completion or cancellation. Original status text is preserved beside broad filter groups.

Stable source record IDs connect snapshots. A source layout/schema change, duplicate ID, incomplete ArcGIS pagination, or loss of over 20% of a municipality’s active records stops refresh for review. History is retained in `web/data/applications.json` and Git history. Applicant contacts are not copied; only public project information is included.

Contains information from the linked municipal sources, subject to their terms. OpenStreetMap contributors supply the basemap; Leaflet's licence is included in `web/vendor/LICENSE`.

## Township building permit history

The [Township active building permit list](https://apps.tol.ca/bpact.aspx) covers permits issued since January 1, 2011. The [Township’s description](https://www.tol.ca/en/building-development/building-permit-activity-information.aspx) says it updates daily and removes permits 30 days after approval of the final inspection.

The collector reads every page of the unfiltered list. Each folder number identifies one permit, even when the Township publishes separate rows for several civic addresses. A folder retains its listed addresses, project descriptions, type and official issue date. Counts of source rows and unique currently listed folders appear beside the retrieval time. Development application counts are displayed separately.

The first collection on November 19, 2026 (UTC) found 2,091 distinct folders across 3,237 rows on 162 pages. Of these, 393 folders covered multiple addresses. This collection establishes the baseline. A folder present at baseline may have been listed much earlier. “Last seen” is the latest successful check that contained the folder. “First check showing absence” is the earliest later check that omitted it. If a folder returns, its earlier observation period remains visible. The exact removal and final inspection approval dates are unknown. A useful additional Township feed would pair the permit folder number with the final inspection approval date.

The collector validates page numbers, page sizes, source headings, required fields and folder identity, then rechecks both ends of the list. A reduction of more than 20% in rows or unique listed folders stops publication for review. The last successful history remains available in `web/data/permits.json`. The archive starts with folders observable at baseline and cannot reconstruct older delistings.

## Development

```sh
python3 -m pip install -r scripts/requirements.txt
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

The build writes `dist/` and works at the project subpath `/langleychanges/`. Do not commit `dist/` or add a `CNAME`; the account’s main Pages site supplies the coolcode.ca domain. Node is used for tests, not a frontend dependency bundle.

`web/` contains the application; `scripts/` contains the offline builder and data refresh; `tests/` contains model/source/build checks and Chromium user-flow tests. Browser checks cover project paths, controls, sharing, exports or layer selection, error handling, and mobile overflow. GitHub Actions installs their test-only dependencies from `tests/browser-requirements.txt`.

## Publishing and maintenance

`.github/workflows/pages.yml` checks pull requests and main commits. Only a successful main build deploys. Repository Settings → Pages must use **GitHub Actions**. The browser-checks artifact contains desktop/mobile screenshots. A failed build leaves the previous deployment in place.

`.github/dependabot.yml` enables **GitHub Dependabot**, which proposes updates to workflow actions and configured dependencies as pull requests. A proposal does not update main until merged. Review the diff and checks for the current PR commit before merging. Netlify is not used by this project.

`tool.json` describes this tool in the CoolCode catalogue. Its reviewed record belongs in `jsdyer/jsdyer.github.io/data/tools.json`; run that repository’s `scripts/sync_readme.py` to keep the hub README and polished homepage aligned. Changing this repository alone does not change the homepage listing.

## Data refreshes

`.github/workflows/refresh.yml` runs daily (08:47 UTC) and can be started manually from Actions → Data snapshot · Refresh and publish. GitHub schedules can be delayed and may be paused for inactive public repositories; the visible retrieval date is the source of truth.

The workflow fetches and validates complete source responses, runs unit/browser checks, then commits the snapshot with GitHub’s Actions token and deploys the same tested build. Failed refreshes do not replace the last successful deployment. A normal non-force push protects concurrent edits; a rejected push stops deployment. This is the only workflow with `contents: write`; ordinary checks use read-only repository access.

Manual refresh:

```sh
python3 scripts/refresh.py
python3 scripts/permits.py
```

Review source/count changes before committing. Keep existing history when refreshing Langley Changes; do not delete a baseline just to reset differences.

## Privacy

Only explicitly saved application IDs are stored in `coolcode:langleychanges:watchlist`. Other tools on coolcode.ca share the same browser origin, so storage keys are namespaced. Searches run against a bundled public snapshot in your browser. OpenStreetMap receives tile requests for the viewed map area. CoolCode counts page opens by tool ID. The count excludes searches and watchlist entries. Sharing places the selected record or comparison view in the URL; it does not upload private files. External source links open the original provider.

<!-- schedule-reliability -->
## Schedule reliability

Public GitHub repositories can have scheduled workflows disabled after 60 days of inactivity. A separate weekly [schedule guard](.github/workflows/schedule-guard.yml) calls GitHub's enable-workflow API for an explicit list of refresh workflows and itself. It can restore workflows disabled for inactivity, preserves manually disabled workflows, and runs independently of collection failures.

This is an interim mitigation, not a scheduling guarantee: GitHub does not document active-workflow renewal as a permanent exemption, and scheduled runs can be delayed or dropped. A scheduler on our own Linux server is the planned independent trigger. The guard does not collect data, create dummy commits, or change source/check timestamps; successful collection and published data freshness still need monitoring.
<!-- /schedule-reliability -->

## Search metadata

The build emits a descriptive page title, canonical URL, social preview metadata and
static `WebApplication` JSON-LD for the free browser tool. The visible application
name stays unchanged. Edit the search title in `web/index.html`; application details
come from `tool.json`. No ratings or reviews are invented.

[Guide: check Langley permits and application dates](https://coolcode.ca/field-notes/checking-langley-permits/).
