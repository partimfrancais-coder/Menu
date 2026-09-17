'use strict';
(function(root){
 function create(restaurant){
  const source=restaurant.source||'';
  const kemang=source.startsWith('Kemang '),kuningan=source.startsWith('Kuningan ');
  const identity=kemang?'KOI Kemang':kuningan?'KOI Kuningan':restaurant.name;
  const reference=source||'the approved reference menu for this restaurant (attach it before generation)';
  const geometry=kemang?'892.92 × 631.44 PDF points':kuningan?'502.32 × 355.20 PDF points':'the dimensions of the approved reference PDF';
  const right=kemang?'Pizza, Lamb, Poke Bowl, Sauce, Side Dishes, Kids':kuningan?'Lamb, Poke Bowl, Sauce, Side Dishes, Kids':'the category stack in this restaurant’s reference';
  return `MENU DESIGN BRIEF — ${identity}

STATUS AND PURPOSE
This is a saved design prompt for future work. Saving or editing it must not generate a menu. Only execute it after an explicit request to generate the menu.
When generation is requested, reproduce the visual design of ${reference} as closely as possible using the current approved menu data for THIS restaurant. Recreate the reference faithfully; do not redesign it or turn it into a modern card-based menu.

SOURCE OF TRUTH
Use the reference PDF for visual structure, typography, colors, artwork, proportions, spacing, and placement. Use the current restaurant data for the menu title, categories, order, visible items, exact dish names, descriptions, prices, variants, add-ons, label assignments, icons, service charge, tax, dietary statement, and footer. The reference is not a source of current prices or item availability. Never restore removed items or copy content from another restaurant. Preserve accents, punctuation and units. Omit hidden items. Flag missing or inconsistent values for review rather than inventing them.

PAGE AND COMPOSITION
Use the reference’s landscape format and approximately 1.414:1 width-to-height ratio. Its native page measures ${geometry}; verify the final physical print size before export instead of assuming A4 or A3. Maintain the same relative geometry if scaled to an approved print size.
Use a plain white background, compact black menu text, narrow bright-red rules, red category headings and small colored food/serving icons. Keep the airy upper header and dense, orderly body. No photographs, decorative backgrounds, shadows, rounded cards, or new decorative graphics. Uploaded dish photos remain assets unless their inclusion is separately requested, since the reference has none.
Center the existing red square KOI logo above the large, black, very bold condensed uppercase menu title. Keep the title’s proportions and placement relative to the logo. Place the small no-pork/no-lard symbol and the approved dietary statement below it. Use current approved wording, not an assumed claim. Reuse the original logo/artwork unless a replacement has been supplied.
At the upper right, arrange the compact icon legend in two columns with icons at a consistent size and vertically aligned explanatory text. Use this restaurant’s current label and serving-detail definitions and assigned artwork. Preserve the original circle/starburst silhouettes, colors, white internal marks, and visual weight. Add new legend entries by extending the same layout; do not substitute emoji when custom artwork exists. Do not infer dietary or allergen claims from dish names.
Separate the header and body with the reference’s pair of thin, closely spaced red horizontal rules running almost the full usable width.

BODY GRID AND THIS RESTAURANT’S BASELINE
Recreate four vertical menu columns with narrow, consistent gutters and aligned top edges. The reference’s category flow is:
• Left column: Soups, Appetizers, Salads, Sandwiches, Burger.
• Second column: Pastas, Noodles & Rice, Poultry.
• Third column: Seafood, Beef, Grill.
• Right column: ${right}.
${kuningan?'This Kuningan reference has no regular Pizza section in the right column; Pizza appears inside Monthly Specials. Do not import Kemang’s regular Pizza section unless it is present in Kuningan’s current menu data.':kemang?'Keep Kemang’s regular Pizza section at the top of the right column when that category remains in the current data. It is distinct from the Pizza subsection inside Monthly Specials.':'Use this restaurant’s approved reference to confirm these baseline groupings before generating.'}
Treat this flow as the reference layout, not a fixed item count. Respect deliberate ordering changes in the current menu. Add new categories in their configured order using the same heading style. Remove empty categories without leaving ghost headings or fixed empty slots.

TYPOGRAPHY AND DISH ROWS
Match the reference’s tall, narrow uppercase category lettering with red outlines and white interiors. Center each category heading above a thin red rule spanning its column. The main title is solid black, bold and condensed; it must not look like the outlined category headings.
Use the original fonts or approved metrically close replacements, measuring them against the PDF. Embedded font resources include Calibri, Tw Cen MT Std Bold, Myriad Pro Regular and Arial MT; verify their actual roles rather than assuming that list identifies the outlined heading font. Some headings/artwork may be vector outlines. Reuse those outlines where suitable; do not claim exact typeface matching without checking the source.
Set dish names in compact, readable black sans-serif. Keep descriptions and qualifiers smaller and lighter in visual emphasis, matching the reference’s inline or indented continuation treatment. Preserve the reference’s modest weight differences; avoid making every name heavy bold.
Reserve a stable, right-aligned price column for every section. Prices must line up vertically and never collide with names or descriptions. Use the restaurant’s stored currency and price multiplier; e.g. IDR × 1,000 displays 95 as 95 rather than 95,000. Do not append a currency symbol to every row if it is explained in the footer. Never change or round a price to make it fit.
Place assigned icons close to the associated dish, aligned with the text baseline; preserve leading/trailing placement where meaningful. Keep icons clear and consistently scaled, with enough separation from text and prices. Keep variants and additional charges visually attached to their parent item. Distinguish a variant’s replacement price from an add-on charge; indent supporting rows. Reproduce thin black internal separators where the reference groups subsections, without drawing a box around every item.

MONTHLY SPECIALS
Keep a prominent thin red rectangular panel near the lower center, spanning the second and third columns. Use its outlined red uppercase MONTHLY SPECIALS heading centered above a red dividing line. Inside, use the reference’s two-column arrangement with smaller solid-red bold uppercase subgroup headings: Salad, Pasta and Main on the left; Pizza, Dessert and Wine of the Month on the right, when present in current data.
Keep specials separate from the regular category stacks. Adapt the panel’s height to its actual contents. Align special prices and preserve wine bottle/glass sizes and prices. Show a crossed-out previous price only when explicitly recorded as an approved previous price; never copy an obsolete promotion from the PDF. If there are no specials, remove the panel and rebalance the space. Add or remove subgroups using the same visual hierarchy.

FOOTER
Place the restaurant’s current pricing/service/tax note in small, readable black text near the bottom center. Reconcile it with the saved price multiplier and percentages before export; flag discrepancies rather than silently calculating or rewriting terms. Keep any restaurant/version identifier small at the lower left. Do not copy the old reference filename or date as the new menu version. Keep footer text inside the printable area, clear of the specials panel and body.

FLEXIBLE CONTENT RULES
For an unchanged menu, aim for a visually faithful reproduction of the reference. When content changes, preserve the same design language and hierarchy rather than every old line break.
For fewer dishes: keep type and icon sizes stable; close unnecessary gaps and balance section spacing without stretching lines or inflating text to fill the page.
For extra dishes or longer names/descriptions: first reflow text within its text area while protecting the price column; then adjust section gaps and available column heights modestly. Keep category headings with at least their first item, and keep a dish with its description, variants and add-ons. Rebalance whole sections only when necessary, keeping a clear reading order and the specials panel’s central role.
For longer prices: reserve enough price-column width for the widest current value, then reflow adjacent text. Do not overlap text, abbreviate approved item names, truncate descriptions, drop items, shrink icons to illegibility, or silently reduce the print scale.
Aim for one page while preserving the reference’s readable density. If the approved content cannot fit legibly, prepare additional pages in the same visual system and flag the page-count change for review. Continue categories with a clear continuation heading, repeat necessary header/legend context and footer, and keep item groups intact. Exact one-page geometry and unlimited extra content cannot both be guaranteed: content completeness and readability take priority over forcing overflow onto one page.

FUTURE GENERATION CHECKS
Before releasing a generated menu, compare the rendered result side by side with this restaurant’s reference at the same scale: logo/title placement, header rules, column alignment, heading shapes, red color, legend symbols, text hierarchy, price alignment, specials panel and footer. Check every visible item and price against current data, verify icon assignments, and inspect all pages for clipping, overlaps, broken accents, orphan headings and missing content. Flag uncertain source spelling or missing fonts/assets for review. Keep text selectable and vector artwork crisp where feasible; embed fonts and preserve print-quality assets.
Do not generate a menu now. This document is the editable placeholder for the later generation stage.`;
 }
 const api={create};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MenuDesignPrompts=api;
})(globalThis);
