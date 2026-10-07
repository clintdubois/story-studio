"""Package source for review. No Git publication, deployment or credentials."""
from pathlib import Path
import hashlib, json, zipfile
ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local'
UPSTREAM=LOCAL/'ckeditor5-v48.5.2-source.tar.gz'
EXPECTED='131b0a502f56580800bf1185449d64e45cea2ebc338c541a916860f9614901d6'
if not UPSTREAM.exists() or hashlib.sha256(UPSTREAM.read_bytes()).hexdigest()!=EXPECTED:
    raise SystemExit('Retrieve the exact upstream archive documented in docs/SOURCE.md and verify its SHA-256 first.')
files=['.gitignore','README.md','AGENTS.md','CLAUDE.md','context.md','LICENSE','NOTICE.md','local.settings.example.json','staticwebapp.config.json','index.html','source.html','403.html','404.html']
for folder in ('admin','api','tools','tests','docs','licenses','.github'):
    files.extend(str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in {'.py','.json','.html','.md','.yml','.cjs'} and '__pycache__' not in p.parts and p.name!='story_studio_core.py')
files.append('tools/story_studio_core.py')
output=LOCAL/'Story-Studio-Source-Review.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
    for rel in sorted(set(files)):z.write(ROOT/rel,'story-studio/'+rel)
    z.write(UPSTREAM,'upstream/'+UPSTREAM.name)
    z.write(LOCAL/'SOURCE-MANIFEST.json','upstream/SOURCE-MANIFEST.json')
with zipfile.ZipFile(output) as z:
    if z.testzip():raise SystemExit('Archive verification failed.')
print('Verified source review archive:',output)
