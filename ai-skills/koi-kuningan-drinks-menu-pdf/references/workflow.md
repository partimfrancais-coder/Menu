# Kuningan drinks workflow

## Source and snapshot

The retained design source is `assets/kuningan-drinks-original.pdf`, copied unchanged from **Kuningan Fingerood Drinks Menu 20260720.pdf**. Its tiny historical footer names Kemang; do not use that footer to identify this restaurant or reproduce the obsolete file/version label. The separate target is KOI Kuningan Drinks and Cocktail, ID `b8ae17c2-f1e0-4169-8a95-40f4b9b39cc9`.

For a local task, use an authenticated GET of `/api/menus` from the user's configured Menu Studio instance, or a current user-provided full backup. Use the existing authorized access mechanism, never embed login details in scripts or outputs. If fresh access is unavailable, explain which snapshot is available and its age instead of representing a historical export as current. Retain fetch timestamp and revision beside the working snapshot, not as permanent content inside this skill.

Run `scripts/prepare_snapshot.py` only for a full backup containing `restaurants`, `products`, `productCategories`, and `productTags`. It selects the exact restaurant and resolves shared fields while preserving placement IDs, order and visibility. Hosted generation provides a resolved restaurant-only file and `request.json` containing saved revision, generation mode and request. Read those directly.

The initial import expanded grouped drink choices into individual shared products. Counts and prices from that import are not targets. Existing shared prices deliberately take precedence over source-PDF prices. For example, source finger-food prices can differ from the catalog; never use the reference to undo this choice. Shared descriptions and options can also differ across source PDFs. Flag unresolved content without changing it.

## Visual specification

Inspect the bundled reference image before layout. Measurements below are starting geometry in PDF points, measured from the upper-left of the **1190.64 x 841.92** page; adapt vertical positions to actual content.

| Region | Reference arrangement |
| --- | --- |
| Logo | Centered near the top, approximately x=564..637, y=4..77; isolate a clean crop from the original vector PDF. |
| Finger Food title | Centered black uppercase title below the logo, above the panel border. |
| Finger Food panel | Thin red rectangle, approximately x=94..1116, y=113..240; three item columns, prices aligned at each column's right edge. |
| Dietary note | Small no-pork/no-lard mark near the panel's upper-right; use only when current dietary text supports it. |
| Drinks title | Large centered black uppercase title beneath the food panel. The source's complete-drinks-menu sentence is optional presentation copy, not a product; do not invent it as current data. |
| Drink columns | Four columns starting around x=96, 343, 608 and 858; heading baseline near y=323. Keep generous gutters and independent vertical flow. |
| Category headings | Bold red uppercase, left-aligned; source headings are approximately 20pt, with some optical variation. |
| Body copy | Dark charcoal Calibri-like regular, around 12pt in the source; supporting descriptions smaller and sometimes italic. Maintain readable print size when reflowing. |
| Beer origin subheads | Black uppercase Belgium/Ireland/Germany with a short black underline. Derive these only from current descriptions if used; preserve saved product order and category membership. |
| Happy Hour | Red-bordered panel beneath the central drink content; centered red heading, timing/bucket note, product names and current prices. |
| Cocktails promotion | Separate red-bordered panel below the right-side content; centered offer heading, current timing note, and two internal item columns. |
| Footer | Centered dark text at the bottom with current currency/unit/service/tax wording, kept clear of all panels. |

Reference palette: red roughly `#AD0000`, charcoal roughly `#231916`, plus black and white. The source uses Calibri, Arial Bold, Trebuchet Bold and Copperplate Gothic Bold. Prefer matching available fonts; Carlito is a reasonable Calibri substitute on Linux. Do not depend on a hard-coded Windows font path. Tightly cropped original vector headings can preserve the source appearance when the current heading text matches; regenerate changed headings with a suitable font.

Do not place a complete source page beneath new text, even under white rectangles: historical content must not remain extractable. Build a fresh page and copy only isolated artwork regions. Verify logo crops include no menu text.

## Flow and content rules

The upper food panel and lower promotional boxes must expand for current content. Preserve the saved restaurant category sequence and item sequence; the reference's four-column grouping is a visual guide, not permission to move products to different shared categories. Use columns in reading order with a consistent category gap. A long category can continue with a repeated heading when needed. The audit must account for each placement exactly once even if continuation headings repeat.

Place each promotion panel after the content in the columns it spans, below the lowest occupied column edge plus the standard category gap. Do not pin panels to fixed y-coordinates and allow overlaps. If all current entries cannot remain legible on one page, create matching landscape continuation pages and repeat a compact branded header and current footer. Explain the changed page count.

Prices use `priceUnit` without double multiplication. A saved price of 95 with unit 1000 prints as 95 under the matching footer. Format variant and add-on prices distinctly: a variant price is a full alternative price, while an add-on price is additional. Never display a bucket price as an individual bottle price. Multiple current wine sizes and coffee add-ons must remain explicit. Group rows only if the user requests it and a lossless mapping proves that every product ID and all distinct details remain represented.

Use current `tagCatalog` definitions and the bundled `assets/menu-icons.js` when necessary; hosted bundles replace that file with the current icon library. Source NEW flashes, alcohol percentages, serving sizes and no-pork/no-lard claims must not be inferred for a product from its name. Use saved descriptions/tags/dietary fields. Private `notes`, product codes, review flags and internal IDs belong in the audit, not the customer-facing PDF.

The source contains Friday/Saturday buy-one-get-one terms and a daily 4–8 PM bucket offer. Include the current saved category notes, which may change; no automatic Thursday Aperitivo or other branch's offers. Use current footer text and validate that numeric service/tax fields agree. Flag a contradiction instead of silently selecting a value.

## QA and revision

Before export, create a coverage manifest with placement ID, product ID, category, name, page and bounding box for each visible row. Check row text/price/options against the current resolved snapshot, including long wrapped descriptions. Compare the manifest's placement multiset with the available-item multiset: no missing or duplicate rows. Check actual extracted PDF text in the row regions as well; a manifest alone does not prove the PDF contains the content.

Render all pages with Poppler when available, otherwise PyMuPDF. Inspect logo, food panel, column gutters, longest item names, coffee options, tea notes, imported-beer percentages, both promotion panels and footer. Record physical dimensions, font substitutions and unresolved content. Successful PDF creation alone is not a passed visual check.

A fresh generation starts from current saved data and this reference. An adjustment starts from the latest generated PDF/source and the user's requested changes. Do not merge old proofs into fresh content or change live product records. No fixed PDF renderer is currently included: generate and verify a renderer when a PDF is actually requested.
