# Story Studio context

Updated 2026-10-06. Public repository setup authorized by the owner. Repository: https://github.com/clintdubois/story-studio. Standalone authoring frontend, Azure API, photo preparation, publisher, tests, build instructions and license notices are included. Existing blog history, posts, photos, secrets, invitations and contact files are excluded.

GPL-2.0-or-later covers the application including backend and publisher. CKEditor community 48.5.2 is pinned. Upstream source archive and review ZIP remain in ignored local/; docs/SOURCE.md records its URL and verified hash. Public release packaging must include the exact corresponding source and notices.

15 isolated tests, standalone build and frontend syntax check passed during extraction. Storage account, target blog repository, public origin and optional historical image host are configurable without live defaults. Preview configuration disables publication. Separate Free Azure Static Web App story-studio now exists in the existing resource group. Host: https://zealous-ground-065787e1e.3.azurestaticapps.net. Deployment runs 37568882689 and 37568997755 succeeded. Initial hosted source commit f07f667; see batch fix status below. Public home/source pages return 200; editor and API redirect anonymous requests to Microsoft. Source download link is verified. Server settings connect to the existing dedicated Studio storage. Publishing remains false with no publishing token. No custom DNS changes were made.

Default branch main; development branch codex/standalone-studio. The two approved authors have seven-day Microsoft studio_editor invitations, stored only in ignored local/. No email was sent. Acceptance and authenticated hosted tests remain pending. Workflow is on main and development branch; docs-only pushes do not deploy. Next: accept invitations and verify hosted draft upload/save/reopen/access restrictions, then verify the static-blog publishing contract before production enablement. Earlier hosted preview authentication remains unresolved.

Public preview source release: https://github.com/clintdubois/story-studio/releases/tag/v0.1.0-preview. Source ZIP includes the exact upstream CKEditor source. Account invitation acceptance and authenticated uploads remain unverified; do not call those checks complete.

## Latest checkpoint: photo insertion works (2026-10-06, later)

**Resolved:** the draft 403 cleared after the fresh invitation (the session had lost `studio_editor`), and the editor now opens, uploads, inserts a library photo into the story, saves and reopens with the photo still present. The user confirmed this on the deployed preview (commit c246cc2, run 37573426370).

**What the insertion failures were (found by making the server error name the rejected address):**
1. The editor held a studio photo under the site's full web address (`https://<host>/api/story-media/...`); the validator only accepted the short `/api/story-media/<draft>/<photo>` form. Fixed in `tools/story_studio_core.py` (`localize_story_media`): the exact photo path is rewritten to the short form; any other address is still rejected.
2. Then "Every story photo must belong to this draft": a library tile dragged into the text carries the small thumbnail's address, which the draft check does not list (it lists each photo's full-size `src`). Fixed: a thumbnail address is stored as the photo itself (publishing makes the small and large versions). Cause inferred from the code and both messages; the fix resolved it.
3. A stuck draft blocked every save, and photo uploads save first, so uploads failed with the same message until the picture was normalized.
Rejection messages now name the offending address (never story text) and cut very long `data:` addresses short (`describe_address`).

**HEIC/HEIF (iPhone photos), added Oct 6:** the browser sends the original file and the server converts it, the same approach as the WestCoastViewNavion site: `pillow-heif` is added to `api/requirements.txt` (BSD-3, bundles libheif under LGPL-3.0; recorded in NOTICE.md) and the reader is registered lazily at the first photo (`enable_heif()`), so a missing or broken install cannot take the API down (HEIC would then be refused as unreadable). The primary image is used, orientation is applied, metadata is stripped, and the web copy and thumbnail are ordinary JPEGs; the original HEIC stays in private storage. The upload button and CKEditor's own image upload accept `.heic`/`.heif` (Windows often reports no type for them). Tests: HEIC conversion and bad-bytes refusal in `tests/test_story_studio.py` (skipped where pillow-heif is not installed) and `tests/test_photo_types.cjs`. Not yet verified on the deployed preview with a real iPhone photo.

**Deployment note:** `.github/workflows/deploy-studio.yml` runs only by hand (`workflow_dispatch`); a push, including to the development branch, does not deploy. Deploy with `gh workflow run deploy-studio.yml --repo clintdubois/story-studio --ref codex/standalone-studio`, then check with a single `gh run list` call. Do not use `gh run watch`.

