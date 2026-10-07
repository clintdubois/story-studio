const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('admin/story-studio/index.html', 'utf8');
const start = html.indexOf('const PHOTO_TYPES');
const end = html.indexOf('function webPhoto(', start);
assert(start >= 0 && end > start, 'photo type check not found');
const context = {};
vm.createContext(context);
vm.runInContext(html.slice(start, end) + '\nthis.isPhotoFile = isPhotoFile;', context);
const ok = (name, type) => assert.equal(context.isPhotoFile({ name, type }), true, `${name} (${type}) should be accepted`);
const no = (name, type) => assert.equal(context.isPhotoFile({ name, type }), false, `${name} (${type}) should be refused`);
ok('a.jpg', 'image/jpeg'); ok('a.png', 'image/png'); ok('a.webp', 'image/webp');
ok('a.heic', 'image/heic'); ok('a.heif', 'image/heif');
ok('IMG_0001.HEIC', ''); ok('IMG_0002.heif', '');          // Windows often reports no type for HEIC
no('a.gif', 'image/gif'); no('a.pdf', 'application/pdf'); no('a.txt', ''); no('heic', '');
assert.match(html, /accept="image\/jpeg,image\/png,image\/webp,image\/heic,image\/heif,\.heic,\.heif"/);
assert.match(html, /upload:\{types:\['jpeg','png','webp','heic','heif'\]\}/);
console.log('Photo type checks passed: JPG, PNG, WebP, HEIC and HEIF accepted (including a missing type with a .heic name); GIF, PDF and unnamed files refused.');
