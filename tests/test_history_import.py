# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Clint and Liz DuBois. See LICENSE and NOTICE.md.
import base64
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'tools'),str(Path(__file__).resolve().parents[1]/'api')]
import studio_api as api
import studio_import as importer
import story_studio_core as core
from test_story_api import request, KEY, PHOTO

URL='https://legacy.example/media/trip/1.jpg'

def source(body='A **trip**.\n\n![]('+URL+')'):
    return {'index.md':{'sha':'source-sha','text':'---\ntitle: A trip\ndate: 2024-06-07\ncover: '+URL+'\n---\n'+body}}

class HistoryImportTests(unittest.TestCase):
    def test_import_markdown_keeps_photos_and_source_fingerprint(self):
        with patch.object(core,'PUBLIC_MEDIA_HOST','legacy.example'):
            draft=importer.convert_post('a-trip',source(),KEY)
        self.assertIn('<strong>trip</strong>',draft['html'])
        self.assertEqual(draft['photos'][0]['src'],URL)
        self.assertTrue(draft['photos'][0]['external'])
        self.assertEqual(draft['imported']['files'],{'index.md':'source-sha'})
        self.assertFalse(draft['published']['studio_managed'])

    def test_import_rejects_script_and_untrusted_photos(self):
        with patch.object(core,'PUBLIC_MEDIA_HOST','legacy.example'):
            for body in ['<script>alert(1)</script>','![](https://untrusted.example/photo.jpg)']:
                with self.assertRaises(ValueError):importer.convert_post('a-trip',source(body),KEY)

    def test_missing_cover_is_reported_without_inventing_an_address(self):
        data=source();data['index.md']['text']=data['index.md']['text'].replace(URL,'missing.JPG',1)
        with patch.object(core,'PUBLIC_MEDIA_HOST','legacy.example'):
            draft=importer.convert_post('a-trip',data,KEY)
        self.assertEqual(draft['cover'],'');self.assertTrue(draft['imported']['warnings'])

    def test_history_coalesces_autosaves_and_force_keeps_recovery_point(self):
        client=MagicMock();draft={'title':'Test','updated':'2026-10-07T12:00:00+00:00'}
        first=api.record_version(client,KEY,draft);second=api.record_version(client,KEY,draft)
        self.assertEqual(first,second)
        self.assertNotEqual(first,api.record_version(client,KEY,draft,force=True))
        self.assertFalse(client.get_blob_client.return_value.upload_blob.call_args.kwargs['overwrite'])

    def test_restore_preserves_current_publication_and_new_assets(self):
        current={'title':'Current','date':'2026-10-07','summary':'','html':'<p>Now</p>','cover':'','photos':[],
                 'published':{'active':True,'slug':'a-trip','commit':'latest'},'imported':{'slug':'a-trip'}}
        current['photos']=[{'id':PHOTO,'src':f'/api/story-media/{KEY}/{PHOTO}','caption':'New upload'}]
        prior={**current,'photos':[],'title':'Earlier','html':'<p>Before</p>','published':{'active':False}}
        client=MagicMock();client.get_blob_client.return_value.download_blob.return_value.readall.return_value=json.dumps(prior).encode()
        with patch.object(api,'read_draft',return_value=(current,'v1')),patch.object(api,'record_version') as archive,patch.object(api,'put_draft',return_value='v2') as put:
            response=api.version_history(client,KEY,request('POST',action='versions',body={'version':PHOTO}))
        self.assertEqual(response.status_code,200);restored=json.loads(response.get_body())
        self.assertEqual(restored['title'],'Earlier');self.assertEqual(restored['published'],current['published'])
        self.assertEqual(restored['imported'],current['imported']);self.assertEqual(restored['photos'],current['photos']);archive.assert_called_once_with(client,KEY,current,force=True)
        self.assertEqual(put.call_args.args[-1],'v1')

    def test_stale_restore_writes_nothing(self):
        client=MagicMock()
        with patch.object(api,'read_draft',return_value=({},'changed')),patch.object(api,'record_version') as archive,patch.object(api,'put_draft') as put:
            self.assertEqual(api.version_history(client,KEY,request('POST',action='versions',body={'version':PHOTO})).status_code,409)
        archive.assert_not_called();put.assert_not_called();client.get_blob_client.assert_not_called()

    def test_reimport_opens_private_edits_without_overwriting_them(self):
        stored={'id':KEY,'title':'My private edits','html':'<p>Work in progress</p>'}
        with patch.object(api,'PostRepository') as repository,patch.object(api,'read_draft',return_value=(stored,'v2')),patch.object(api,'put_draft') as put:
            repository.return_value.post.return_value=source()
            result=api.import_posts(MagicMock(),request('POST',body={'slug':'a-trip'}))
        self.assertEqual(json.loads(result.get_body()),stored);put.assert_not_called()

    def test_changed_source_imports_into_a_distinct_draft(self):
        keys=[]
        with patch.object(core,'PUBLIC_MEDIA_HOST','legacy.example'),patch.object(api,'PostRepository') as repository,patch.object(api,'read_draft',side_effect=api.ResourceNotFoundError('missing')),patch.object(api,'put_draft',return_value='v1') as put:
            for sha in ['first','changed']:
                data=source();data['index.md']['sha']=sha;repository.return_value.post.return_value=data
                result=api.import_posts(MagicMock(),request('POST',body={'slug':'a-trip'}));keys.append(json.loads(result.get_body())['id'])
        self.assertNotEqual(*keys)
        self.assertTrue(all(call.kwargs['new'] for call in put.call_args_list))

    def test_imported_publish_replaces_markdown_only_if_source_is_unchanged(self):
        with patch.object(core,'PUBLIC_MEDIA_HOST','legacy.example'):
            draft=importer.convert_post('a-trip',source(),KEY)
        for changed in (False,True):
            client=MagicMock();session=MagicMock()
            session.get.return_value.status_code=200;session.get.return_value.json.return_value=[{'name':'index.md','sha':'changed' if changed else 'source-sha'}]
            answers=[{'object':{'sha':'base'}},{'tree':{'sha':'tree-base'}},{'sha':'tree-new'},{'sha':'commit-new'},{}]
            session.request.side_effect=[MagicMock(ok=True,json=MagicMock(return_value=v)) for v in answers]
            with patch.object(core,'PUBLIC_MEDIA_HOST','legacy.example'),patch.dict(api.os.environ,{'STUDIO_ALLOW_PUBLISH':'true','STUDIO_GITHUB_TOKEN':'fake'}),patch.object(api.Path,'read_text',return_value='{"profile":"production"}'),patch.object(api,'read_draft',return_value=(draft.copy(),'v1')),patch.object(api,'put_draft'),patch.object(api.requests,'Session',return_value=session):
                if changed:
                    with self.assertRaisesRegex(ValueError,'original post changed'):api.publish(client,KEY,request('POST',action='publish',body={'slug':'a-trip'}))
                else:
                    self.assertEqual(api.publish(client,KEY,request('POST',action='publish',body={'slug':'a-trip'})).status_code,200)
                    tree=session.request.call_args_list[2].kwargs['json']['tree']
                    self.assertTrue(any(row['path'].endswith('index.md') and row['sha'] is None for row in tree))
                    meta=json.loads(tree[0]['content']);self.assertEqual(meta['cover'],URL)
            self.assertFalse(any(call.args[0]=='published' for call in client.get_blob_client.call_args_list))

if __name__=='__main__':unittest.main()
