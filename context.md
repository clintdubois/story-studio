# Story Studio context

Updated 2026-10-06. Public repository setup authorized by the owner. Repository: https://github.com/clintdubois/story-studio. Standalone authoring frontend, Azure API, photo preparation, publisher, tests, build instructions and license notices are included. Existing blog history, posts, photos, secrets, invitations and contact files are excluded.

GPL-2.0-or-later covers the application including backend and publisher. CKEditor community 48.5.2 is pinned. Upstream source archive and review ZIP remain in ignored local/; docs/SOURCE.md records its URL and verified hash. Public release packaging must include the exact corresponding source and notices.

15 isolated tests, standalone build and frontend syntax check passed during extraction. Storage account, target blog repository, public origin and optional historical image host are configurable without live defaults. Preview configuration disables publication. Separate Free Azure Static Web App story-studio now exists in the existing resource group. Host: https://zealous-ground-065787e1e.3.azurestaticapps.net. Deployment runs 37568882689 and 37568997755 succeeded. Current hosted source commit f07f667. Public home/source pages return 200; editor and API redirect anonymous requests to Microsoft. Source download link is verified. Server settings connect to the existing dedicated Studio storage. Publishing remains false with no publishing token. No custom DNS changes were made.

Default branch main; development branch codex/standalone-studio. The two approved authors have seven-day Microsoft studio_editor invitations, stored only in ignored local/. No email was sent. Acceptance and authenticated hosted tests remain pending. Workflow is on main and development branch; docs-only pushes do not deploy. Next: accept invitations and verify hosted draft upload/save/reopen/access restrictions, then verify the static-blog publishing contract before production enablement. Earlier hosted preview authentication remains unresolved.

Public preview source release: https://github.com/clintdubois/story-studio/releases/tag/v0.1.0-preview. Source ZIP includes the exact upstream CKEditor source. Account invitation acceptance and authenticated uploads remain unverified; do not call those checks complete.

## Batch upload feedback fix

User reports selecting six or eight JPGs with no photos or visible error. Confirmed code renders the library only after the full batch finishes and errors appear only as temporary toasts. This does not establish whether that batch failed or was still uploading. Library now renders each success immediately, shows numbered progress and a final count, retains filename-specific errors, continues after failures, and reports preparation/save errors. Autosave is paused during the library batch, which is serialized with direct-editor uploads. Non-JSON HTTP failures now distinguish oversized requests, sign-in failures and service errors.

A Node check exercises the actual library handler with eight mock files, a failed third file, incremental rendering, retained errors and failed initial preparation. It passes, along with JS syntax checking. Hosted acceptance is reported by the user; the available in-app tab still shows the earlier access page, so actual authenticated batch success is not confirmed. Deployment of this fix is pending.
