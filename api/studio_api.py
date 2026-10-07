"""HTTP endpoints for approved Story Studio editors.

Secrets are server-only. Local shared modules are copied into api/ by the
deployment workflow; the maintained source is tools/story_studio_core.py.
"""
import base64
import datetime as dt
import json
import logging
import os
import re
import uuid
from pathlib import Path

import azure.functions as func
from azure.core import MatchConditions
from azure.core.exceptions import ResourceNotFoundError, ResourceModifiedError, ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings
import requests

from story_studio_core import validate_draft, prepare_photo, thumbnail, MAX_PHOTO_BYTES

PRIVATE='drafts'
ACCOUNT=os.environ.get('STUDIO_STORAGE_ACCOUNT','')
REPO=os.environ.get('STUDIO_GITHUB_REPOSITORY','')
WEBSITE=os.environ.get('STUDIO_PUBLIC_SITE_URL','').rstrip('/')

def response(data,status=200,etag=None):
    headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}
    if etag:headers['ETag']=etag
    return func.HttpResponse(json.dumps(data),status_code=status,mimetype='application/json',headers=headers)

def permitted(req):
    # SWA supplies this header after authentication; route rules also require
    # studio_editor. Local frontend flags never authorize a request.
    try:
        principal=json.loads(base64.b64decode(req.headers.get('x-ms-client-principal',''),validate=True))
        return principal.get('identityProvider')=='aad' and 'studio_editor' in principal.get('userRoles',[])
    except (ValueError,TypeError):return False

def identifier(value):
    try:
        if str(uuid.UUID(value))!=value:raise ValueError()
        return value
    except (ValueError,TypeError,AttributeError):raise ValueError('Invalid draft or photo identifier.') from None

def storage():
    if not re.fullmatch(r'[a-z0-9]{3,24}',ACCOUNT):raise RuntimeError('Configure the expected storage account.')
    connection=os.environ.get('STUDIO_STORAGE_CONNECTION_STRING')
    if not connection:raise RuntimeError('Draft storage has not been configured.')
    client=BlobServiceClient.from_connection_string(connection)
    if client.account_name!=ACCOUNT:raise RuntimeError('Draft storage account mismatch.')
    return client

def read_draft(client,key):
    blob=client.get_blob_client(PRIVATE,key+'/draft.json')
    download=blob.download_blob()
    return json.loads(download.readall()),download.properties.etag

def put_draft(client,key,data,etag=None,new=False):
    blob=client.get_blob_client(PRIVATE,key+'/draft.json')
    options={'overwrite':not new,'content_settings':ContentSettings(content_type='application/json')}
    if etag:options.update(etag=etag,match_condition=MatchConditions.IfNotModified)
    result=blob.upload_blob(json.dumps(data).encode(),**options)
    return result['etag']

def checked_draft(payload,key,old):
    clean,images=validate_draft(payload)
    assets={a['id']:a for a in old.get('photos',[])}
    submitted=payload.get('photos',[])
    if not isinstance(submitted,list):raise ValueError('Invalid photo library.')
    photos=[]
    for photo in submitted:
        if not isinstance(photo,dict) or photo.get('id') not in assets:raise ValueError('Upload the photo before saving.')
        asset=dict(assets[photo['id']]);caption=photo.get('caption','')
        if not isinstance(caption,str) or len(caption)>2000:raise ValueError('Keep photo captions under 2,000 characters.')
        asset['caption']=caption
        for flag in ('used','removed','reuseAvailable'):
            value=photo.get(flag,False)
            if not isinstance(value,bool):raise ValueError('Invalid photo library state.')
            asset[flag]=value
        photos.append(asset)
    # Keep assets uploaded by another tab; only captions are edited here.
    ids={a['id'] for a in photos}
    photos.extend(a for a in old.get('photos',[]) if a['id'] not in ids)
    valid={a['src'] for a in photos}
    refs=images+([clean['cover']] if clean['cover'] else [])
    if any(a.get('removed') and a['src'] in refs for a in photos):raise ValueError('Remove this photo from the story and cover first.')
    if any(url not in valid for url in refs):raise ValueError('Every story photo must belong to this draft. Add it to the library first.')
    return {**clean,'id':key,'photos':photos,'updated':dt.datetime.now(dt.timezone.utc).isoformat(),
            'published':old.get('published')}