**Local testing:** `PYTHONPATH=<path with azure.functions> python -m unittest discover -s tests` (22 tests) and the three `tests/*.cjs` files with Node. The user's machine has no Node on PATH; the Codex runtime copy is at `~/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe`. git needed a `safe.directory` exception for this folder because another Windows account owns it (added Oct 6 with the user's approval).

**Still open:** HEIC/HEIF verification on the deployed preview with a real iPhone photo (code and tests added Oct 6); publishing disabled with no publishing token; verify the static-blog publishing contract before enabling production; gallery insert, cover choice, photo edit-copy and the preview have not been re-tested on this deployment; `chezduboistravels/context.md` still describes the older private-repo path and needs refreshing.

## Batch upload feedback fix

User reports selecting six or eight JPGs with no photos or visible error. Confirmed code renders the library only after the full batch finishes and errors appear only as temporary toasts. This does not establish whether that batch failed or was still uploading. Library now renders each success immediately, shows numbered progress and a final count, retains filename-specific errors, continues after failures, and reports preparation/save errors. Autosave is paused during the library batch, which is serialized with direct-editor uploads. Non-JSON HTTP failures now distinguish oversized requests, sign-in failures and service errors.

A Node check exercises the actual library handler with eight mock files, a failed third file, incremental rendering, retained errors and failed initial preparation. It passes, along with JS syntax checking. Hosted acceptance is reported by the user; the available in-app tab still shows the earlier access page, so actual authenticated batch success is not confirmed. Fix commit bee399c was deployed by run 37569630243; public source page verifies v0.1.1-preview is served. Workflow completion remains to be recorded. Public source archive is released under v0.1.1-preview.

User then reported the old generic Please sign in again message. This may mean a non-JSON service response rather than authentication failure; cause remains unconfirmed. Azure confirms one assigned studio_editor user. User asked to refresh after preserving unsaved writing and retry one JPG for the new persistent diagnostic message. JPG batch success and save/reopen remain unverified.

## Upload draft readiness guard

User's next single-JPG attempt returned Invalid draft or photo identifier. Read-only storage inspection confirms one draft with a canonical UUID matching its folder and zero photos. This rules out a malformed stored draft but not a missing frontend ID or failed initialization. The current browser automation tab still shows old access denial, so it cannot inspect the working editor session. Asked user for top-of-page status.

Upload input now starts disabled and enables only after the draft and CKEditor are ready. applyDraft rejects missing/malformed IDs, and webPhoto rejects an invalid upload address before any request. Node checks exercise missing/undefined/malformed IDs as well as the existing batch cases. Syntax and checks pass. Underlying hosted initialization failure, if any, remains unconfirmed.

Readiness deployment 37569988344 succeeded (b54aae7); public source page verifies v0.1.2-preview. User confirms the draft itself also says sign in again, so draft initialization failure explains missing upload IDs. Exact session/access failure remains unknown. Azure confirms the approved Microsoft identity has aad plus studio_editor/anonymous/authenticated roles; the agent's fresh in-app tab still gets editor access denial and was closed. Requested userDetails/userRoles or null clientPrincipal from /.auth/me in the user's actual working browser. Do not collect tokens/cookies or bypass the browser tool's auth endpoint restrictions. Next step depends on that session evidence; no repeat blind sign-in requests.

## Successful direct API checks; editor request diagnosis

User provided session evidence: correct approved Microsoft account, aad and studio_editor/anonymous/authenticated. Direct navigation in Microsoft Edge to both the draft list and the specific draft returns JSON. Therefore basic authentication, roles and draft read/storage work. Earlier claim that a fresh sign-in is required is unsupported. Failure is in the editor's background request path/session or response handling. Edge automation is unavailable; Codex's built-in browser has a different session and is not evidence of the user's Edge access.

Frontend requests now explicitly include cookies and request JSON, preserve save headers, and report HTTP method/path/status plus sanitized redirect path without query strings. Init reports whether list loading or opening the saved draft failed and displays that beside the disabled photo control. Request tests cover cookies, headers, service statuses and redirect query exclusion; batch/readiness tests remain passing. This is diagnostic improvement, not a confirmed resolution of authenticated uploads.

