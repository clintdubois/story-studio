"""Build only the standalone authoring frontend; never deploy or publish."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'
SITE.mkdir(exist_ok=True)
for name in ('index.html','403.html','404.html','source.html','staticwebapp.config.json'):
    shutil.copy2(ROOT/name,SITE/name)
(SITE/'admin/story-studio').mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/'admin/story-studio/index.html',SITE/'admin/story-studio/index.html')
shutil.copy2(ROOT/'tools/story_studio_core.py',ROOT/'api/story_studio_core.py')
print('Built standalone site and packaged API validator. No deployment performed.')
