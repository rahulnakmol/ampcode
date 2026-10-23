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

## gsap-3.15.0.min.js

- Package: `gsap@3.15.0` from the npm registry (`npm pack gsap@3.15.0`).
- Source file: `package/dist/gsap.min.js` (core only; no ScrollTrigger or other plugins), copied byte for byte.
- npm tarball integrity: `sha512-dMW4CWBTUK1AEEDeZc1g4xpPGIrSf9fJF960qbTZmN/QwZIWY5wgliS6JWl9/25fpTGJrMRtSjGtOmPnfjZB+A==`
  (tarball SHA-256 `d2e33ad202d4811e9084883f7ff9a27967ac4095caef51ca4c9d20697a253b1c`).
- File SHA-256: `92bb9a96476f983d212a2bc4f54c889039c1696dd4461d40a736860938570fbb`
- Project: https://gsap.com, https://github.com/greensock/GSAP
- License: Standard "No Charge" GSAP License, https://gsap.com/standard-license (not OSI). See
  `LICENSE-gsap.md`. The header notice in the file is kept unaltered.
- Network behavior: the bundle makes no requests. Its only URLs are the license header and an SVG
  namespace string.
- Use: optional motion. `article.js` checks for `window.gsap` and works without it.

To upgrade, repeat `npm pack`, copy `dist/gsap.min.js` under a new versioned name, update `GSAP` in
`scripts/publication.py`, and update the hashes above.

## Generated, not vendored

`themes.css` and `THEMES.md` are generated at render time by `scripts/themes.py`, which records each
theme's original source, license, token mapping, and contrast adaptations.
