# Menu Studio

Local restaurant menu editor, preloaded from the supplied Kemang and Kuningan PDFs. Run `python server.py`, then open http://127.0.0.1:8765. Python 3.10+; no dependencies needed to run the editor.

The editor saves to `data/menus.json`. The previous successful file is retained in `data/menus.previous.json`. Export a JSON backup from the website for an additional portable copy, including uploaded images. Keep the project folder backed up. Do not run `scripts/seed.py` to update a live menu; that script only creates missing initial data.

Restaurant menus are independent. Prices preserve the PDF units (IDR × 1,000), so 95 means Rp 95,000. Tax and service charge are stored as separate percentages; no assumption is made about compounded calculation. Item options distinguish replacement prices from additional charges.

Initial entries are transcribed from artwork and marked for review. Review against each restaurant's source before approving for print. One special's spelling is explicitly flagged as unclear. Dietary labels reproduce source symbols and are not verified ingredient or allergy claims.

This version is a local, single-user editor with disk persistence and optimistic concurrency protection. The server binds to the local computer only. It is not an authenticated hosted application. PDF layout generation is a later phase. For multi-device use, add authenticated shared storage before deployment.

Files: `dist/` contains the interface; `server.py` provides local storage and source PDF access; `scripts/seed.py` records the initial transcription.