Request diagnostic source commit 50ab1a6 deployed via run 37570676199; source page verifies v0.1.3-preview is live. User asked to hard-refresh Edge and report the new stage/request/HTTP message if draft initialization still fails. Actual editor upload success remains pending.

## Confirmed JPEG variant rejection and fix

User supplied an original failing .jpg locally. Pillow identifies it as MPO, a JPEG-based two-image file, 4032 by 3024 pixels and under 2 MB. Old validator rejects it because its format whitelist lacks MPO. This failure is reproduced directly against the original bytes; no user image or metadata is committed or included in public source packages.

Validator now accepts MPO alongside JPEG/PNG/WebP, verifies it and decodes only frame zero for orientation-corrected, EXIF-stripped ordinary JPEG web/thumbnail output. Originals remain private. Size/pixel limits remain unchanged. Unsupported recognized formats report their actual format. Synthetic two-frame MPO and rejected GIF cases bring backend tests to 17 passing. Original user file also passes preparation, JPEG output, EXIF removal and 1800/720 size checks. This confirms the format bug; hosted upload success still needs user verification after deployment.

## Current checkpoint — 2026-10-06

MPO fix commit 42ea23f was pushed on codex/standalone-studio and deployed successfully by Actions run 37571089548. Public source release: https://github.com/clintdubois/story-studio/releases/tag/v0.1.4-preview. User confirms a photo uploaded and is visible. Supported inputs are JPEG (including MPO), PNG and WebP. HEIC/HEIF conversion to JPEG is requested but not implemented.

User reports brief messages when inserting a photo into the story, rather than adding it to the library. Local, uncommitted changes in admin/story-studio/index.html skip a queued autosave if an upload begins before that save executes and retain save/recovery messages. New tests/test_save_upload_queue.cjs passes, along with request and batch tests. These changes have not been deployed; their relationship to the user's brief messages is not confirmed.

Earlier blocker (resolved, see the latest checkpoint above): opening the saved draft from the editor failed with HTTP 403. Screenshot identifies the failed background GET to the saved draft and shows initialization stopped before CKEditor loads; photo controls remain paused. User logged out and back in and confirms the same 403 persists. Earlier direct navigation in the same Microsoft Edge browser returned draft JSON, and supplied session evidence included the correct Microsoft provider and studio_editor role. Do not recommend repeated sign-ins or relax access rules without evidence. The current failure's origin (Azure route authorization versus backend principal check) remains unknown.

Pending diagnostic question: after this fresh sign-in, does direct navigation to the same saved draft API URL still return JSON or now an access-denied page? No answer received yet. Edge automation is unavailable; the agent's in-app browser has a separate session. Do not collect cookies, tokens, raw authentication headers or private story text.

Next: resolve the draft GET 403, then finish and deploy the tested queued-save/message changes and verify upload, insertion, save and reopen in the user's authenticated browser. Add HEIC/HEIF preparation afterward. Publishing remains disabled, with no publishing token configured. Development remains on codex/standalone-studio; this checkpoint does not deploy or merge application changes.

## Authentication diagnosis update — 2026-10-06

After logging out and back in, the user confirms HTTP 403 persists. Direct navigation to the saved draft now also returns the Editor access required page. Azure users list still assigns studio_editor to the approved Clint Microsoft account, but the user's current /.auth/me response contains only anonymous and authenticated roles. The missing session role explains the current access denial; why the session lost the assigned role remains unconfirmed.

Created a fresh seven-day aad invitation for the already-approved Clint account and studio_editor role. Invitation expires 2026-10-13 at 9:32 PM Pacific (2026-10-14 04:32 UTC). Signed invitation is stored only in ignored local/Clint-Studio-Invitation.json and was shared privately in chat; do not commit the URL or signature. No email was sent, no access rules were weakened and no application deployment was triggered.

Next user action: accept the fresh invitation in the same Edge browser with Clint's approved account, then reopen Studio. Verify /.auth/me includes studio_editor, the saved draft opens, and the role persists after a later logout/login. Invitation acceptance and restored access are not yet confirmed. After access is restored, finish the locally tested queued-save/message fix and verify insertion/save/reopen. HEIC/HEIF conversion remains requested and unimplemented; publishing remains disabled.

## Photo selection controls — 2026-10-07

