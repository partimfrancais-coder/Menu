# Menu Studio

Each restaurant has an editable **Menu design prompt** section. The initial Kemang and Kuningan prompts describe their own reference PDF, layout, type hierarchy, legend, specials panel, pricing and content reflow rules. Prompts are saved in restaurant data and backups. This is a planning placeholder: saving a prompt does not generate a menu. Regression checks: `node --test tests/design-prompts.test.cjs`.

Local restaurant menu editor, preloaded from the supplied Kemang and Kuningan PDFs. Run `python server.py`, then open http://127.0.0.1:8765. Python 3.10+; no dependencies needed to run the editor.

The editor saves to `data/menus.json`. The previous successful file is retained in `data/menus.previous.json`. Export a JSON backup from the website for an additional portable copy, including uploaded images. Keep the project folder backed up. Do not run `scripts/seed.py` to update a live menu; that script only creates missing initial data.

Restaurant menus are independent. Prices preserve the PDF units (IDR × 1,000), so 95 means Rp 95,000. Tax and service charge are stored as separate percentages; no assumption is made about compounded calculation. Item options distinguish replacement prices from additional charges.

Each restaurant has a **Labels & serving details** manager. Add options, rename them, change their type, or remove them. Renames update assigned dishes in that restaurant; removals ask for confirmation when dishes are affected. Item editing displays separate label and serving-detail choices. Existing menus and older backups are migrated in the editor without replacing menu data. Restaurant copies have independent catalogs. Run catalog regression checks with `node --test tests/catalog.test.cjs`.

Initial entries are transcribed from artwork and marked for review. Review against each restaurant's source before approving for print. One special's spelling is explicitly flagged as unclear. Dietary labels reproduce source symbols and are not verified ingredient or allergy claims.

The local server binds to the local computer only. The Railway version uses Flask and Gunicorn with password authentication, secure session cookies, origin checks, and persistent disk storage. PDF layout generation is a later phase.

## Railway

Build with the included Dockerfile. Attach a persistent volume at `/data`; set `MENU_DATA_DIR=/data`, `PORT=8080`, and `MENU_PUBLIC_ORIGIN` to the exact HTTPS service URL. Set `MENU_USERNAME`, `MENU_PASSWORD_HASH` (a Werkzeug password hash), and a random `MENU_SESSION_SECRET` as private Railway variables. Optional additional logins can be supplied with `MENU_ADDITIONAL_USERS` as a JSON object mapping usernames to Werkzeug password hashes, for example `{"admin2":"scrypt:..."}`. Startup refuses to run with missing or malformed authentication configuration. Do not commit credentials. `.deployment/` and `.env*` are excluded from both Git and deployment uploads.

Use one replica and one Gunicorn worker (four threads). The file store uses a process lock and optimistic revision checks; multiple workers or replicas would require a transactional database. The initial menu data is copied only when the volume is empty. Later releases never replace the stored menus. `/health` checks storage readability; menus and PDFs require sign-in. Sessions expire after 12 hours; sign-in attempts are rate limited per IP within the running process. Export backups regularly.

Run checks with `python -m unittest discover -s tests -v` after installing `requirements.txt`. Gunicorn runs on Linux in the container; local editing still works with `python server.py` and no additional packages.

Files: `dist/` contains the interface; `server.py` provides local storage and source PDF access; `scripts/seed.py` records the initial transcription.

Labels and serving details support a built-in symbol or a custom PNG, JPG or WebP icon (up to 256 KB). Icons appear in item selections, item badges and the content preview. Use Clear to remove an icon. Icon assignments and image data are restaurant-specific and included in backups.

The icon picker includes 11 original menu icons under “Menu”. These are high-resolution PNG assets extracted from the supplied PDF's vector artwork, with white details preserved for display on colored surfaces. Reusable files are in `assets/menu-icons/`; the bundled web definitions are in `dist/menu-icons.js`. Matching options in newly initialized catalogs use these icons by default. Saved selections and explicitly cleared icons are retained.


## User management

Configured additional logins are imported as Editors without overwriting existing accounts. After import, manage their role and access through Manage users; removing an environment entry does not disable its saved account.

On first startup with account support, the existing MENU_USERNAME and MENU_PASSWORD_HASH seed a protected owner/admin account in `/data/accounts.sqlite3`. Subsequent starts preserve that account and its password; changing the bootstrap environment variables does not reset it. Existing shared sessions expire and users sign in again using their existing credentials. Back up the account database securely along with menu data; JSON menu exports do not include accounts or invitations.

