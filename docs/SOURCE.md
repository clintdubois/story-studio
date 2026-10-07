# Licensing and source package

This package treats the entire Story Studio application, including its API, photo preparation and GitHub publisher, as GPL-2.0-or-later. Complete Studio source, tests, build script, configuration examples, license text and notices are included. Credentials, personal content and generated drafts are not source code and are excluded.

CKEditor is the unmodified community version 48.5.2. The page currently loads its pinned npm browser distribution from jsDelivr. The review archive includes the matching upstream Git source archive, with original build files and notices. See local/SOURCE-MANIFEST.json for retrieval URLs and SHA-256. These local archives are ignored by Git; public release packaging must retain the corresponding source alongside the release and link it from the editor.

Official license documentation: https://ckeditor.com/docs/ckeditor5/latest/getting-started/licensing/license-and-legal.html
Upstream source: https://github.com/ckeditor/ckeditor5/tree/v48.5.2
Pinned browser distribution: https://cdn.jsdelivr.net/npm/ckeditor5@48.5.2/dist/browser/ckeditor5.umd.js

## Before public release

Review third-party notices and all archive contents. Provide an accessible corresponding-source download for the exact release and preserve its build instructions. Keep the upstream source and dependency notices available rather than relying solely on a mutable upstream link. Add the final source URL to the editor. Confirm the separate public blog does not load CKEditor/application code; it consumes published story output. A separate repository or HTTP connection alone does not establish every GPL boundary.

The local package is a practical compliance preparation, not a legal determination that the whole deployment complies. Source publication and production hosting remain review steps.

Verified upstream archive SHA-256: `131b0a502f56580800bf1185449d64e45cea2ebc338c541a916860f9614901d6`. Run `python tools/package_source.py` to assemble the allowlisted review archive after retrieving that exact source archive.
