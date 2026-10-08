"""Storage-independent validation for the CKEditor draft workflow.

Draft HTML is validated rather than flattened into Markdown. Unknown markup
is rejected with a useful error so save/reopen cannot silently lose layouts.
"""
from __future__ import annotations

import datetime as dt
import io
import math
import os
import re
import warnings
from html.parser import HTMLParser
from urllib.parse import urlsplit

from PIL import Image, ImageOps, ExifTags

_heif_ready = None


def enable_heif():
    """Registers the HEIC/HEIF reader (pillow-heif) the first time a photo is prepared, not at import time, so a
    missing or broken install cannot take the whole API down (same approach as the WestCoastViewNavion site).
    HEIC photos are then refused as unreadable instead."""
    global _heif_ready
    if _heif_ready is None:
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
            _heif_ready = True
        except Exception:
            _heif_ready = False
    return _heif_ready


MAX_PHOTO_BYTES = 20 * 1024 * 1024
MAX_HTML_BYTES = 2 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 40_000_000
PUBLIC_MEDIA_HOST = os.environ.get('STUDIO_LEGACY_MEDIA_HOST','')
STUDIO_MEDIA_HOST = os.environ.get('STUDIO_STORAGE_ACCOUNT','') + '.blob.core.windows.net'


def safe_url(value: str, image=False) -> bool:
    if not isinstance(value, str) or re.search(r'[\x00-\x20\\]', value):
        return False
    parts = urlsplit(value)
    if image:
        return (parts.scheme == 'https' and ((parts.hostname == PUBLIC_MEDIA_HOST
                and parts.path.startswith('/media/')) or (parts.hostname == STUDIO_MEDIA_HOST
                and parts.path.startswith('/published/')))) or bool(
                    re.fullmatch(r'/api/story-media/[0-9a-f-]{36}/[0-9a-f-]{36}(?:/thumbnail)?', value))
    return (parts.scheme in {'https', 'http', 'mailto'} and not parts.username) or (
        value.startswith(('/', '#')) and not value.startswith('//'))


STORY_MEDIA_PATH = r'/api/story-media/[0-9a-f-]{36}/[0-9a-f-]{36}(?:/thumbnail)?'
_ABSOLUTE_IMG_SRC = re.compile(r'(\bsrc=")https?://[^/"\s]+(' + STORY_MEDIA_PATH + r'")')
_THUMBNAIL_IMG_SRC = re.compile(r'(\bsrc="/api/story-media/[0-9a-f-]{36}/[0-9a-f-]{36})/thumbnail"')
_ABSOLUTE_COVER = re.compile(r'https?://[^/\s]+(' + STORY_MEDIA_PATH + r')')


def localize_story_media(html: str, cover: str):
    """The editor (or the browser) can hold a studio photo under the site's full web address instead of the short
    /api/story-media/... form. Both name the same photo on the same site, so store the short form. Only that exact
    photo path is rewritten; any other address still has to pass the normal check."""
    html = _ABSOLUTE_IMG_SRC.sub(r'\1\2', html)
    # A tile dragged from the photo library carries the small thumbnail's address; a picture in the story is the
    # photo itself (publishing makes the small and large versions), so keep the photo's own address.
    html = _THUMBNAIL_IMG_SRC.sub(r'\1"', html)
    m = _ABSOLUTE_COVER.fullmatch(cover or '')
    cover = m.group(1) if m else cover
    if re.fullmatch(STORY_MEDIA_PATH, cover or '') and cover.endswith('/thumbnail'):
        cover = cover[:-len('/thumbnail')]
    return html, cover


def describe_address(value) -> str:
    """The rejected address for an error message. Addresses are not story text; long ones (a picture still
    uploading is a huge data: address) are cut short so the message stays readable."""
    text = str(value if value is not None else '')
    if text.startswith('data:'):
        text = text.split(',', 1)[0] + ',...'
    return text[:90] + ('...' if len(text) > 90 else '') if text else '(empty)'


