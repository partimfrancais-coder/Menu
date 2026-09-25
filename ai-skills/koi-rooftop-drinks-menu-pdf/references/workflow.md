# Rooftop drinks workflow

## Source and identity

The retained source `assets/rooftop-drinks-original.pdf` is an unchanged copy of **KOI ROOFTOP Menu - Drinks & Cocktails November.pdf**. Its two pages belong to the separate **KOI Rooftop Drinks and Cocktail** restaurant, ID `e5ca8e2c-519c-40d8-86be-1727820c3d47`. Do not use the Lunch & Dinner Rooftop source or select a restaurant by a loose Rooftop-name match.

For local generation, obtain an authenticated GET of `/api/menus` from the configured Menu Studio instance using the existing authorized access mechanism, or use a current user-supplied export. Keep credentials out of the skill, renderer and delivered source. Retain fetch timestamp and revision beside the working snapshot. If fresh data is unavailable, disclose the available snapshot's age rather than presenting it as current.

`scripts/prepare_snapshot.py` accepts a full backup with `restaurants`, `products`, `productCategories`, and `productTags`. It selects the exact restaurant, resolves shared fields and preserves placement IDs, order and visibility. Hosted bundles instead provide resolved `restaurant.json`, `request.json` with revision/mode/request, and `conversation.json`. Read those directly.

Use current shared prices even where the reference differs. The original import expanded grouped flavours and drinks into separate shared records, so old row counts are not generation targets. Saved descriptions, options and tags can be shared across branches and need not match every historical PDF. Do not silently remove them to achieve a closer visual copy.

## Visual system

Both pages are A4 portrait: **595.276 x 841.890 points**. The source uses charcoal near `#272E2E`, orange `#D45004` for headings, and gold `#CFA567` for item copy, prices, logo and borders. Inspect both retained page images before starting. Use the source's warm gold-on-charcoal contrast; do not switch to the red-and-white style of Kuningan/Mahakam.

Page one:

- Center the geometric cocktail-glass Rooftop logo at the top. Reuse a clean, tightly isolated crop from the vector reference; exclude food text and borders outside the logo region.
- Below the logo, draw a gold-bordered Finger Food panel spanning the content width. Its orange condensed uppercase title is separated from the two-column gold item list by a thin gold horizontal rule.
- Below the panel, use two drink columns. The historical left column has Soft, Water, Tea and Coffee; the right has Local Beer, Imported Beers and Bali Craft Beers. This is layout evidence, not permission to override saved ordering.
- Imported-beer country subheads are gold bold italic. Render them only from supported current content, preserving product order and category membership.

Page two:

- Begin with a wide gold-bordered Cocktails panel, orange condensed uppercase title and a horizontal separator. Place cocktails in two columns, with prices right-aligned and ingredient descriptions in smaller italic gold text under each name.
- Below it, the historical left column has Korean Soju, Gin, Rum and Vodka; the right has Whisky, Tequila and Wine by Glass. Reflow these based on current saved categories and order rather than recreating an old item list.
- Keep spirit option prices visibly associated with their own product. Allow long brand names to wrap without colliding with paired prices.

Use a content area around x=38..557 with a generous center gutter. Category headings have a broad serif/copperplate character; panel titles have a tall condensed sans-serif style. Body text is a readable humanist sans-serif, with italic supporting text. Inspect the PDF's fonts and reuse matching available fonts; use reasonable substitutes where needed and disclose them. Do not require hard-coded Windows font paths.

Keep the gold footer centered near the bottom, outside product/panel bounds. Use current footer/currency/unit/service/tax data; the source's 10% service and 10% tax sentence is historical evidence, not a value to restore automatically.

## Reflow and data safeguards

Build fresh pages, copying only isolated artwork. Do not place new text over complete source pages or rely on white/charcoal masks to hide old dishes; historical text must not remain extractable.

Preserve current restaurant category and item order. The source's food/cocktail panels are category treatments, not a reason to reorder the saved menu. If current order differs from the historical positions, retain the treatments at the appropriate place in the flow. Measure each panel from its actual contents, use consistent category gaps, and let columns finish at different heights. Do not stretch gaps to fill a page or reduce body text excessively. Add matching continuation pages if needed, repeating compact branding and current footer.

Include all and only available placements. Use a coverage manifest with placement ID, product ID, category, name, page and row bounding box. Expanded flavours are distinct records; group them only when requested and when a lossless mapping preserves every product and its differing descriptions/options/prices.

Options with `kind: Variant` are full alternative prices; `Add-on` prices are additional. The source shows paired spirit prices without explicit serving labels. If current saved options say First listed price / Second listed price, retain that uncertainty rather than guessing bottle/shot definitions. Names such as H, Kranken or Gentelman Jack may need content review; do not silently change the shared names.

Use current `tagCatalog` definitions and `assets/menu-icons.js` for assigned icons. Hosted bundles replace the icon library with the current app version. Do not infer dietary claims or add no-pork/no-lard wording from other branches. The source has no promotional Happy Hour or Monthly Specials panel; include such content only when present in the current saved target or explicitly requested.

The current `priceUnit` governs price formatting. For IDR with unit 1000, a stored value of 120 prints as 120 under the matching footer; do not multiply twice. Preserve option values without inventing new serving sizes. Private notes, codes, internal IDs and review status must not appear in the customer menu.

## QA and revisions

Compare the output manifest's placement multiset with the available snapshot placements and check actual extracted PDF text in each row region. Require every name, own-row price, description and option to be present once per placement. A manifest by itself is not proof of rendered content.

Render every output page using Poppler when available, otherwise PyMuPDF. Inspect the logo crop, panel titles, gold rules, wrapped ingredient descriptions, wine/soju options, narrow spirit-price gutters, longest brand names and footer. Check contrast and readable type at actual A4 print size. Record page sizes/count, provenance, font substitutions and unresolved names or serving labels. Do not claim checks passed without running them.

A new generation uses current saved data and this reference only. An adjustment uses the latest generated PDF/source plus requested design changes. Neither changes live product records. No fixed renderer is currently included; derive and verify it when generation is requested.