User confirms a six-photo upload worked, but clearing the automatically selected photos was unclear. Selection previously used a small checkmark button; clicking an image opens the viewer. Buttons now explicitly say Deselect for selected photos, and Clear selection clears the batch without deleting photos or changing story content. Delegated clicks use the closest selection/view control. Frontend syntax, individual toggle, clear-selection and existing batch checks pass locally. Hosted verification remains pending deployment and user retest.

## Photo pane follows editing — 2026-10-07

User requested access to the photo library while editing lower in a long story. The desktop photo pane now uses sticky positioning with a 16px top gap, aligns to the top of its grid column and has a viewport-limited height with its own vertical scrolling. At widths of 950px or less, where the page uses a single column, it returns to normal page flow. This avoids covering the story on narrow screens. Standalone build passes; hosted scrolling and insertion require user verification. No save/upload/publish behavior changed.

## Selection button visibility fix — 2026-10-07

User screenshot reveals long unbroken photo filenames push the Select/Deselect buttons outside the clipped photo tiles. Filename flex items now shrink with min-width zero and show an ellipsis; selection buttons cannot shrink. Hovering over the filename shows its full value. The viewer still displays the full name. This fixes the visible layout cause rather than changing selection state. Frontend syntax passes. Hosted verification pending user retest.

## Cleaner photo tiles — 2026-10-07

User still could not see Select and requested filenames only on hover. Removed filename text from the tile row entirely. The photo's title attribute shows its filename on hover, and the row contains only a full-width Select/Deselect button. Full filename remains available in the viewer. Actual tile rendering and frontend syntax checks pass. User verification after deployment remains pending.

## Available and Used photo tabs — 2026-10-07

Added compact Available/Used tabs with counts. Inserting a photo through the button, gallery or editor marks it Used; cover photos count as Used too. Used history remains after a photo is deleted from the story. Move back returns an unused photo to Available; photos still referenced by the story or cover must be removed there first. Selection clears when a photo becomes used or tabs change. Existing drafts infer usage from their story and cover.

Tiles now have 80px thumbnails and compact Select/Remove controls; filenames stay on hover and in the viewer. Remove hides an unused photo from the draft library, retaining private original and prepared blobs. It does not delete story content. Backend persists validated boolean used/removed state and rejects hiding referenced photos. Tests cover persistence, reference protection, usage history, move-back and removal; 25 Python tests and all five frontend checks pass. Standalone build passes. Publishing remains disabled. Development branch is codex/standalone-studio; hosted interaction verification remains pending user retest after deployment.

## Interactive crop editor — 2026-10-07

Replaced the centered 4:3 toggle with a movable crop rectangle and freeform, square, landscape 4:3 and portrait 3:4 presets. Drag inside to move; bottom-right handle resizes. Arrow keys move the box and Shift+arrows resize. Rotation resets the box for the chosen shape; Reset restores the full photo. Brightness remains available. Saved JPEG copies are rendered from a separate clean canvas so crop outlines and shading are never exported. Originals remain unchanged in private storage. Implementation uses built-in browser canvas only, with no new third-party dependency; application code remains covered by the repository GPL license.

Crop geometry/bounds/preset/export-path and frontend syntax checks pass, alongside all existing frontend checks; standalone build passes. Actual pointer interaction and cropped-copy save/reopen on the hosted editor require user verification after deployment. Development branch remains codex/standalone-studio; publishing remains disabled.

## Photo reuse and red crop control — 2026-10-07

Move back now returns a photo to Available without requiring deletion from the story or cover. Persisted reuseAvailable state keeps it available through rendering and reopening; a new story occurrence moves it back into Used. Occurrence tracking supports both insertion buttons and dragging. Remove still protects photos referenced by the story or cover. Backend validates and preserves the new boolean alongside used/removed.

Crop border is red and the bottom-right resize handle is a bold red plus; clean exported JPEGs do not include these controls. All 25 Python tests and six frontend checks pass, including moving back while referenced and marking Used after another insertion. Hosted user verification remains pending after deployment.

## Crop control layout — 2026-10-07

Moved Crop shape into a labeled field with its label above a full-width styled dropdown. Crop shape, Rotate and Reset align along their bottom edges, share a 44px control height and wrap on narrow screens. Crop behavior is unchanged. Crop checks and frontend syntax pass; visual acceptance pending user review after deployment.
