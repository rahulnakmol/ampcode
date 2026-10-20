# Plan: distilling-videos publication UX extension

Spec: `docs/superpowers/specs/2026-10-20-distilling-videos-publication-ux-design.md`.
Branch: `feat/distilling-videos` (isolated worktree). Commit locally; do not push.

## Tasks

1. **Theme sources.** Collect official palettes (repositories, npm packages, or archived official
   documentation) for the 20 families; record source URL, license, and token mapping in
   `skills/distilling-videos/scripts/themes.py`. Generate `themes.css` and `THEMES.md`; compute
   WCAG contrast and record adaptations.
2. **Vendored motion.** Add `assets/vendor/gsap-3.15.0.min.js` byte for byte from `npm pack
   gsap@3.15.0`, `LICENSE-gsap.md`, and provenance (tarball integrity, file SHA-256, network
   behavior).
3. **Renderer.** In `scripts/publication.py`: glossary validation; shared page shell (nav, toolbar,
   Markdown disclosure, search dialog, evidence panel); cover, article, brief, transcripts index,
   per-video transcript pages, gallery, glossary, references; Markdown twins; evidence templates;
   search index; link and Markdown-twin integrity checks; copy selected and cited frames; PDF of
   `article.html`; `pdf.json` `page`/`page_sha256`; `RENDERER = 2`.
4. **Behavior and style.** `assets/article.js` (Alpine components: shell, copy page, evidence panel,
   filters, gallery viewer, search; GSAP motion with safe fallbacks), `assets/theme-init.js`
   (guarded early theme), `assets/article.css` (tokens, layout, nav, panels, viewer, print).
5. **Tests.** Extend `tests/test_distilling_publication.py`: page set and nav, Markdown twins,
   transcript completeness, glossary contract, link integrity failure, search index offline,
   theme contrast and labeling, vendored provenance, PDF target and stale record.
6. **Docs.** Update `reference/article-contract.md`, `SKILL.md` inspection step, `README.md`
   publication guidance, eval README and evaluation doc.
7. **Evaluation.** Update `run_eval.py` and `capture.mjs` for the index/article split and the new
   interactions; run the harness with Chrome Canary and `--capture`; inspect screenshots with
   view_media; record results.
8. **Verification and commit.** `make check`, eval harness, `git diff --check`; commit locally.

## Stop conditions

Stop and report rather than widen scope if an unrelated module needs changes, a contract outside the
publication layer would break, or a theme source cannot be verified (omit it and say so).
