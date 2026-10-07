# Setup and deployment

## Configuration

Set server-only application settings before starting the API:

| Setting | Purpose |
| --- | --- |
| STUDIO_STORAGE_ACCOUNT | Expected dedicated Azure storage account name; required |
| STUDIO_STORAGE_CONNECTION_STRING | Secret connection string for that account |
| STUDIO_GITHUB_REPOSITORY | Target owner/repository for manual publishing |
| STUDIO_PUBLIC_SITE_URL | HTTPS origin of the reader-facing blog |
| STUDIO_LEGACY_MEDIA_HOST | Optional exact host for historical /media/ images; empty by default |
| STUDIO_ALLOW_PUBLISH | Keep false until production verification |
| STUDIO_GITHUB_TOKEN | Fine-grained Contents read/write token for the target repository |

Copy local.settings.example.json to ignored local.settings.json for Azure Functions local tooling. The static preview server does not load these values or provide authentication. Restart the API after changing settings because account/host settings are read on import.

Create a private drafts container and a published container that allows individual-blob public reads. Originals remain private. Store credentials only in server settings. No browser-direct uploads or CORS wildcard is required.

## Hosting

1. Run `python tools/build_studio.py` to create site/ and package the validator into api/.
2. Deploy site/ plus api/ to Azure Static Web Apps with Python 3.11. The deployment workflow is `.github/workflows/deploy-studio.yml`. Configure its AZURE_STATIC_WEB_APPS_API_TOKEN GitHub secret for your own hosting app. Pushes to main deploy it; manual dispatch can deploy the development branch. Documentation-only main pushes skip deployment.
3. Use Microsoft's aad provider. Invite only approved authors with studio_editor on this hosting app. Roles from a different app must not be assumed to transfer.
4. Keep API endpoints behind the SWA authentication gateway. Function authLevel anonymous is intentional only behind that gateway; do not expose a separate Functions host that accepts caller-supplied x-ms-client-principal headers.
5. Verify sign-in, library/direct upload, duplicate filenames, edited copies, galleries, save/reopen and denied access for ordinary authenticated users.
6. For production only, change api/studio_deployment.json profile to production and set STUDIO_ALLOW_PUBLISH=true. Both gates are required. Supply the repository-limited token only after the target is reviewed.
7. Publish a reviewed test story manually and verify its blog page and thumbnail/full-size viewer. Start with subscriber notifications unchecked.

## Blog connection

The publisher targets main and atomically commits content/posts/<slug>/meta.json and body.html. The blog must understand that contract, use editor_format=ckeditor, display cover_thumbnail, preserve image layout styles, and support data-full photo links. Notification choice is stored as notify; the receiving blog controls actual email delivery. This is a specific static-blog adapter, not a universal CMS integration.

Deploying Studio independently keeps editor-only work out of the blog build. Draft saves and uploads do not trigger Actions. Publication triggers the existing blog deployment. No additional CI tests were added to that deploy path.

## Limitations

No draft deletion/history or existing-post import. JSON backup contains writing and private photo addresses, not image bytes. Interactive crop supports freeform, square, landscape and portrait selections. Large-batch synchronous publication timing is unmeasured. Source extraction has local mocked tests; the new hosting application requires its own authenticated end-to-end checks.

## Reusing Studio for another website

Start with local.settings.example.json. Its empty credentials and example destinations are safe to share. Your own local.settings.json is ignored by Git; Azure deployment uses private server app settings instead of shipping this file. Never replace the public example with live credentials. The hosting deployment token belongs in a GitHub Actions secret, not in either public file.

A site using the documented meta.json/body.html blog contract needs configuration changes only. WordPress, Drupal or another publishing format requires replacing the publishing adapter in api/studio_api.py. Configure Microsoft editor invitations separately for your hosting app. This repository does not include a universal destination selector.

## Current hosted preview

The separate Studio application is hosted at https://zealous-ground-065787e1e.3.azurestaticapps.net/admin/story-studio/. It uses the Free plan. Microsoft invitations are specific to this application. Publication is disabled while authenticated workflow verification is pending. Source downloads are available at https://github.com/clintdubois/story-studio/releases/tag/v0.1.5-preview. No custom domain has been configured.

JPEG-based multi-picture (MPO) files with .jpg names are accepted. Their primary image is prepared as ordinary JPEG; additional image frames stay only in the private original.