def upload_photo(client,key,req):
    old,etag=read_draft(client,key)
    payload=req.get_json(); encoded=payload.get('data','')
    if not isinstance(encoded,str) or len(encoded)>MAX_PHOTO_BYTES*4//3+8:raise ValueError('Choose a photo under 20 MB.')
    raw=base64.b64decode(encoded,validate=True)
    image,width,height=prepare_photo(raw)
    photo_id=str(uuid.uuid4())
    name=payload.get('name','Photo')
    if not isinstance(name,str):raise ValueError('Invalid photo name.')
    name=name[:200]
    # UUIDs prevent duplicate filenames or edited copies overwriting originals.
    client.get_blob_client(PRIVATE,f'{key}/{photo_id}/original').upload_blob(raw,overwrite=False,
        content_settings=ContentSettings(content_type='application/octet-stream'))
    client.get_blob_client(PRIVATE,f'{key}/{photo_id}/web.jpg').upload_blob(image,overwrite=False,
        content_settings=ContentSettings(content_type='image/jpeg'))
    client.get_blob_client(PRIVATE,f'{key}/{photo_id}/thumbnail.jpg').upload_blob(thumbnail(image),overwrite=False,
        content_settings=ContentSettings(content_type='image/jpeg'))
    asset={'id':photo_id,'name':name,'caption':'','width':width,'height':height,
           'src':f'/api/story-media/{key}/{photo_id}',
           'thumbnail':f'/api/story-media/{key}/{photo_id}/thumbnail'}
    old.setdefault('photos',[]).append(asset)
    newetag=put_draft(client,key,old,etag)
    return response({'photo':asset},etag=newetag)

