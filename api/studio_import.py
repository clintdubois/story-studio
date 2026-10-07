"""Read-only conversion of existing repository posts into Studio drafts."""
import base64
import datetime as dt
import json
import re
import uuid
from html.parser import HTMLParser
from html import escape
from urllib.parse import urlsplit
import markdown
import yaml
import requests
from story_studio_core import validate_draft, safe_url, MAX_HTML_BYTES


def slug_value(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',value) or len(value)>100:
        raise ValueError('Choose a valid post address.')
    return value


class PostRepository:
    def __init__(self,repo,token):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo) or not token:
            raise ValueError('Configure repository access before importing posts.')
        self.root='https://api.github.com/repos/'+repo
        self.session=requests.Session()
        self.session.headers.update({'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
        self.ref=self.get('/git/ref/heads/main')['object']['sha']

    def get(self,path):
        result=self.session.get(self.root+path,params={'ref':self.ref} if hasattr(self,'ref') else None,timeout=30)
        if not result.ok:raise RuntimeError('Could not read the existing posts. Your draft is unchanged.')
        return result.json()

    def posts(self):
        return [{'slug':item['name'],'title':item['name'].replace('-',' ').capitalize()} for item in self.get('/contents/content/posts')
                if item.get('type')=='dir' and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',item['name'])]

    def post(self,slug):
        slug=slug_value(slug);entries=self.get('/contents/content/posts/'+slug)
        source={}
        for entry in entries:
            if entry['name'] in {'index.md','meta.json','body.html'} and entry.get('type')=='file':
                file=self.get('/contents/content/posts/'+slug+'/'+entry['name'])
                if file.get('size',0)>MAX_HTML_BYTES:raise ValueError('This post is too large to import.')
                source[entry['name']]={'sha':file['sha'],'text':base64.b64decode(file['content']).decode('utf-8-sig')}
        return source


class ImportHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.parts=[]
    def handle_starttag(self,tag,attrs):
        # Reader-only responsive attributes are regenerated on publishing.
        attrs=[(k,v) for k,v in attrs if k not in {'srcset','sizes','data-full'}]
        self.parts.append('<'+tag+''.join(' '+k+'="'+escape(v or '',quote=True)+'"' for k,v in attrs)+'>')
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs)
    def handle_endtag(self,tag):self.parts.append('</'+tag+'>')
    def handle_data(self,value):self.parts.append(escape(value))


def convert_post(slug,source,key):
    slug=slug_value(slug)
    if 'index.md' in source:
        text=source['index.md']['text'];match=re.match(r'\A---\s*\n(.*?)\n---\s*(?:\n|$)(.*)\Z',text,re.S)
        if not match:raise ValueError('This older post has no supported metadata header.')
        meta=yaml.safe_load(match[1]);body=markdown.markdown(match[2],extensions=['extra'])
    elif 'meta.json' in source and 'body.html' in source:
        meta=json.loads(source['meta.json']['text']);body=source['body.html']['text']
    else:raise ValueError('This post has no supported story source.')
    if not isinstance(meta,dict):raise ValueError('This post has invalid metadata.')
    meta=json.loads(json.dumps(meta,default=str));parser=ImportHTML();parser.feed(body);parser.close();body=''.join(parser.parts)
    payload={'title':meta.get('title',slug),'date':str(meta.get('date',''))[:10],'summary':meta.get('excerpt','') or '',
             'html':body,'cover':meta.get('cover','') or ''}
    warnings=[]
    if payload['cover'] and not safe_url(payload['cover'],image=True):
        payload['cover']=''
        warnings.append('The original cover address could not be used. Choose a cover photo before publishing.')
    clean,images=validate_draft(payload)
    photos=[]
    for src in dict.fromkeys(images+([clean['cover']] if clean['cover'] else [])):
        if not safe_url(src,image=True) or src.startswith('/api/'):
            raise ValueError('This post has a photo that cannot be imported safely.')
        photos.append({'id':str(uuid.uuid5(uuid.NAMESPACE_URL,key+src)),'name':urlsplit(src).path.rsplit('/',1)[-1],
                       'caption':'','src':src,'thumbnail':src,'external':True,'used':src in images})
    published=None if str(meta.get('draft','false')).lower()=='true' else {'active':True,'slug':slug,'studio_managed':False}
    return {**clean,'id':key,'photos':photos,'published':published,'updated':dt.datetime.now(dt.timezone.utc).isoformat(),
            'imported':{'slug':slug,'files':{name:item['sha'] for name,item in source.items()},'meta':meta,'warnings':warnings}}
