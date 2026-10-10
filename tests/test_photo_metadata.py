# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Clint and Liz DuBois. See LICENSE and NOTICE.md.
import io
import sys
import unittest
from pathlib import Path
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'))
from story_studio_core import extract_metadata, coordinates
from story_studio_core import prepare_photo
from unittest.mock import MagicMock, patch
import studio_api as api
from test_story_api import request, KEY, PHOTO


class MetadataTests(unittest.TestCase):
    def test_metadata_is_private_and_reads_original_for_edited_copy(self):
        edited='33333333-3333-4333-8333-333333333333'
        req=MagicMock(headers=request().headers,route_params={'draft':KEY,'photo':edited,'variant':'metadata'})
        client=MagicMock()
        draft={'photos':[{'id':PHOTO},{'id':edited,'source_photo_id':PHOTO,'width':30,'height':20}]}
        with patch.object(api,'storage',return_value=client),patch.object(api,'read_draft',return_value=(draft,'v1')),patch('story_studio_core.extract_metadata',return_value={'tags':{}}):
            res=api.handle_media(req)
            self.assertEqual(res.status_code,200)
            client.get_blob_client.assert_called_once_with('drafts',f'{KEY}/{PHOTO}/original')
            self.assertIn('original photo',res.get_body().decode())
        denied=MagicMock(headers=request(role='authenticated').headers,route_params=req.route_params)
        with patch.object(api,'storage') as storage:
            self.assertEqual(api.handle_media(denied).status_code,403)
            storage.assert_not_called()

    def test_capture_details_and_public_stripping(self):
        exif=Image.Exif();exif[271]='Example camera';exif[36867]='2026:10:07 12:34:56';exif[36881]='-07:00'
        out=io.BytesIO();Image.new('RGB',(80,60)).save(out,'JPEG',exif=exif)
        raw=out.getvalue();details=extract_metadata(raw)
        self.assertEqual(details['taken'],'2026:10:07 12:34:56')
        self.assertEqual(details['timezone'],'-07:00')
        self.assertEqual(details['dimensions'],'80 × 60')
        prepared,_,_=prepare_photo(raw)
        self.assertFalse(Image.open(io.BytesIO(prepared)).getexif())

    def test_missing_metadata_and_coordinates(self):
        out=io.BytesIO();Image.new('RGB',(20,30)).save(out,'PNG')
        details=extract_metadata(out.getvalue())
        self.assertNotIn('taken',details)
        self.assertNotIn('location',details)
        self.assertAlmostEqual(coordinates((48,30,0),'N'),48.5)
        self.assertAlmostEqual(coordinates((123,15,0),'W'),-123.25)
