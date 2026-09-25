"""Exercise the standalone renderer with changed content, prices and availability."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import fitz

ROOT = Path(__file__).resolve().parents[1]
FONT = Path('C:/Windows/Fonts/calibri.ttf')


@unittest.skipUnless(FONT.exists(), 'Desktop renderer proof requires local Calibri fonts')
class MahakamRendererTests(unittest.TestCase):
    def test_current_content_dividers_options_and_hidden_items(self):
        def item(name, cuisine, **fields):
            return dict(id=name, name=name, cuisine=cuisine, available=True, price=65,
                        description='Fresh saved description', tags=[], options=[], **fields)
        hidden = item('Hidden dish', 'European'); hidden['available'] = False
        data = dict(name='KOI Mahakam', menuTitle='Lunch & Dinner', dietaryNote='No pork, no lard',
                    footer='Test footer', tagCatalog=[], categories=[
            dict(name='Finger Food', items=[item('Chicken Lahmacun', 'European'), hidden]),
            dict(name='Soups', items=[item('European Soup', 'European'), item('Asian Soup', 'Asian')]),
            dict(name='Beef', items=[item('Test Beef', 'European')]),
            dict(name='Seafood', items=[item('Test Fish', 'European')]),
        ])
        data['categories'][-1]['items'][0]['options'] = [{'name':'Extra sauce','price':17,'kind':'Add-on'}]
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory)/'restaurant.json'; output=Path(directory)/'menu.pdf'
            snapshot.write_text(json.dumps(data),encoding='utf-8')
            result=subprocess.run([sys.executable,str(ROOT/'scripts/build_mahakam_menu.py'),
                                   '--snapshot',str(snapshot),'--output',str(output)],cwd=ROOT,
                                  capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            audit=json.loads(output.with_suffix('.audit.json').read_text())
            self.assertEqual(audit['count'],5)
            self.assertEqual(audit['dividers'],['Soups'])
            with fitz.open(output) as doc:
                text=' '.join(' '.join(p.get_text() for p in doc).split())
                self.assertIn('Chicken Lahmacun',text)
                self.assertIn('+17',text)
                self.assertNotIn('Hidden dish',text)
                self.assertAlmostEqual(doc[0].rect.width,538.81,places=2)
                self.assertAlmostEqual(doc[0].rect.height,348,places=2)
