import base64
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'api')]
import azure.functions as func
import studio_api as api
api.REPO="example/blog"
api.WEBSITE="https://blog.example"
from PIL import Image

KEY='11111111-1111-4111-8111-111111111111'
PHOTO='22222222-2222-4222-8222-222222222222'

def request(method='GET',role='studio_editor',body=None,action=None,etag='v1'):
    principal={'identityProvider':'aad','userRoles':[role]}
    headers={'x-ms-client-principal':base64.b64encode(json.dumps(principal).encode()).decode(),'If-Match':etag}
    return func.HttpRequest(method,'https://example/api/story-studio/'+KEY,headers=headers,
                           body=json.dumps(body or {}).encode(),route_params={'id':KEY,'action':action})

class APITests(unittest.TestCase):
    def test_missing_account_cannot_open_storage(self):
        with patch.object(api,'ACCOUNT',''),patch.object(api,'BlobServiceClient') as service:
            with self.assertRaises(RuntimeError):api.storage()
            service.from_connection_string.assert_not_called()

    def test_wrong_account_cannot_open_storage(self):
        with patch.object(api,'ACCOUNT','examplestudio'),patch.dict(os.environ,{'STUDIO_STORAGE_CONNECTION_STRING':'test-only'}),patch.object(api,'BlobServiceClient') as service:
            service.from_connection_string.return_value.account_name='wrongaccount'
            with self.assertRaises(RuntimeError):api.storage()

    def test_non_editor_cannot_read_or_write(self):
        for method in ['GET','POST','PUT']:
            with patch.object(api,'storage') as storage:
                self.assertEqual(api.handle_studio(request(method,role='authenticated')).status_code,403)
                storage.assert_not_called()

    def test_preview_cannot_publish_even_with_publishing_setting(self):
        with patch.dict(os.environ,{'STUDIO_ALLOW_PUBLISH':'true','STUDIO_GITHUB_TOKEN':'not-real'}):
            self.assertEqual(api.publish(MagicMock(),KEY,request('POST',action='publish')).status_code,409)

    def test_stale_save_does_not_overwrite(self):
        with patch.object(api,'storage'),patch.object(api,'read_draft',return_value=({},'v2')),patch.object(api,'put_draft') as put:
            self.assertEqual(api.handle_studio(request('PUT')).status_code,409)
            put.assert_not_called()

    def test_upload_duplicate_names_get_distinct_ids_and_variants(self):
        image=Image.new('RGB',(800,400),'green');raw=io.BytesIO();image.save(raw,'JPEG')
        payload={'name':'same.jpg','data':base64.b64encode(raw.getvalue()).decode()}
        ids=[]
        for _ in range(2):
            client=MagicMock()
            with patch.object(api,'read_draft',return_value=({'photos':[]},'v1')),patch.object(api,'put_draft',return_value='v2'):
                result=api.upload_photo(client,KEY,request('POST',body=payload,action='photos'))
                photo=json.loads(result.get_body())['photo'];ids.append(photo['id'])
                paths=[call.args[1] for call in client.get_blob_client.call_args_list]
                self.assertTrue(any(p.endswith('/original') for p in paths))
                self.assertTrue(any(p.endswith('/web.jpg') for p in paths))
                self.assertTrue(any(p.endswith('/thumbnail.jpg') for p in paths))
        self.assertNotEqual(*ids)

    def test_unowned_photo_cannot_be_saved(self):
        payload={'title':'A trip','date':'2026-10-06','summary':'','html':f'<p><img src="/api/story-media/{KEY}/{PHOTO}"></p>','cover':'','photos':[]}
        with self.assertRaises(ValueError):api.checked_draft(payload,KEY,{'photos':[]})

    def test_invalid_photo_writes_nothing(self):
        client=MagicMock()
        with patch.object(api,'read_draft',return_value=({'photos':[]},'v1')):
            with self.assertRaises(ValueError):api.upload_photo(client,KEY,request('POST',body={'name':'bad.jpg','data':base64.b64encode(b'not a photo').decode()}))
        client.get_blob_client.assert_not_called()

    def test_publish_commits_both_files_and_keeps_original_private(self):
        src=f'/api/story-media/{KEY}/{PHOTO}'
        draft={'title':'Reviewed trip','date':'2026-10-06','summary':'A trip',
               'html':f'<figure class="image image-style-side"><img src="{src}"></figure>',
               'cover':src,'photos':[{'id':PHOTO,'src':src,'width':1200,'height':1800}]}
        client=MagicMock()
        def blob(container,path):
            obj=MagicMock();obj.url=f'https://examplestudio.blob.core.windows.net/{container}/{path}'
            obj.exists.return_value=False;obj.download_blob.return_value.readall.return_value=b'prepared'
            return obj
        client.get_blob_client.side_effect=blob
        session=MagicMock()
        session.get.return_value.status_code=404
        answers=[{'object':{'sha':'base'}},{'tree':{'sha':'tree-base'}},{'sha':'tree-new'},{'sha':'commit-new'},{'object':{'sha':'commit-new'}}]
        session.request.side_effect=[MagicMock(ok=True,json=MagicMock(return_value=value)) for value in answers]
        with patch.dict(os.environ,{'STUDIO_ALLOW_PUBLISH':'true','STUDIO_GITHUB_TOKEN':'test-only'}),\
             patch.object(api.Path,'read_text',return_value='{"profile":"production"}'),\
             patch.object(api,'read_draft',return_value=(draft,'v1')),\
             patch.object(api,'put_draft'),patch.object(api.requests,'Session',return_value=session):
            result=api.publish(client,KEY,request('POST',body={'slug':'reviewed-trip','notify':False},action='publish'))
        self.assertEqual(result.status_code,200)
        self.assertEqual(json.loads(result.get_body())['url'],'https://blog.example/post/reviewed-trip/')
        calls=session.request.call_args_list
        files=calls[2].kwargs['json']['tree']
        self.assertEqual({item['path'].split('/')[-1] for item in files},{'meta.json','body.html'})
        meta=json.loads(files[0]['content']);html=files[1]['content']
        self.assertFalse(meta['notify']);self.assertTrue(meta['cover_thumbnail'].endswith('-thumbnail.jpg'))
        self.assertIn('image-style-side',html);self.assertIn('480w',html);self.assertIn('data-full=',html)
        self.assertNotIn('/api/story-media/',html)
        self.assertFalse(calls[-1].kwargs['json']['force'])
        self.assertFalse(any(call.args[0]=='published' and call.args[1].endswith('/original') for call in client.get_blob_client.call_args_list))

if __name__=='__main__':unittest.main()
