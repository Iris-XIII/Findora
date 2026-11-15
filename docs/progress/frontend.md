# Frontend progress

**Status:** IN PROGRESS
**Last updated:** 2026-11-14

## Verified completed
- First-run onboarding requires a valid local profile before showing the app; choosing Other reveals a required custom clothing-interest field.
- Only a profile explicitly submitted through setup is treated as complete. Legacy or placeholder profiles do not skip onboarding; completed profiles persist on later visits.
- Profile changes persist locally. The Other collection filter uses the entered label and is omitted when Other is not selected.
- The search box is inside the Homepage welcome panel below the greeting, uses the requested clothing/brand/URL placeholder, and routes searches to Price Intelligence; it is hidden on other tabs.
- Search results do not open Product Intelligence automatically, including single-result searches; the detail view opens only after the user selects a catalog product button.
- Product Intelligence has an upper-right Add to Collection control that toggles saved state and stays synchronized with the catalog save button.
- My Collection filters saved demo products into all five standard clothing categories; each category was exercised in the browser.

## In progress
- Frontend remains in explicit synthetic Clothing demo mode by default; live API behavior has only been checked with contract-shaped mocks.
- Chrome extension files are split into a Manifest V3 unpacked-extension folder; loading and runtime behavior have not yet been verified in Chrome.

## Next steps
- Verify search and product detail against the integrated FastAPI backend when clothing records are available.
- Rehearse the full judge flow with the team’s integrated data.

## Blockers / dependencies
- No live backend validation was performed for this change; frontend behavior depends on an integrated API with supported clothing records.

## Changed files / tests and outcomes
- `frontend/index.html`: added the Other interest field, combined the Homepage-only search box and welcome into one panel, added My Collection category filters, and added the Product Intelligence collection control.
- Browser: verified profile gating, conditional/required Other input, saved-profile behavior, all standard collection filters, conditional Other filter, homepage-only search visibility and demo search routing; no page errors or duplicate IDs observed.
- Browser: verified single-result demo and mocked API searches keep Product Intelligence closed until the product button is selected.
- Browser: verified Add to Collection appears in the product detail header, adds/removes the product, and synchronizes the catalog save control and collection count.
- Browser: verified an old “Demo Shopper” profile opens onboarding, submitting a user profile opens Homepage, completed profiles return on reload, and a cleared profile starts at onboarding with the app and search hidden.
- Browser: verified the welcome panel contains the search box below the greeting, the removed subtitle is absent, the layout fits mobile without horizontal overflow, the search stays hidden on My Collection, and demo search still routes to results.
- `extension/manifest.json`, `extension/popup.html`, `extension/popup.css`, and `extension/popup.js`: replaced the concatenated `extension/extension.html` with a standard unpacked extension package; mock output is labeled synthetic.
- Extension validation: Python manifest/asset-reference/whitespace checks passed; `git diff --check` passed. `node --check extension/popup.js` could not run because Node.js is unavailable, and Chrome installation has not been tested in this environment.
- `git diff --check`: passed.

## Handoff notes
- No backend, Databricks, or shared contract files changed.
