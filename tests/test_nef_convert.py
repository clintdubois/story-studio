# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Clint and Liz DuBois. See LICENSE and NOTICE.md.
"""NEF -> JPEG conversion (the browser code in admin/story-studio/index.html).

Builds small NEF-shaped TIFF files (little- and big-endian; preview in a SubIFD, or in the Nikon maker note),
runs the page's own nefBytesToJpegBytes under Node, and checks the result with Pillow. Skipped without Node.
"""
import io
import json
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / 'admin' / 'story-studio' / 'index.html'
NODE = (os.environ.get('NODE') or shutil.which('node')
        or str(Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'))
RUNNER = r"""
const fs=require('fs'),vm=require('vm');
const html=fs.readFileSync(process.argv[2],'utf8');
const a=html.indexOf('// NEF-BEGIN'),b=html.indexOf('// NEF-END');
const ctx={};vm.createContext(ctx);vm.runInContext(html.slice(a,b)+'\nthis.f=nefBytesToJpegBytes;',ctx);
try{const out=ctx.f(new Uint8Array(fs.readFileSync(process.argv[3])));fs.writeFileSync(process.argv[4],Buffer.from(out));}
catch(e){console.error('ERR:'+e.message);process.exit(3)}
"""


def jpeg(size, color):
    out = io.BytesIO()
    Image.new('RGB', size, color).save(out, 'JPEG')
    return out.getvalue()


class Tiff:
    """Tiny TIFF writer: IFDs as {tag: (type, count, bytes)} with out-of-line values placed after the IFDs."""
    def __init__(self, le):
        self.le = le
        self.e = '<' if le else '>'

    def pack(self, fmt, *v):
        return struct.pack(self.e + fmt, *v)

    def ifd_blob(self, entries, start, next_off=0):
        """Returns (ifd bytes, data bytes placed at start+ifd_len)."""
        n = len(entries)
        ifd_len = 2 + 12 * n + 4
        data = b''
        body = self.pack('H', n)
        for tag, (typ, count, raw) in sorted(entries.items()):
            if len(raw) <= 4:
                val = raw.ljust(4, b'\0')
            else:
                val = self.pack('I', start + ifd_len + len(data))
                data += raw + (b'\0' if len(raw) & 1 else b'')
            body += self.pack('HHI', tag, typ, count) + val
        return body + self.pack('I', next_off), data


def rationals(le, *pairs):
    e = '<' if le else '>'
    return b''.join(struct.pack(e + 'II', a, b) for a, b in pairs)


def build_nef(le=True, previews=(), nikon_preview=None, orientation=6):
    """previews: JPEG byte strings placed via SubIFD. nikon_preview: JPEG placed via the Nikon maker note."""
    t = Tiff(le)
    head = (b'II' if le else b'MM') + t.pack('H', 42) + t.pack('I', 8)
    body = bytearray()  # everything after the 8-byte header; offsets are absolute (8 + index)

    def place(raw):
        off = 8 + len(body)
        body.extend(raw + (b'\0' if len(raw) & 1 else b''))
        return off

    jpg_offsets = [(place(j), len(j)) for j in previews]
    nk_off = nk_len = 0
    if nikon_preview:
        nk_off, nk_len = place(nikon_preview), len(nikon_preview)

    # Nikon maker note: "Nikon\0" 0x02 0x10 0x00 0x00 + TIFF header, then an IFD with tag 17 -> preview IFD
    maker = b''
    if nikon_preview:
        mt = Tiff(le)
        mhead = (b'II' if le else b'MM') + mt.pack('H', 42) + mt.pack('I', 8)
        # preview IFD offsets are relative to the maker-note TIFF header; our JPEG sits in the main file, so we
        # store it again inside the maker note region instead (as real Nikon files do).
        mk_body = bytearray()
        prev_ifd_off = 8 + 2 + 12 + 4  # after the one-entry main maker IFD
        main_ifd, _ = mt.ifd_blob({17: (4, 1, mt.pack('I', prev_ifd_off))}, 8)
        jpg_rel = prev_ifd_off + 2 + 2 * 12 + 4
        prev_ifd, _ = mt.ifd_blob({513: (4, 1, mt.pack('I', jpg_rel)), 514: (4, 1, mt.pack('I', nk_len))}, prev_ifd_off)
        maker = b'Nikon\0\x02\x10\0\0' + mhead + main_ifd + prev_ifd + nikon_preview

    # sub IFDs (one per preview)
    sub_offsets = []
    for off, ln in jpg_offsets:
        ifd, _ = t.ifd_blob({513: (4, 1, t.pack('I', off)), 514: (4, 1, t.pack('I', ln))}, 0)
        sub_offsets.append(place(ifd))

    gps_entries = {1: (2, 2, b'N\0'), 2: (5, 3, rationals(le, (44, 1), (50, 1), (3600, 100))),
                   3: (2, 2, b'W\0'), 4: (5, 3, rationals(le, (0, 1), (34, 1), (3000, 100)))}
    gps_off_slot = len(body)
    exif_entries = {33434: (5, 1, rationals(le, (1, 250))), 33437: (5, 1, rationals(le, (28, 10))),
                    34855: (3, 1, t.pack('H', 400)), 36867: (2, 20, b'2026:10:05 09:14:03\0')}
    if maker:
        exif_entries[37500] = (7, len(maker), maker)

    # Layout: place GPS IFD, Exif IFD, then IFD0 (so every offset is known before it is written).
    def place_ifd(entries):
        off = 8 + len(body)
        # values that are out of line follow the IFD directly; compute with the real start offset
        ifd, data = t.ifd_blob(entries, off)
        body.extend(ifd + data + (b'\0' if len(data) & 1 else b''))
        return off

    gps_off = place_ifd(gps_entries)
    exif_off = place_ifd(exif_entries)
    ifd0 = {271: (2, 6, b'NIKON\0'), 272: (2, 9, b'NIKON D90\0'), 274: (3, 1, t.pack('H', orientation)),
            306: (2, 20, b'2026:10:05 09:14:03\0'), 34665: (4, 1, t.pack('I', exif_off)),
            34853: (4, 1, t.pack('I', gps_off))}
    if sub_offsets:
        ifd0[330] = (4, len(sub_offsets), b''.join(t.pack('I', o) for o in sub_offsets))
    ifd0_off = place_ifd(ifd0)
    head = head[:4] + t.pack('I', ifd0_off)
    return head + bytes(body)


@unittest.skipUnless(os.path.exists(NODE) or shutil.which(NODE), 'Node is not available here')
class NefConversion(unittest.TestCase):
    def convert(self, nef_bytes):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / 'in.nef').write_bytes(nef_bytes)
            (td / 'run.cjs').write_text(RUNNER, encoding='utf-8')
            r = subprocess.run([NODE, str(td / 'run.cjs'), str(HTML), str(td / 'in.nef'), str(td / 'out.jpg')],
                               capture_output=True, text=True)
            if r.returncode:
                return None, r.stderr.strip()
            return (td / 'out.jpg').read_bytes(), ''

    def check_details(self, out):
        with Image.open(io.BytesIO(out)) as im:
            ex = im.getexif()
            self.assertEqual(ex.get(271), 'NIKON')
            self.assertEqual(ex.get(272), 'NIKON D90')
            self.assertEqual(ex.get(274), 6)
            sub = ex.get_ifd(0x8769)
            self.assertEqual(sub.get(36867), '2026:10:05 09:14:03')
            self.assertEqual(sub.get(34855), 400)
            self.assertAlmostEqual(float(sub.get(33437)), 2.8, places=2)
            gps = ex.get_ifd(0x8825)
            self.assertEqual((gps.get(1), gps.get(3)), ('N', 'W'))
            self.assertAlmostEqual(float(gps[2][0]) + float(gps[2][1]) / 60 + float(gps[2][2]) / 3600, 44.8433, places=3)
            return im.size

    def test_subifd_preview_is_extracted_with_the_cameras_details(self):
        for le in (True, False):
            with self.subTest(little_endian=le):
                out, err = self.convert(build_nef(le, previews=[jpeg((160, 120), 'red')]))
                self.assertIsNotNone(out, err)
                self.assertEqual(self.check_details(out), (160, 120))

    def test_largest_jpeg_wins_over_thumbnails(self):
        nef = build_nef(True, previews=[jpeg((40, 30), 'blue'), jpeg((640, 480), 'green'), jpeg((160, 120), 'red')])
        out, err = self.convert(nef)
        self.assertIsNotNone(out, err)
        self.assertEqual(self.check_details(out), (640, 480))

    def test_preview_stored_in_the_nikon_maker_note(self):
        for le in (True, False):
            with self.subTest(little_endian=le):
                nef = build_nef(le, previews=[jpeg((40, 30), 'blue')], nikon_preview=jpeg((800, 600), 'yellow'))
                out, err = self.convert(nef)
                self.assertIsNotNone(out, err)
                self.assertEqual(self.check_details(out), (800, 600))

    def test_existing_exif_in_the_preview_is_replaced_not_duplicated(self):
        src = io.BytesIO()
        im = Image.new('RGB', (200, 100), 'purple')
        ex = Image.Exif(); ex[271] = 'SOMEONE ELSE'
        im.save(src, 'JPEG', exif=ex)
        out, err = self.convert(build_nef(True, previews=[src.getvalue()]))
        self.assertIsNotNone(out, err)
        self.assertEqual(out.count(b'Exif\0\0'), 1)
        self.assertEqual(self.check_details(out), (200, 100))

    def test_files_that_are_not_nef_or_have_no_preview_are_refused_cleanly(self):
        out, err = self.convert(b'not a tiff at all, just some text bytes' * 4)
        self.assertIsNone(out)
        self.assertIn('does not look like a NEF', err)
        out, err = self.convert(build_nef(True, previews=[]))
        self.assertIsNone(out)
        self.assertIn('no embedded JPEG preview', err)

    def test_output_is_a_normal_jpeg_the_existing_pipeline_accepts(self):
        out, err = self.convert(build_nef(True, previews=[jpeg((320, 240), 'orange')]))
        self.assertIsNotNone(out, err)
        import sys
        sys.path.insert(0, str(ROOT / 'api'))
        import story_studio_core as core
        web, w, h = core.prepare_photo(out)
        self.assertEqual((w, h), (240, 320))  # orientation 6 (rotate) is applied by the existing pipeline
        meta = core.extract_metadata(out)
        self.assertEqual(meta.get('camera'), 'NIKON D90')
        self.assertIn('44.8433', meta.get('location', ''))


if __name__ == '__main__':
    unittest.main()
