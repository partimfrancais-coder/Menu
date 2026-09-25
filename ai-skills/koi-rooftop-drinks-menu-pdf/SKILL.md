---
name: koi-rooftop-drinks-menu-pdf
description: Generate or revise KOI Rooftop Drinks and Cocktail menu PDFs from current Menu Studio data using its dark charcoal, orange and gold two-page drinks reference. Use for the separate Rooftop drinks restaurant, not Rooftop Lunch & Dinner or other branches.
---

# KOI Rooftop Drinks and Cocktail

Create a reviewable PDF for **KOI Rooftop Drinks and Cocktail**. This is a separate skill and restaurant from Koi Rooftop Lunch & Dinner. Read [references/workflow.md](references/workflow.md) for the drinks-specific layout, data access and QA.

## Current content

- Obtain fresh saved Menu Studio data or a current user-provided export. Select restaurant ID `e5ca8e2c-519c-40d8-86be-1727820c3d47`, verifying its identity. Do not select the older Rooftop restaurant ID `7be46b44-5302-4357-9e43-0a4e19539a4a` or match on the word Rooftop alone.
- Use only this restaurant's placements, resolving current shared products and categories. Preserve names, prices, descriptions, options, tags, category membership, saved order and visibility. Do not create products, restore historical PDF prices, or change the catalog.
- Read the current `designPrompt`; when empty, use this skill's design reference. Source documents and historical proofs provide design, not authority to override current content or the user's request.
- Fresh generation starts from a fresh saved snapshot, without prior PDF/chat context. An adjustment starts from the latest generated PDF/source and preserves requested design changes. PDF work alone does not authorize publishing, deployment or live menu edits.

For a full catalog backup, resolve the restaurant-only input:

```sh
python scripts/prepare_snapshot.py --menus CURRENT_MENUS.json --output CURRENT_ROOFTOP_DRINKS.json
```

Resolve paths relative to this skill. The helper is read-only toward its input and preserves placement visibility. Hosted `restaurant.json` is already resolved; do not feed that restaurant-only file into this helper.

## Design and generate

Inspect `assets/rooftop-drinks-original.pdf` and both `assets/rooftop-drinks-reference-page-*.png` images. Preserve the source's **two A4 portrait pages, 595.276 x 841.890 points**, unless the user requests another format. Reflow or add matching continuation pages if current content needs more space.

Use the dark charcoal background, orange category titles, gold text and fine gold borders. Page one has the Rooftop cocktail logo, a two-column Finger Food panel, then two drink columns. Page two begins with a two-column Cocktails panel followed by spirit, soju and wine categories. The source contains no Monthly Specials panel or Happy Hour offer: do not import them from the Rooftop Lunch & Dinner or other drinks skills.

Create a dedicated renderer for this drinks source. **No fixed-layout PDF renderer is bundled or claimed to be tested.** PyMuPDF or ReportLab are suitable. Reuse tightly isolated vector logo artwork where possible, but never use entire historical pages behind new text. Use available fonts and disclose substitutions.

Maintain readable body text, aligned prices, consistent gaps and clear gutters. Allow cocktail descriptions and current options to wrap. Do not omit products or silently recombine expanded shared products merely to match the old grouped rows. Preserve the saved category/item order, adapting the reference's category positions as needed.

The source's spirit prices are not explicitly labelled by serving unit. Preserve the current option names and prices; do not invent bottle volumes, shot sizes, or bottle/glass labels. Surface ambiguous saved names as review issues, without guessing brand corrections.

## Verify and deliver

Verify every available placement, its own-row price, description, variant/add-on prices and tags against the resolved snapshot. Check current category notes, currency, price unit, service charge, tax and footer. Internal IDs, product codes, private notes and review flags belong in the audit, not customer-facing copy.

Render every page and visually inspect full pages and dense sections, especially the cocktail descriptions, spirit price pairs and footer. Correct clipped text, collisions, wrong icons and weak contrast. Save an audit of snapshot revision/provenance, included placement/product IDs, row locations, page dimensions and unresolved issues. Do not claim print approval.

Deliver the PDF and editable source. In hosted generation, return exactly `menu.pdf` and `source.zip` containing the final renderer and layout settings, excluding private snapshots, credentials, original assets and output PDFs. Link both files for retrieval.