Admins open **Manage users** in the top bar. Create an invitation for an email and choose Editor (default) or Admin. Copy the generated link and share it privately; no email is sent automatically. Invitations expire after seven days, work once, and store only a token hash. Reissuing an invitation invalidates the earlier link. Recipients choose a password of at least 12 characters and sign in using their invited email. Editors can edit all restaurants, but only admins can manage users. Role/access changes invalidate existing sessions. The owner cannot be disabled or demoted. There is no public registration or automated password recovery in this release.


## Restaurant data import/export

Use **Manage data** in a restaurant's header to download its saved data as an editable JSON file. Keep the `format: menu-studio-restaurant` and `version: 1` wrapper and edit the `restaurant` object. The file includes settings, logo, categories/items in order, prices, labels/icons, design prompt, and notes; it excludes user accounts and other restaurants.

Uploading replaces the selected restaurant object completely after validation and explicit confirmation; it never merges old dishes. The selected restaurant's internal identity is retained. Other restaurants remain unchanged. Missing optional prompt/catalog fields become empty. Invalid files and stale revisions are rejected without replacing current menu data. The automatic previous snapshot also receives the replacement, so it cannot restore the erased restaurant data. Previously downloaded files or backups outside this application are not deleted. This flow works in both the hosted app and local server.

Each item has an optional, manually editable **Product code** (up to 100 characters). Codes are text, so leading zeros and letters are preserved. They are included in restaurant JSON downloads and full backups, and retained on upload/restore. Older files without product codes remain valid and display a blank field. Product codes are internal data and do not change printed menu content.

## Shared Products catalog

Products is the master catalog above Restaurants. Create and edit names, codes, prices, descriptions, options, labels, icons and specifics there. Restaurants add existing products through a searchable picker. Edit on a menu row opens the shared product; changes apply everywhere it is used. Category membership is shared; ordering and visibility remain restaurant-specific. A product must be removed from all menus before deletion; non-empty product codes must be unique.

On first startup, existing entries with the same product code become a shared product, using KOI Kuningan first, then KOI Kemang, then remaining restaurants. Entries without codes stay separate. The migration preserves category/item IDs and order, increments the revision to protect open older windows, and keeps `menus.before-products.json` on the private data volume. The shared catalog lives in `products`, with `productTags` for shared label definitions. Each menu placement retains `productId` and materialized fields for existing PDF tooling and exports.

Restaurant data replacement still replaces the selected menu, but only accepts products already in the catalog (by ID or product code). Shared product details come from Products, not uploaded restaurant fields. Full backups include the catalog; pre-catalog full backups cannot overwrite a migrated workspace. Restaurant PDF design prompts remain independent.

## Shared product categories

Products has a category sidebar with counts and a single category selector per product. Create and rename categories there. Category changes move every placement of that product across all restaurant menus, without adding or removing products from a restaurant. Restaurants choose existing categories and can add only products assigned to the selected category. Restaurant category notes, order and product visibility remain local.

`productCategories` contains the shared taxonomy, each product has `categoryId`, and restaurant category containers have `catalogCategoryId`. Migration takes each product's category from Kuningan, then Kemang, then other restaurants, preserving all placement IDs. Obsolete headings with no products are removed during migration, including combined headings whose products now belong to separate categories. A private `menus.before-product-categories.json` snapshot is retained. Restaurant uploads resolve product categories from the catalog; they cannot override a product's shared category.

Products also have a cuisine dropdown: European or Asian. Existing products start unassigned; choose a cuisine when saving product edits. The shared value is included on restaurant exports and full backups.

## Public customer menus

Each restaurant toolbar includes Customer menu and Copy menu link. The stable public URL is `/menu/<restaurant-id>` and does not require sign-in. The mobile-first view has sticky category navigation, a category dropdown, continuous scrolling, product photos, full currency prices, options and assigned label icons. Smartphone cards use one column; portrait tablets use two. Missing images show a neutral placeholder; photos are requested lazily through a public image endpoint.

Public responses use an explicit field allowlist in `public_menu.py`. Only available menu entries are published; private notes, product codes, design prompts, review flags, accounts and the shared workspace remain private. Empty categories are omitted. The public view reads the latest saved data when opened/refreshed. It does not place orders. Uploaded images and labels come from Products.
