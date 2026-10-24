# Physical surfaces: print, packaging, and signage

Paper, cardboard, and walls are touchpoints too: the receipt, the onboarding card in the box, the
label on the shelf, the sign that says which way to go. They cannot be patched after release, so
proofing is part of the design. Production values below are common defaults; confirm them with the
printer or fabricator and the applicable regulations.

## Print (`print`)

Covers posters, brochures, flyers, business cards, books, reports, menus, tickets, and receipts.

Craft:

- **Grid and type first.** A baseline grid, a clear hierarchy, and a measure of 45 to 75
  characters for reading text. Body text usually 9 to 12 pt depending on the face and audience;
  large-print editions 16 pt or more.
- **Color for paper.** Design in the printer's CMYK profile (for example a FOGRA or GRACoL
  standard), or in spot colors when brand color must match. Coated and uncoated stock shift color;
  proof on the real stock. Small text in 100% black; large black areas in a rich black the printer
  recommends; stay under the total ink limit.
- **Soft-proof the accent.** When a saturated color carries the design, render a soft proof on the
  target profile (for example uncoated FOGRA52) next to the grayscale check and show the user the
  shift. If the accent is out of gamut (most screen pinks, oranges, and greens are), recommend a
  spot or fluorescent ink (for example a Pantone fluorescent or a riso fluoro) as the default
  specification, not the nearest process mix.
- **Bleed and safety.** Extend backgrounds about 3 mm (0.125 in) past the trim; keep text and key
  content at least 3 to 5 mm inside it. Account for folds, binding, and perforations.
- **Images at 300 ppi at final size** for photos (line art higher), in the correct color space.
- **Files the printer can use.** PDF/X (for example PDF/X-4) with fonts embedded, crop marks and bleed,
  and no RGB or low-resolution surprises. Ask the printer for their specification.
- **Readable by everyone.** Contrast that survives cheap printing and photocopies, no meaning in
  color alone, plain language, and a digital accessible version (tagged PDF) for screen readers.
- **Bridge to digital.** QR codes with a short human-readable URL beside them, a quiet zone, and a
  tested destination that works on a phone.

Mockup and verification: export the print PDF and check its page size (trim plus bleed), fonts,
image resolution, and color with the available preflight tools (Acrobat Preflight, `pdffonts` and
`pdfimages`, or a script). Render a grayscale version, a long-copy version, and a mockup in context
(on a wall, in a hand) at real size. A printed proof is the final check; say when one was not made.

## Packaging (`packaging`)

Craft:

- **Shelf first.** The front panel must work at shelf distance (two to three meters) in under three
  seconds: brand, product, and the one reason to choose it.
- **Every panel has a job.** Front to sell, sides and back to inform; regulatory content (ingredients,
  nutrition, warnings, recycling marks, barcode with its quiet zone) is designed, not squeezed in.
- **Dieline-driven.** Design on the supplier's dieline, with folds, glue flaps, and bleed; check
  what is visible when assembled and when stacked.
- **Unboxing is a journey.** Opening order, what is seen first, instructions where they are needed,
  and easy recycling.
- **Tactile and accessible.** High-contrast key information, braille where required (for example,
  medicines in the EU), and easy-open features.

Mockup and verification: flat artwork on the dieline, a 3D or photographic mockup from each side, a
shelf-distance render among competitors, and a regulatory checklist for the markets in the brief.

## Signage and wayfinding (`signage`)

Craft:

- **Decision points.** Place a sign wherever a person must choose a direction, and nowhere else.
  Walk the route (or its plan) in sequence, in both directions.
- **Legible at distance.** Letter height scales with viewing distance; a common rule of thumb is
  about 25 mm of cap height per 7 to 10 m. Use a clear sans, high contrast, non-glare finishes, and
  tested lighting conditions.
- **Consistent vocabulary.** The same name for a place everywhere (signs, maps, app, website),
  standard pictograms (for example ISO 7001), and arrows with a single, consistent meaning.
- **Accessible.** Mounting heights and tactile characters with braille for permanent room signs
  where codes such as the ADA Standards require them; plain words and pictograms for non-native
  readers.
- **Digital signage** follows the same rules plus motion limits: long dwell times, no fast loops,
  and nothing that distracts drivers.

Mockup and verification: elevation drawings with dimensions and mounting heights, renders at real
size in context and at the intended viewing distance, a low-light render, and the route sequence as
a frame strip of what a person sees at each decision point.

## Physical slop

- Thin light-gray type on textured paper; text placed in the fold or the trim; RGB files sent to
  print; QR codes with no explanation or broken destinations.
- Packaging that hides the product name behind the brand story; regulatory text below legible size.
- Signs that use internal jargon or different names from the map and app.