class StoryHTML(HTMLParser):
    tags = set('p h2 h3 h4 strong b em i u s del span a ul ol li blockquote '
               'figure figcaption img table thead tbody tfoot tr td th caption '
               'hr br code pre div'.split())
    classes = set('image image-inline image_resized image-style-side '
                  'image-style-align-left image-style-align-right '
                  'image-style-align-center image-style-block-align-left '
                  'image-style-block-align-right table photo-gallery'.split())
    void = {'img', 'br', 'hr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.tags:
            raise ValueError(f'Unsupported story element: {tag}. Please remove it before saving.')
        allowed = {'class', 'style'}
        if tag == 'img': allowed |= {'src', 'alt', 'width', 'height', 'loading'}
        if tag == 'a': allowed |= {'href', 'target', 'rel', 'title'}
        if tag in {'td', 'th'}: allowed |= {'colspan', 'rowspan'}
        if tag == 'ol': allowed |= {'start', 'reversed', 'type'}
        if tag == 'li': allowed |= {'value', 'data-list-item-id'}
        for name, value in attrs:
            if name not in allowed:
                raise ValueError(f'Unsupported story attribute: {name}.')
            if name == 'class' and any(c not in self.classes for c in (value or '').split()):
                raise ValueError('Unsupported photo or table layout.')
            if name == 'style': self.check_style(value or '')
            if name in {'src', 'href'} and not safe_url(value, image=name == 'src'):
                raise ValueError('The story contains an unsupported ' + ('picture' if name == 'src' else 'link')
                                 + ' address: ' + describe_address(value) + '.')
            if name in {'width', 'height', 'colspan', 'rowspan', 'start', 'value'} and not re.fullmatch(r'\d{1,5}', value or ''):
                raise ValueError('Invalid image or table size.')
            if name == 'target' and value not in {'_blank', '_self'}:
                raise ValueError('Unsupported link target.')
            if name == 'loading' and value not in {'lazy','eager'}:
                raise ValueError('Unsupported photo loading option.')
            if name == 'data-list-item-id' and not re.fullmatch(r'[a-z0-9]{16,64}',value or ''):
                raise ValueError('Invalid list item identifier.')
            if name == 'rel' and not set((value or '').split()) <= {'noopener','noreferrer','nofollow'}:
                raise ValueError('Unsupported link option.')
        if tag == 'img':
            src = dict(attrs).get('src')
            if not src: raise ValueError('A story photo has no address.')
            self.images.append(src)
        if tag not in self.void: self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.void: self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in self.void: return
        if not self.stack or self.stack.pop() != tag:
            raise ValueError('The story markup is incomplete. Please reload the editor.')

    def handle_decl(self, decl):
        raise ValueError('Document declarations are not allowed in a story.')

    @staticmethod
    def check_style(value):
        for declaration in value.split(';'):
            if not declaration.strip(): continue
            if ':' not in declaration: raise ValueError('Invalid text styling.')
            prop, val = [p.strip().lower() for p in declaration.split(':', 1)]
            valid = False
            if prop in {'color','background-color'}:
                valid = bool(re.fullmatch(r'#[0-9a-f]{3,8}|[a-z]+|rgba?\([\d., %]+\)|hsla?\([\d., %]+\)',val))
            elif prop in {'width','height','max-width','font-size','margin-left'}:
                valid = bool(re.fullmatch(r'(?:\d+(?:\.\d+)?(?:%|px|pt|em|rem)|auto)',val))
            elif prop == 'text-align': valid = val in {'left','right','center','justify'}
            elif prop == 'float': valid = val in {'left','right','none'}
            elif prop == 'aspect-ratio': valid = bool(re.fullmatch(r'[1-9]\d{0,4}\s*/\s*[1-9]\d{0,4}',val))
            elif prop == 'font-family': valid = bool(re.fullmatch(r'[a-z ,"\'-]+',val))
            if not valid: raise ValueError(f'Unsupported text or photo style: {prop}.')


def validate_draft(data):
    if not isinstance(data, dict): raise ValueError('Expected a draft object.')
    title = data.get('title', '')
    summary = data.get('summary', '')
    html = data.get('html', '')
    if not isinstance(title,str) or not 1 <= len(title.strip()) <= 200:
        raise ValueError('Add a title of up to 200 characters.')
    if not isinstance(summary,str) or len(summary) > 2000:
        raise ValueError('Keep the summary under 2,000 characters.')
    date = data.get('date')
    try:
        if dt.date.fromisoformat(date).isoformat() != date: raise ValueError()
    except (ValueError,TypeError): raise ValueError('Choose a valid post date.') from None
    if not isinstance(html,str) or len(html.encode('utf-8')) > MAX_HTML_BYTES:
        raise ValueError('The story is too large. Upload photos through the photo library.')
    html, cover_in = localize_story_media(html, data.get('cover', ''))
    parser = StoryHTML()
    parser.feed(html)
    parser.close()
    if parser.stack: raise ValueError('The story contains unclosed formatting.')
    cover = cover_in
    if cover and not safe_url(cover,image=True): raise ValueError('Choose a valid cover photo.')
    return {'title':title.strip(),'date':date,'summary':summary,'html':html,'cover':cover}, parser.images


def prepare_photo(raw: bytes):
    enable_heif()
    if not raw or len(raw) > MAX_PHOTO_BYTES: raise ValueError('Choose a photo under 20 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as test:
                # JPEG-based multi-picture files can arrive with a .jpg name.
                # Decode only their primary image; auxiliary frames stay private.
                if test.format not in {'JPEG','MPO','PNG','WEBP','HEIF'}:
                    raise ValueError(f'This photo is {test.format}, which is not supported. Export it as JPG, PNG, WebP, or HEIC.')
                test.verify()
            with Image.open(io.BytesIO(raw)) as source:
                # A HEIC file opens on its primary image already; the first frame of a JPEG-based multi-picture
                # file is its primary image, so only those are rewound.
                if source.format != 'HEIF': source.seek(0)
                im = ImageOps.exif_transpose(source)
                im.thumbnail((1800,1800), Image.Resampling.LANCZOS)
                if im.mode in {'RGBA','LA'} or 'transparency' in im.info:
                    rgba=im.convert('RGBA'); bg=Image.new('RGB',im.size,'white');bg.paste(rgba,mask=rgba.getchannel('A'));im=bg
                out=io.BytesIO();im.convert('RGB').save(out,'JPEG',quality=88,optimize=True)
                return out.getvalue(),im.width,im.height
    except (Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise ValueError('This photo has too many pixels; resize it before adding.') from None
    except (OSError,SyntaxError): raise ValueError('This file could not be read as a photo.') from None


def thumbnail(web_jpeg):
    with Image.open(io.BytesIO(web_jpeg)) as image:
        image.thumbnail((720,720),Image.Resampling.LANCZOS)
        result=io.BytesIO();image.save(result,'JPEG',quality=82,optimize=True)
        return result.getvalue()


def readable(value):
    if isinstance(value, bytes):
        return f'[binary data: {len(value)} bytes]'
    return str(value).replace('\x00', '').strip()[:1000]


def coordinates(values, ref):
    number = float(values[0]) + float(values[1])/60 + float(values[2])/3600
    if not math.isfinite(number):
        raise ValueError('Invalid coordinate')
    return -number if ref in ('S', 'W') else number


def extract_metadata(raw):
    enable_heif()
    with Image.open(io.BytesIO(raw)) as image:
        result = {'format': image.format, 'dimensions': f'{image.width} × {image.height}',
                  'bytes': len(raw), 'tags': {}}
        try:
            exif = image.getexif()
            tags = dict(exif)
            tags.update(exif.get_ifd(ExifTags.IFD.Exif))
            gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
            result['tags'] = {ExifTags.TAGS.get(k, str(k)): readable(v) for k, v in tags.items()}
            result['tags'].update({'GPS ' + ExifTags.GPSTAGS.get(k, str(k)): readable(v) for k, v in gps.items()})
            for field, tag in [('taken',36867),('timezone',36881),('camera',272),('make',271),('lens',42036),('iso',34855),('exposure',33434),('aperture',33437),('focal_length',37386)]:
                if tag in tags:
                    result[field] = readable(tags[tag])
            if all(k in gps for k in (1,2,3,4)):
                lat = coordinates(gps[2], gps[1]); lon = coordinates(gps[4], gps[3])
                if abs(lat)<=90 and abs(lon)<=180:
                    result['location'] = f'{lat:.6f}, {lon:.6f}'
            if 6 in gps:
                below_sea_level = gps.get(5) in (1, bytes([1]))
                altitude = float(gps[6]) * (-1 if below_sea_level else 1)
                result['altitude'] = f'{altitude:g} m'
        except (ValueError, TypeError, KeyError, IndexError, OSError, ZeroDivisionError):
            result['note'] = 'Some recorded metadata could not be read.'
        return result
