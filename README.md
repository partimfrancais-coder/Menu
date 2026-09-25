# Menu Studio

Each restaurant has an editable **Menu design prompt** section. The initial Kemang and Kuningan prompts describe their own reference PDF, layout, type hierarchy, legend, specials panel, pricing and content reflow rules. Prompts are saved in restaurant data and backups. Saving a prompt does not itself generate a menu. In the hosted workspace, Generate menu uses it to create a PDF conversation. Regression checks: `node --test tests/design-prompts.test.cjs`.

Local restaurant menu editor, preloaded from the supplied Kemang and Kuningan PDFs. Run `python server.py`, then open http://127.0.0.1:8765. Python 3.10+; no dependencies needed to run the editor.

The editor saves to `data/menus.json`. The previous successful file is retained in `data/menus.previous.json`. Export a JSON backup from the website for an additional portable copy, including uploaded images. Keep the project folder backed up. Do not run `scripts/seed.py` to update a live menu; that script only creates missing initial data.

Restaurant menus are independent. Prices preserve the PDF units (IDR × 1,000), so 95 means Rp 95,000. Tax and service charge are stored as separate percentages; no assumption is made about compounded calculation. Item options distinguish replacement prices from additional charges.

Each restaurant has a **Labels & serving details** manager. Add options, rename them, change their type, or remove them. Renames update assigned dishes in that restaurant; removals ask for confirmation when dishes are affected. Item editing displays separate label and serving-detail choices. Existing menus and older backups are migrated in the editor without replacing menu data. Restaurant copies have independent catalogs. Run catalog regression checks with `node --test tests/catalog.test.cjs`.

Initial entries are transcribed from artwork and marked for review. Review against each restaurant's source before approving for print. One special's spelling is explicitly flagged as unclear. Dietary labels reproduce source symbols and are not verified ingredient or allergy claims.

The local server binds to the local computer only. The Railway version uses Flask and Gunicorn with password authentication, secure session cookies, origin checks, and persistent disk storage. AI PDF generation is available in the authenticated hosted workspace.

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


## AI menu PDF conversations

Mahakam now has a dedicated standalone renderer: `python scripts/build_mahakam_menu.py --snapshot CURRENT_RESTAURANT.json --output menu.pdf`. The canonical script lives in `ai-skills/koi-menu-pdf/scripts/` so hosted generation receives the same implementation. Pass `--source`, `--icons`, `--date`, `--font-regular` and `--font-bold` explicitly in hosted/Linux environments. It preserves Mahakam's physical size, current available items and saved order, and emits a coverage/row-price audit next to the PDF. Extra whole categories can continue on additional pages; an oversized single category or specials panel requires explicit layout adaptation rather than dropping dishes.

The red **Generate menu** button only opens a private conversation for the signed-in user and selected restaurant. Click **Generate menu** inside the chat to start the first PDF, or **Regenerate from saved menu** to create a fresh version when a conversation already exists. Opening or reopening the chat never starts generation. Later messages ask for revisions; every PDF version remains available to preview, enlarge and download. Conversations persist across refreshes and sign-outs. Save menu edits before generating; the server rejects stale menu revisions. PDF revisions never write back to the catalog or public menu.

Alain saves an OpenAI API key in the top bar. Only the account configured by `MENU_AI_KEY_USERNAME` (default `alain`) can save or remove it. The server supplies the same permission to the interface. All authenticated workspace users can generate with that key and incur API charges. Keys are encrypted using a key derived from `MENU_SESSION_SECRET` and stored in the private `menu-ai/conversations.sqlite3` database under `MENU_DATA_DIR`; plaintext keys are not returned to the browser, persisted in browser storage, included in exports, or sent to the model. Replacing the session secret requires Alain to re-enter his API key. Removing a key stops new requests; an already running request may finish.

Generation uses the Responses API with `gpt-6-astra` and Code Interpreter. Each request receives the deployed `ai-skills/koi-menu-pdf` skill, the selected restaurant's fresh saved snapshot and reference artwork, current icon library, conversation history and previous PDF/editable source. Generated code runs in OpenAI's sandbox, never on the application server. Returned PDFs are parsed and rendered into page previews, with missing dish-name warnings. The skill requires visual and content checks; generated proofs still require human approval. Linux font substitutions may differ from the desktop Calibri renderers.

Artifacts and private conversation state live in `MENU_DATA_DIR/menu-ai/` on the existing volume. Back up that directory securely; it is excluded from menu JSON exports, Git and deployment uploads. Provider input files, responses and containers are removed on completion on a best-effort basis, after artifacts have been copied locally. Each request uses a fresh sandbox with the saved prior PDF and source, so revisions do not depend on an expired container.

Each restaurant also has design versions in `MENU_DATA_DIR/design-versions/`. The first view copies its current skill and reference PDF to immutable v1. Editors can upload a new SKILL.md and PDF together or ask the design chat to create both files; a new version remains inactive until selected. Menu generation pins the active design version when the request starts, and older versions remain available for review and reactivation. Back up `design-versions/` with the persistent volume; menu JSON exports do not include these files. AI design creation uses the saved API key and incurs provider usage. A restaurant without a reference PDF must upload an initial skill and PDF to create v1.

New generation attempts retain structured diagnostics in the private conversation database before provider cleanup: provider status, incomplete reason/error code, HTTP/network failures, elapsed time, code-step counts, token limits, and reported input/output/reasoning/cache token usage. Expand **Generation details** in the chat to inspect these fields. Missing usage is unavailable, not zero or a billing receipt. Diagnostics exclude provider error messages, raw responses, generated code, prompts, model identifiers and API keys. Existing attempts without retained metadata cannot be backfilled. Token-limit failures receive a specific explanation; this tracking does not automatically retry or change generation limits.

Keep one Gunicorn worker. The service allows two generation jobs concurrently and one per conversation, with a 20-minute generation deadline, 24,000 output-token cap, 25 MB file cap and 12-page PDF cap. Duplicate request IDs do not trigger duplicate generation. Interrupted jobs are marked failed on restart; they are never automatically retried or billed again. An interrupted upstream request may still have incurred charges. Old PDF versions remain available. OpenAI model/tool access and billing must be enabled for Alain's key.

Verification: `python -m unittest discover -s tests -v`, `node --test tests/*.test.cjs`, and JavaScript syntax checks. `tests/serve_menu_ai_fixture.py` is a loopback-only HTTPS browser fixture using a fake provider and temporary storage. It never calls OpenAI. A live end-to-end generation check requires Alain's actual key; simulated-provider tests do not establish live generation quality or model access.
