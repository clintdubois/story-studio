# Story Studio

A standalone CKEditor 5 writing application with shared private drafts, a large photo viewer, editable photo copies, Azure Blob thumbnails and full-size images, and manual publication to a static blog.

Public source repository: https://github.com/clintdubois/story-studio. This application is not yet deployed. Hosted editing will remain restricted to approved Microsoft accounts.

## Start here

- `docs/SETUP.md`: configuration, packaging and hosting.
- `docs/SOURCE.md`: licensing and corresponding source.
- `context.md`: status and remaining work.
- `local.settings.example.json`: empty credentials and synthetic destinations.

## Development

Use Python 3.11 or later. Install `api/requirements.txt` in a virtual environment. Run `python -m unittest discover -s tests -v` and `python tools/build_studio.py`. Serve the generated `site/` folder to inspect the page; saving and uploading require the authenticated Azure backend. Never use simulated authentication in a public deployment.

The maintained validator lives in `tools/story_studio_core.py`. Packaging copies it to `api/`.

## License

Story Studio code is licensed under GPL-2.0-or-later. See `LICENSE`, `NOTICE.md`, and the upstream CKEditor notice in `licenses/`. The authoring application includes its API and publishing code in the shared source. Stories and photos are data and are not included in this source package.
