# Project and data

Original workspace: `C:/Users/Owner/Documents/ChatGPT/Restaurant menu project`.
Menu Studio: `https://web-production-88016.up.railway.app/`.
These are discovery hints; verify availability and current configuration.

The existing Flask application uses a session login: POST `/login` with form fields `username` and `password`, then authenticated GET `/api/menus`. The response contains `restaurants` and a revision. Read `hosted.py` to verify the contract before access. Existing credentials may be in `.deployment/credentials.json`; never print, bundle, or pass them on a command line. Use a requests session with TLS verification; `truststore.inject_into_ssl()` can use Windows certificate trust if needed. Stop after a failed login rather than repeated retries. Fetching a menu does not require any POST to `/api/menus`.

Select the intended restaurant by verified id/name, then save only its object as an input snapshot in task scratch space. Preserve the response revision/fetch time separately for provenance. A user-provided current export can also be used. If current data is unavailable, ask for access/export; do not pass an old snapshot off as fresh.

Restaurant fields used: `name`, `menuTitle`, `designPrompt`, `dietaryNote`, `footer`, `categories`, and `tagCatalog`. Categories have name/id/items. Items have id/name/description/price/available/tags/options/notes/reviewed. Options have name/price/kind; `Add-on` prices use a plus sign, alternatives show their own price. Catalog entries have name/kind/icon/iconImage. PNG data URIs are in `iconImage` or the icon-key map in `dist/menu-icons.js`.

Never invent prices or dishes. Preserve ordering, names, accents, descriptions, variants, add-ons, availability, and icon associations from current data. Prices use IDR x 1,000: 95 prints as 95, not 95,000. Notes are review context, not automatically menu copy. Do not restore historical struck-through wine prices without current approval. Adjacent dishes may share an identical add-on row only when its applicability remains clear.

# Kuningan design

The bundled source is `assets/kuningan-original.pdf`; the original is 502.32 x 355.20 points, landscape. Source render is `assets/kuningan-original.png`; the approved corrected proof is `assets/kuningan-proof.png`. The proof demonstrates the rendering workflow, not current menu content or a requirement to preserve old item counts.

- White background, centered original red square KOI logo, black condensed LUNCH & DINNER title, no-pork symbol/statement below.
- Two-column legend upper right using original colored menu icons; thin red double rule under the header.
- Four columns: Soups/Appetizers/Salads/Sandwiches/Burger; Pastas/Noodles & Rice/Poultry; Seafood/Beef/Grill; Lamb/Poke Bowl/Sauce/Side Dishes/Kids.
- Outlined red uppercase narrow category headings, red rules, compact black sans-serif dish names, smaller descriptions, aligned prices.
- Central red bordered Monthly Specials panel across columns two and three: Salad/Pasta/Main left; Pizza/Dessert/Wine of the Month right. No separate regular Pizza column in this Kuningan reference.
- Footer from saved restaurant data; version/date updated for the generated proof.

Original headings and title are vector outlines. `show_pdf_page` with carefully inspected clip rectangles preserves them better than approximating fonts. First remove source text from a working in-memory copy with PyMuPDF redaction while preserving images and vector graphics; this avoids hidden stale prices entering the new PDF. Never modify the source asset. Crop only artwork, not old menu rows. Wide-enough crops are essential: the first attempt clipped DINNER, SALADS, BEEF, POULTRY, POKE BOWL, and SIDE DISHES. Recheck if changing crops, dimensions, or source.

The helper balances whole categories in saved order across four columns, reserving lower-center space for specials. Its current one-page capacity is explicit; overflow requires adapting a working copy. The helper lays out at 3x native coordinates then scales the vector page back to source dimensions. It embeds Windows Calibri for new text. Icons contain transparent padding. Keep at most one leading icon in tight gutters; put additional icons after text to prevent colliding with the preceding column's prices. Respect configured no-icon choices and replace custom artwork when current data requests it.

For changed quantities, rebalance column gaps, wrap descriptions, move whole sections sensibly, or add a continuation page in the same style. Do not silently omit added categories, shrink type to unreadability, overlap the specials box, or insist on the initial 103-item count. Existing helper categories and single-page capacity are explicit constraints to adapt, not content constraints for the user.

# QA details

Extract the output text once with `get_textpage()` and reuse it for names, descriptions, options, and coordinate-based price checks. Repeated extraction for every row was unnecessarily slow. Calibri extraction may use nonbreaking spaces and U+2010 for a hyphen; normalize whitespace, Unicode NFKC, and that hyphen for comparison without changing the underlying menu wording.

Audit ids/counts against all and only available items. Check price values on their expected rows, options and add-on applicability, all icon mappings, and the saved footer. The bundled checker checks option text/value presence, so visually verify the association of each option price. Inspect all rendered pages, especially the central dense columns, artwork clipping, leading-icon gutters, specials wine row, and footer. Native size is small: preserve it for a faithful proof but offer a larger print format if requested.

Kemang source is retained as `assets/kemang-original.pdf`. It uses a different page size (892.92 x 631.44 points) and content arrangement. Inspect it and read Kemang's own saved prompt before deriving a renderer. The bundled Kuningan script has not been validated for Kemang.


# Approved refinements from the updated menu review

- Small Bites and Asian must use the same outlined letterforms as the source headings. Arial Narrow with a red stroke was visibly different and rejected. The updated renderer composes new words from actual vector glyph paths extracted from LAMB, PASTAS, and SANDWICHES. Preserve compound paths, holes/even-odd fill, line/Bezier/rectangle commands, and original red fill. Normalize glyph height to 26 working units and use 1.6 units tracking. Other future headings may need additional source glyphs; never silently substitute a mismatched font.
- Original category artwork is clipped at verified bounds. Continue to inspect complete glyph edges and original letter proportions.
- Leading icons now use x - 23 instead of x - 19 in the 3x coordinate system, giving a small clear gap before the dish name. Keep trailing icons and legend placement unchanged. Check gutters against the preceding column's prices after any reflow.
- Remove the two black horizontal separators previously inserted before Crispy Kalan and Vietnamese Steak. Preserve red category rules, header double rules, and the red Monthly Specials border. Do not restore these black lines just because the source has them.
- Reflow whole regular categories in saved sequence, top-to-bottom then left-to-right. The approved revision places Small Bites, Soups, Appetizers, Salads, Asian, Sandwiches, Burger in column one; Pastas, Noodles & Rice, Poultry in two; Seafood, Beef, Grill in three; remaining categories in four. This is an example from revision 6, not a permanent ordering override.
- Cache measured category heights before evaluating column splits. Balance spacing per inter-category gap, rather than raw unused column height; the latter produced an excessive gap and moved Grill unnecessarily.
- The updated reference uses a taller lower-center specials panel at working y=760, height=268. Omit headings for empty subgroups, including the former Pizza special after Chicken Lahmacun moved to Small Bites. Future panel size must follow contents; the helper remains a one-page renderer and does not automatically paginate arbitrary growth.
- Layout approval does not confirm the 14 provisional prices or the unresolved ravioli spelling. Read current notes and report unresolved values accurately. Do not invent dietary icons for the new dishes.
