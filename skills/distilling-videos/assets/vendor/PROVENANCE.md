# Vendored files

## alpine-3.17.4.min.js

- Package: `alpinejs@3.17.4` from the npm registry (`npm pack alpinejs@3.17.4`).
- Source file: `package/dist/cdn.min.js`, copied byte for byte.
- npm tarball integrity: `sha512-N2gsr+58XVUt7OAPKnUGiKPDtkd+xbSGTae8C8IJxeRdkkhBJPIautkJ+qcwb7lcjJ/QK3/CPVIbN20JPvtK7A==`
- File SHA-256: `232519394c6c8fdba6f362b1d9da16106db513cdbf899011f00daab4051df31c`
- Project: https://alpinejs.dev, https://github.com/alpinejs/alpine
- License: MIT. See `LICENSE-alpinejs.md`, copied from `LICENSE.md` at tag `v3.17.4`
  (SHA-256 `08b7502da6e7aa1d0bbdc97d220fbf669b9366c61bd0f072238283c89bc4773a`).
  The bundle also embeds `@vue/reactivity` 3.5.x, which is MIT licensed; its notice is kept in the file.
- Network behavior: the bundle makes no requests. Its only URLs appear in warning text about missing plugins.

To upgrade, repeat `npm pack`, copy `dist/cdn.min.js` under a new versioned name, update `ALPINE` in
`scripts/publication.py`, and update the hashes above.
