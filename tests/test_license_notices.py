# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Clint and Liz DuBois. See LICENSE and NOTICE.md.
"""GPL housekeeping: source link in the editor, integrity-pinned CKEditor, and a license header on every source file."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / 'admin' / 'story-studio' / 'index.html').read_text(encoding='utf-8')


class LicenseNotices(unittest.TestCase):
    def test_editor_page_links_to_source_and_license(self):
        self.assertRegex(HTML, r'<footer class="source-note"><a href="/source\.html">Source code and license</a>')
        self.assertTrue((ROOT / 'source.html').exists())
        self.assertIn('SPDX-License-Identifier: GPL-2.0-or-later', HTML)

    def test_ckeditor_files_are_pinned_with_integrity_hashes(self):
        for tag in re.findall(r'<(?:script|link)[^>]*cdn\.jsdelivr\.net/npm/ckeditor5@[^>]*>', HTML):
            self.assertRegex(tag, r'ckeditor5@48\.5\.2/', 'CKEditor must stay on an exact version')
            self.assertRegex(tag, r'integrity="sha384-[A-Za-z0-9+/]{64}"')
            self.assertIn('crossorigin="anonymous"', tag)
        self.assertEqual(len(re.findall(r'integrity="sha384-', HTML)), 2)

    def test_every_source_file_has_a_license_header(self):
        missing = []
        for pattern in ('api/**/*.py', 'tools/*.py', 'tests/*.py', 'tests/*.cjs'):
            for f in ROOT.glob(pattern):
                if '__pycache__' in f.parts:
                    continue
                if 'SPDX-License-Identifier: GPL-2.0-or-later' not in f.read_text(encoding='utf-8')[:400]:
                    missing.append(str(f.relative_to(ROOT)))
        self.assertEqual(missing, [])


if __name__ == '__main__':
    unittest.main()
