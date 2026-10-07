"""Readable EXIF from private originals; never added to published JPEGs."""
import io
import math
from PIL import Image, ExifTags


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
    from story_studio_core import enable_heif
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
                result['altitude'] = f'{float(gps[6]) * (-1 if gps.get(5) in (1,b"\x01") else 1):g} m'
        except (ValueError, TypeError, KeyError, IndexError, OSError, ZeroDivisionError):
            result['note'] = 'Some recorded metadata could not be read.'
        return result
