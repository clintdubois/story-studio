import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from PIL import Image
from story_studio_core import validate_draft, prepare_photo, thumbnail
import story_studio_core
story_studio_core.PUBLIC_MEDIA_HOST="legacy.example"
story_studio_core.STUDIO_MEDIA_HOST="examplestudio.blob.core.windows.net"

URL='https://legacy.example/media/test/photo.jpg'

class StudioTests(unittest.TestCase):
    def draft(self,html):
        return {'title':'A trip','date':'2026-10-06','summary':'A story','cover':URL,'html':html}

    def test_ckeditor_gallery_and_placement_preserved(self):
        html=f'<figure class="table"><table class="photo-gallery"><tbody><tr><td><figure class="image image_resized image-style-align-right" style="width:40%;"><img src="{URL}" alt="A view"><figcaption>A view</figcaption></figure></td><td><p>Words</p></td></tr></tbody></table></figure>'
        saved,images=validate_draft(self.draft(html))
        self.assertEqual(saved['html'],html)
        self.assertEqual(images,[URL])

    def test_rejects_active_html_and_dangerous_links(self):
        for html in ['<script>alert(1)</script>','<img src="'+URL+'" onerror="alert(1)">','<a href="javascript:alert(1)">x</a>','<span style="color:red;background-image:url(x)">x</span>','<img src="data:image/png;base64,AAAA">','<img src="https://evil.example/photo.jpg">']:
            with self.subTest(html=html),self.assertRaises(ValueError): validate_draft(self.draft(html))

    def test_full_web_address_of_a_studio_photo_is_stored_in_short_form(self):
        d, p = '1bd28ab3-73b0-4d46-8a1f-0123456789ab', '2cd28ab3-73b0-4d46-8a1f-0123456789cd'
        full = f'https://studio.example.net/api/story-media/{d}/{p}'
        saved, images = validate_draft({**self.draft(f'<figure class="image"><img src="{full}" alt="x"></figure>'), 'cover': full})
        short = f'/api/story-media/{d}/{p}'
        self.assertIn(f'src="{short}"', saved['html'])
        self.assertNotIn('studio.example.net', saved['html'])
        self.assertEqual((images, saved['cover']), ([short], short))

    def test_other_full_addresses_are_still_rejected(self):
        for html in ('<p><img src="https://evil.example/photo.jpg"></p>',
                     '<p><img src="https://studio.example.net/api/other/1/2"></p>',
                     '<p><img src="https://studio.example.net/api/story-media/not-a-uuid/nope"></p>'):
            with self.assertRaises(ValueError):
                validate_draft(self.draft(html))

    def test_rejection_names_the_address_without_dumping_it(self):
        big = 'data:image/png;base64,' + 'A' * 5000
        cases = [
            (f'<p><img src="blob:https://studio.example/abc"></p>', 'picture address: blob:https://studio.example/abc'),
            (f'<p><img src="{big}"></p>', 'picture address: data:image/png;base64,...'),
            ('<p><a href="www.example.com">x</a></p>', 'link address: www.example.com'),
            ('<p><img src="/api/story-media/not-a-uuid/also-not"></p>', 'picture address: /api/story-media/not-a-uuid/also-not'),
        ]
        for html, expected in cases:
            with self.assertRaises(ValueError) as caught:
                validate_draft(self.draft(html))
            self.assertIn(expected, str(caught.exception))
            self.assertLess(len(str(caught.exception)), 200)

    def test_direct_upload_dimensions_and_list_ids_preserved(self):
        html=f'<figure class="image"><img style="aspect-ratio:1200/800;" src="{URL}" width="1200" height="800" loading="lazy"></figure><ul><li data-list-item-id="a0123456789abcdef0123456789abcdef">A stop</li></ul>'
        saved,images=validate_draft(self.draft(html))
        self.assertEqual(saved['html'],html)
        self.assertEqual(images,[URL])

    def test_broken_html_and_invalid_metadata_rejected(self):
        with self.assertRaises(ValueError): validate_draft(self.draft('<figure><p>broken</figure>'))
        draft=self.draft('<p>ok</p>');draft['date']='bad'
        with self.assertRaises(ValueError):validate_draft(draft)

    def test_photo_bytes_validated_and_metadata_removed(self):
        image=Image.new('RGB',(2000,1000),'red');raw=io.BytesIO();image.save(raw,'JPEG')
        prepared,w,h=prepare_photo(raw.getvalue())
        self.assertEqual((w,h),(1800,900))
        with Image.open(io.BytesIO(prepared)) as result:
            self.assertEqual(result.format,'JPEG');self.assertFalse(result.getexif())
        with self.assertRaises(ValueError):prepare_photo(b'pretend-jpeg')
        with Image.open(io.BytesIO(thumbnail(prepared))) as thumb:
            self.assertEqual(thumb.size,(720,360))

    def test_server_rejects_oversized_files(self):
        from story_studio_core import MAX_PHOTO_BYTES
        with self.assertRaises(ValueError):prepare_photo(b'x'*(MAX_PHOTO_BYTES+1))

    def test_multi_picture_jpeg_prepares_only_primary_image(self):
        first=Image.new('RGB',(2000,1000),'red')
        second=Image.new('RGB',(2000,1000),'blue')
        raw=io.BytesIO();first.save(raw,'MPO',save_all=True,append_images=[second])
        with Image.open(io.BytesIO(raw.getvalue())) as source:
            self.assertEqual(source.format,'MPO');self.assertEqual(source.n_frames,2)
        prepared,w,h=prepare_photo(raw.getvalue())
        self.assertEqual((w,h),(1800,900))
        with Image.open(io.BytesIO(prepared)) as result:
            self.assertEqual(result.format,'JPEG');self.assertEqual(getattr(result,'n_frames',1),1)
            red,green,blue=result.getpixel((0,0));self.assertGreater(red,240);self.assertLess(blue,10)
            self.assertFalse(result.getexif())

    def test_other_recognized_image_formats_remain_rejected(self):
        raw=io.BytesIO();Image.new('RGB',(20,20),'green').save(raw,'GIF')
        with self.assertRaisesRegex(ValueError,'GIF'):
            prepare_photo(raw.getvalue())

if __name__=='__main__':unittest.main()
