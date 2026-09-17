# Menu Studio

Local restaurant menu editor, preloaded from the supplied Kemang and Kuningan PDFs. Run `python server.py`, then open http://127.0.0.1:8765. Python 3.10+; no dependencies needed to run the editor.

The editor saves to `data/menus.json`. The previous successful file is retained in `data/menus.previous.json`. Export a JSON backup from the website for an additional portable copy, including uploaded images. Keep the project folder backed up. Do not run `scripts/seed.py` to update a live menu; that script only creates missing initial data.

Restaurant menus are independent. Prices preserve the PDF units (IDR × 1,000), so 95 means Rp 95,000. Tax and service charge are stored as separate percentages; no assumption is made about compounded calculation. Item options distinguish replacement prices from additional charges.

Initial entries are transcribed from artwork and marked for review. Review against each restaurant's source before approving for print. One special's spelling is explicitly flagged as unclear. Dietary labels reproduce source symbols and are not verified ingredient or allergy claims.

The local server binds to the local computer only. The Railway version uses Flask and Gunicorn with password authentication, secure session cookies, origin checks, and persistent disk storage. PDF layout generation is a later phase.

## Railway

Build with the included Dockerfile. Attach a persistent volume at `/data`; set `MENU_DATA_DIR=/data`, `PORT=8080`, and `MENU_PUBLIC_ORIGIN` to the exact HTTPS service URL. Set `MENU_USERNAME`, `MENU_PASSWORD_HASH` (a Werkzeug password hash), and a random `MENU_SESSION_SECRET` as private Railway variables. Startup refuses to run without authentication configuration. Do not commit credentials. `.deployment/` and `.env*` are excluded from both Git and deployment uploads.

Use one replica and one Gunicorn worker (four threads). The file store uses a process lock and optimistic revision checks; multiple workers or replicas would require a transactional database. The initial menu data is copied only when the volume is empty. Later releases never replace the stored menus. `/health` checks storage readability; menus and PDFs require sign-in. Sessions expire after 12 hours; sign-in attempts are rate limited per IP within the running process. Export backups regularly.

Run checks with `python -m unittest discover -s tests -v` after installing `requirements.txt`. Gunicorn runs on Linux in the container; local editing still works with `python server.py` and no additional packages.

Files: `dist/` contains the interface; `server.py` provides local storage and source PDF access; `scripts/seed.py` records the initial transcription.
