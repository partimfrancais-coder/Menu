# Rooftop workflow

## Source and current data

The user's reference is `Rooftop Menus Lunch & Dinner 20260605A.pdf`, bundled as `assets/rooftop-original.pdf`. Both reference page PNGs are included for quick visual orientation. They contain historical content and prices.

Menu Studio discovery hint: `https://web-production-88016.up.railway.app/`. The project is `C:/Users/Owner/Documents/ChatGPT/Restaurant menu project`. Verify these when needed; the skill also works from supplied current snapshots and does not require this workstation.

The authenticated hosted app currently serves GET `/api/menus` with `revision`, `restaurants`, `products`, `productCategories` and `productTags`. Existing authorized credentials may be available in the project's private `.deployment/credentials.json`. Use them only through a requests session with verified TLS, never print or bundle them. Do not change passwords, permissions or menus to obtain a snapshot. If current data cannot be obtained, request an export instead of pretending the PDF's content is current.

Copy only Rooftop's restaurant object into the generation input. Resolve each placement's `productId` from the current catalog; retain its placement `id`, order and `available` value. Shared `price`, `name`, `description`, `options`, `tags`, `cuisine` and category assignment take precedence over old materialized values. The helper rejects category drift rather than silently regrouping a menu.

Keep snapshot revision and retrieval time alongside the output. Never package accounts, other restaurants' snapshots or credentials with the skill or generation inputs. A restaurant-only current export may be used directly when its freshness and shared-price provenance are known; the helper requires a full catalog snapshot for independent resolution.

## Distinct Rooftop design

- Two A4 portrait pages, two columns each. Dark charcoal background, warm gold dish text/prices and orange category headings. Read actual color values from the PDF when implementing; the PNG is a visual guide, not a color calibration source.
- Page one header: Rooftop's own gold cocktail-glass/cutlery logo; condensed orange LUNCH & DINNER title; white no-pork/no-lard symbol and text. Compact icon legend at the upper right. Page two has the title, dietary line and legend without repeating the page-one logo.
- Source font inventory: CopperplateCC (category headings), BigNoodleTitling (main/specials title), Calibri regular/italic/bold-italic, and Arial Bold. Reuse vector artwork for stable branded elements. Embedded subset fonts may lack glyphs needed for new headings. Use legally available complete fonts for new text; disclose any substitute and verify its metrics and appearance. Do not assume Calibri exists in a Linux sandbox.
- Gold right-aligned price column; dish names in regular type, smaller italic descriptions. Inline descriptions may follow a name only when price clearance remains generous. Options belong visibly to their parent dish, with their own price aligned to the price column.
- Preserve native dimensions and adequate margins. Keep a consistent gap between categories and top-align columns. Do not stretch short columns merely to align bottoms. Reflow whole categories in current saved order; source category placements are a design example, not authority to reorder today's menu.
- The reference page-one left column contains Soups, Appetizers, Salads, Pizza, Sandwiches and Poultry; its right contains Pasta Favorites, Noodles & Rice and Seafood. Page-two left contains Beef, Burger, Lamb and Poke Bowl; right contains Grill, Sauce, Side Dishes and Kids. Use the saved shared category names (e.g. Pastas) unless the user asks for a presentation-only alias.
- Monthly Specials on page two sits in a gold-outline box with an orange centered title and two internal columns. Source subgroups are Salad, Pasta, Main, Pizza, Dessert and Wine of the Month. Build it from current category membership; omit absent/empty subgroups. Do not pull Chicken Lahmacun out of Finger Food or Rawon out of Beef merely because they appeared as specials in the old PDF.
- Let the specials panel follow the content above with consistent clearance and padding, leaving space for the footer. Reflow or add a continuation page if it cannot fit; do not shrink text indiscriminately or overlap the footer.
- Horizontal orange section dividers separate clearly contiguous cuisine groups. Use saved `cuisine` values and current item order; do not guess a cuisine or reorder mixed groups to force a divider.

## Icons and pricing

Use current `productTags`/`tagCatalog` definitions and each item's assigned tags. The bundled `assets/menu-icons.js` is a fallback icon library; use a fresher library when available. `iconImage` overrides a preset icon. Preserve explicitly empty icon choices. Source header icons show side accompaniments, rice choices and time notes; they do not authorize assigning tags missing from current product records.

The reference's timer legend says more than 20 minutes; some current shared tags say more than 15 minutes. Use the **current actual tag label and artwork**, and flag mismatches rather than changing shared products or displaying a conflicting time icon. Likewise, do not infer vegetarian/spicy labels from a dish name. Current shared icon assignments control, even if a historical PDF differs.

Prices print in the saved currency/unit convention (currently IDR × 1,000: 95 prints as 95). Use current `serviceCharge`, `tax`, `footer` and `dietaryNote`; if a required field is empty, disclose any source-derived footer/dietary wording as a PDF-only presentation choice. Do not silently write it to the app. The source says 10% service and 10% tax; verify current values before using that sentence.

The old wine panel strikes out 690 and shows 590. Never recreate that discount from the historical reference. Use the current product's price and current glass-size options. The initial Rooftop import deliberately reused shared products and shared prices, so source/current price differences are expected.

## Proof checks and delivery

Extract output text and compare it to the current visible-item set. Check every name, description, own-row price, option name/price and footer; normalize Unicode ligatures and spacing for checks without rewriting copy. Check dietary/serving icon association visually. Do not assume a successful render means the content is complete.

Render all pages with Poppler when available, otherwise PyMuPDF. Inspect the header, inner column gutter, longest descriptions, option rows, bottom categories, specials and footer. Watch gold-on-charcoal contrast, type size at A4, cropped vector glyphs and price alignment. Inspect source crops for historical text that must not survive into the new PDF.

Keep the latest PDF, editable renderer and a short audit recording snapshot revision, included item IDs, page count/dimensions and issues. Deliver a reviewable PDF with any font substitutions or unresolved content noted. A PDF adjustment request changes the artifact only unless the user separately asks to update saved menu content.