def publish(client,key,req):
    profile=json.loads((Path(__file__).parent/'studio_deployment.json').read_text())
    if profile.get('profile')!='production' or os.environ.get('STUDIO_ALLOW_PUBLISH')!='true':
        return response({'error':'Publishing is disabled in this environment. Your draft is saved.'},409)
    token=os.environ.get('STUDIO_GITHUB_TOKEN')
    if not token:return response({'error':'Publishing credentials have not been configured. Your draft is saved.'},503)
    old,etag=read_draft(client,key)
    if req.headers.get('If-Match')!=etag:return response({'error':'This draft changed. Reload before publishing.'},409)
    # Prevent two concurrent publishers for this draft; draft saves retain
    # their own ETag check. The reviewed snapshot is immutable during publish.
    lock=client.get_blob_client(PRIVATE,key+'/publish.lock')
    try:lock.upload_blob(b'',overwrite=False)
    except ResourceExistsError:pass
    try:lease=lock.acquire_lease(lease_duration=60)
    except Exception:return response({'error':'This draft is already publishing. Try again after it finishes.'},409)
    try:
        options=req.get_json();slug=options.get('slug','')
        if not isinstance(slug,str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug) or len(slug)>100:
            raise ValueError('Use a short address containing lowercase letters, numbers, and hyphens.')
        if old.get('published') and old['published']['slug']!=slug:raise ValueError('Keep the existing published address.')
        if (old.get('published') or {}).get('active') is False and options.get('notify'):
            sitemap=requests.get(WEBSITE+'/sitemap.xml',timeout=30)
            if not sitemap.ok:raise ValueError('Cannot verify the offline version yet. Try publishing again later.')
            if re.search(r'<loc>[^<]*/post/'+re.escape(slug)+r'/?</loc>',sitemap.text):
                raise ValueError('Wait until unpublishing finishes before republishing with subscriber email.')
        clean,images=validate_draft(old)
        # GitHub git-data API creates both files in one commit; updating the
        # branch is fast-forward only, so unrelated changes are never overwritten.
        session=requests.Session();session.headers.update({'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',REPO):raise ValueError('Configure the publishing repository.')
        if not re.fullmatch(r'https://[A-Za-z0-9.-]+(?::[0-9]+)?',WEBSITE):raise ValueError('Configure an HTTPS public site origin.')
        api='https://api.github.com/repos/'+REPO
        def gh(method,path,body=None):
            r=session.request(method,api+path,json=body,timeout=30)
            if not r.ok:raise RuntimeError('GitHub could not complete publishing. Your draft is safe.')
            return r.json()
        ref=gh('GET','/git/ref/heads/main')['object']['sha'];commit=gh('GET','/git/commits/'+ref)
        existing=session.get(api+'/contents/content/posts/'+slug,params={'ref':ref},timeout=30)
        if existing.status_code not in {200,404}:raise RuntimeError('Could not check the post address.')
        if existing.status_code==200:
            entries={item['name'] for item in existing.json()}
            if 'index.md' in entries:raise ValueError('This address belongs to an older post. Choose a new address.')
            prior=gh('GET','/contents/content/posts/'+slug+'/meta.json?ref='+ref)
            prior_meta=json.loads(base64.b64decode(prior['content']))
            if prior_meta.get('studio_draft_id')!=key:raise ValueError('That post address already exists. Choose a different address.')
        urls={}
        thumbs={}
        for asset in old.get('photos',[]):
            if asset['src'] not in images and asset['src']!=clean['cover']:continue
            lease.renew()
            photo_id=identifier(asset['id']);path=f'{slug}/{photo_id}.jpg'
            public=client.get_blob_client('published',path)
            # Existing UUID bytes are immutable. An edited photo always has a new UUID.
            if not public.exists():
                prepared=client.get_blob_client(PRIVATE,f'{key}/{photo_id}/web.jpg').download_blob().readall()
                public.upload_blob(prepared,overwrite=False,content_settings=ContentSettings(content_type='image/jpeg',cache_control='public, max-age=31536000, immutable'))
            urls[asset['src']]=public.url
            thumb=client.get_blob_client('published',f'{slug}/{photo_id}-thumbnail.jpg')
            if not thumb.exists():
                thumb.upload_blob(client.get_blob_client(PRIVATE,f'{key}/{photo_id}/thumbnail.jpg').download_blob().readall(),overwrite=False,
                    content_settings=ContentSettings(content_type='image/jpeg',cache_control='public, max-age=31536000, immutable'))
            width=asset.get('width',1800);height=asset.get('height',1800)
            thumbs[public.url]=(thumb.url,width,round(width*min(1,720/max(width,height))))
        html=clean['html']
        for private,public in urls.items():html=html.replace(private,public)
        def responsive(match):
            tag=match.group(0);url=match.group(1)
            if url not in thumbs:return tag
            small,width,thumb_width=thumbs[url]
            # The browser selects a thumbnail for smaller display sizes; the
            # lightbox always uses data-full. Portrait widths can be below 720.
            sources=f'{small} {thumb_width}w'
            if width>thumb_width:sources+=f', {url} {width}w'
            return tag[:-1]+f' data-full="{url}" srcset="{sources}" sizes="(max-width: 640px) 100vw, 50vw" loading="lazy">'
        html=re.sub(r'<img\b[^>]*\bsrc="([^"]+)"[^>]*>',responsive,html)
        meta={'title':clean['title'],'slug':slug,'date':clean['date'],'excerpt':clean['summary'],
              'cover':urls.get(clean['cover'],''),'draft':False,'notify':bool(options.get('notify',False)),
              'editor_format':'ckeditor','studio_draft_id':key}
        if meta['cover']:meta['cover_thumbnail']=thumbs[meta['cover']][0]
        tree=gh('POST','/git/trees',{'base_tree':commit['tree']['sha'],'tree':[
            {'path':f'content/posts/{slug}/meta.json','mode':'100644','type':'blob','content':json.dumps(meta,ensure_ascii=False,indent=2)},
            {'path':f'content/posts/{slug}/body.html','mode':'100644','type':'blob','content':html}]})
        newcommit=gh('POST','/git/commits',{'message':'Publish reviewed Story Studio post: '+clean['title'],'tree':tree['sha'],'parents':[ref]})
        lease.renew()
        gh('PATCH','/git/refs/heads/main',{'sha':newcommit['sha'],'force':False})
        old['published']={'active':True,'slug':slug,'commit':newcommit['sha'],'time':dt.datetime.now(dt.timezone.utc).isoformat()}
        try:put_draft(client,key,old,etag)
        except ResourceModifiedError:
            # A new draft edit after the snapshot must not be overwritten.
            latest,newetag=read_draft(client,key);latest['published']=old['published'];put_draft(client,key,latest,newetag)
        return response({'success':True,'commit':newcommit['sha'],'url':WEBSITE+'/post/'+slug+'/',
                         'message':'Publishing started. The site build will make this version live.'})
    finally:lease.release()

def unpublish(client,key,req):
    profile=json.loads((Path(__file__).parent/'studio_deployment.json').read_text())
    if profile.get('profile')!='production' or os.environ.get('STUDIO_ALLOW_PUBLISH')!='true':
        return response({'error':'Publishing is disabled in this environment.'},409)
    token=os.environ.get('STUDIO_GITHUB_TOKEN')
    if not token:return response({'error':'Publishing credentials are not configured.'},503)
    old,etag=read_draft(client,key)
    if req.headers.get('If-Match')!=etag:return response({'error':'This draft changed. Reload before unpublishing.'},409)
    published=old.get('published') or {};slug=published.get('slug','')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug):raise ValueError('This draft has not been published.')
    lock=client.get_blob_client(PRIVATE,key+'/publish.lock')
    try:lock.upload_blob(b'',overwrite=False)
    except ResourceExistsError:pass
    try:lease=lock.acquire_lease(lease_duration=60)
    except Exception:return response({'error':'This draft is already publishing. Try again later.'},409)
    try:
        session=requests.Session();session.headers.update({'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
        api='https://api.github.com/repos/'+REPO
        def gh(method,path,body=None):
            r=session.request(method,api+path,json=body,timeout=30)
            if not r.ok:raise RuntimeError('GitHub could not complete unpublishing. Your draft is safe.')
            return r.json()
        ref=gh('GET','/git/ref/heads/main')['object']['sha'];commit=gh('GET','/git/commits/'+ref)
        prior=gh('GET','/contents/content/posts/'+slug+'/meta.json?ref='+ref)
        meta=json.loads(base64.b64decode(prior['content']))
        if meta.get('studio_draft_id')!=key:raise ValueError('This post does not belong to this draft.')
        # Remove reader-facing files, so legacy draft-preview builds cannot expose the withdrawn story.
        # The editable source remains in private Studio storage.
        tree=gh('POST','/git/trees',{'base_tree':commit['tree']['sha'],'tree':[{'path':f'content/posts/{slug}/'+name,'mode':'100644','type':'blob','sha':None} for name in ('meta.json','body.html')]})
        new=gh('POST','/git/commits',{'message':'Unpublish Story Studio post: '+meta['title'],'tree':tree['sha'],'parents':[ref]})
        lease.renew();gh('PATCH','/git/refs/heads/main',{'sha':new['sha'],'force':False})
        old['published']={**published,'active':False,'commit':new['sha'],'unpublished_at':dt.datetime.now(dt.timezone.utc).isoformat()}
        try:put_draft(client,key,old,etag)
        except ResourceModifiedError:
            latest,newetag=read_draft(client,key);latest['published']=old['published'];put_draft(client,key,latest,newetag)
        return response({'success':True,'message':'Unpublishing started. Wait for the website build to finish. Your editable draft and photos are retained.'})
    finally:lease.release()

def handle_studio(req):
    if not permitted(req):return response({'error':'Microsoft sign-in with the studio_editor role is required.'},403)
    if len(req.get_body())>MAX_PHOTO_BYTES*4//3+4096:return response({'error':'The request is too large.'},413)
    try:
        client=storage();key=req.route_params.get('id');action=req.route_params.get('action')
        if not key:
            if req.method=='GET':
                drafts=[]
                for blob in client.get_container_client(PRIVATE).list_blobs():
                    if blob.name.endswith('/draft.json'):
                        draft,etag=read_draft(client,blob.name.split('/')[0]);drafts.append({k:draft.get(k) for k in ['id','title','date','updated','published']})
                return response({'drafts':sorted(drafts,key=lambda d:d.get('updated') or '',reverse=True)})
            if req.method=='POST':
                key=str(uuid.uuid4());draft={'id':key,'title':'Untitled story','date':dt.date.today().isoformat(),'summary':'','html':'<p></p>','cover':'','photos':[],'updated':dt.datetime.now(dt.timezone.utc).isoformat()}
                etag=put_draft(client,key,draft,new=True);return response(draft,201,etag)
        identifier(key)
        if action=='photos' and req.method=='POST':return upload_photo(client,key,req)
        if action=='publish' and req.method=='POST':return publish(client,key,req)
        if action=='unpublish' and req.method=='POST':return unpublish(client,key,req)
        if not action and req.method=='GET':
            draft,etag=read_draft(client,key);return response(draft,etag=etag)
        if not action and req.method=='PUT':
            old,etag=read_draft(client,key)
            if req.headers.get('If-Match')!=etag:return response({'error':'This draft changed in another tab. Reload before saving.'},409)
            clean=checked_draft(req.get_json(),key,old);newetag=put_draft(client,key,clean,etag)
            return response(clean,etag=newetag)
        return response({'error':'Unsupported action.'},405)
    except ResourceNotFoundError:return response({'error':'Draft or photo not found.'},404)
    except (ResourceModifiedError,ResourceExistsError):return response({'error':'This draft changed. Reload before trying again.'},409)
    except ValueError as error:return response({'error':str(error) or 'The draft or photo is invalid.'},400)
    except TypeError:return response({'error':'The draft or photo is invalid. Check the title, date, photo upload, and formatting.'},400)
    except Exception:
        logging.exception('Story Studio request failed')
        return response({'error':'The operation could not finish. Your saved draft has not been discarded.'},503)

def handle_media(req):
    if not permitted(req):return response({'error':'Editor sign-in required.'},403)
    try:
        draft=identifier(req.route_params.get('draft'));photo=identifier(req.route_params.get('photo'))
        variant=req.route_params.get('variant')
        if variant not in {None,'thumbnail'}:return response({'error':'Photo variant not found.'},404)
        filename='thumbnail.jpg' if variant=='thumbnail' else 'web.jpg'
        content=storage().get_blob_client(PRIVATE,f'{draft}/{photo}/{filename}').download_blob().readall()
        return func.HttpResponse(content,mimetype='image/jpeg',headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
    except ResourceNotFoundError:return response({'error':'Photo not found.'},404)
    except ValueError:return response({'error':'Invalid photo address.'},400)
    except Exception:return response({'error':'Photo storage is unavailable.'},503)
