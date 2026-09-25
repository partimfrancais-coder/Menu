"""Run the canonical Mahakam renderer also supplied to hosted menu generation."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[1] / 'ai-skills' / 'koi-menu-pdf' /
                       'scripts' / 'build_mahakam_menu.py'), run_name='__main__')
