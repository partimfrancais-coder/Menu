from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[2]
source = root / 'ai-skills/koi-kuningan-drinks-menu-pdf'
target = root / 'ai-skills/koi-mahakam-drinks-menu-pdf'
assert not target.exists(), 'Refusing to replace an existing skill'
for relative in ['SKILL.md', 'references/workflow.md', 'scripts/prepare_snapshot.py', 'agents/openai.yaml']:
    text = (source / relative).read_text(encoding='utf-8')
    for old, new in [
        ('b8ae17c2-f1e0-4169-8a95-40f4b9b39cc9', '99b9b1b3-6731-4b93-971d-10a1c4e990a4'),
        ('Kuningan', 'Mahakam'), ('kuningan', 'mahakam'), ('KUNINGAN', 'MAHAKAM'),
        ('1190.64 x 841.92', '1190.55 x 841.89'),
        ('Mahakam Fingerood Drinks Menu 20260720.pdf', 'Mahakam Fingerfood Drinks Standart Menu November.pdf'),
    ]:
        text = text.replace(old, new)
    if relative == 'SKILL.md':
        text = text.replace('Happy Hour and cocktail offers are separate red-bordered panels below their supporting columns.',
                            'Happy Hour and cocktail offers are separate red-bordered panels below their supporting columns. The reference also has a Thursday Aperitivo box explicitly restricted to Kemang and Mega Kuningan; omit that offer for Mahakam unless current saved Mahakam data or the user explicitly authorizes it.')
        text = text.replace('Do not run a Lunch & Dinner renderer or reuse Rooftop artwork.',
                            'Do not run a Lunch & Dinner renderer or reuse Kuningan or Rooftop artwork.')
    elif relative == 'references/workflow.md':
        text = text.replace('Its tiny historical footer names Kemang;', 'Its tiny historical footer names Kuningan;')
        text = text.replace('x=94..1116, y=113..240', 'x=94..1116, y=113..225')
        text = text.replace('heading baseline near y=323', 'heading text around y=281..305')
        text = text.replace('approximately 20pt', 'approximately 21pt')
        text = text.replace('Belgium/Ireland/Germany', 'Belgium/Mexico/Germany')
        text = text.replace('Red-bordered panel beneath the central drink content;', 'Red-bordered panel beneath the left-side drink content;')
        text = text.replace('| Cocktails promotion |', '| Thursday Aperitivo | Historical center panel is restricted in the artwork to Kemang and Mega Kuningan. Omit it for Mahakam unless explicitly authorized in current Mahakam data or by the user; reflow the remaining panels without retaining an empty box. |\n| Cocktails promotion |')
        text = text.replace('The source uses Calibri, Arial Bold, Trebuchet Bold and Copperplate Gothic Bold.',
                            'The source uses Calibri, Arial, Myriad Pro, Trebuchet Bold and Copperplate Gothic Bold. Copperplate Gothic Bold gives the main titles and red headings their distinctive broad serif shape; prefer it or tightly isolated matching vector heading artwork.')
        text = text.replace('Include the current saved category notes, which may change; no automatic Thursday Aperitivo or other branch\'s offers.',
                            'Include current saved category notes, which may change. Its Thursday Aperitivo box explicitly says "Only at Kemang & Mega Kuningan" and was not imported into Mahakam. Do not reproduce that offer merely because it appears on the reference PDF.')
        text = text.replace('## Flow and content rules\n',
                            '## Flow and content rules\n\nMahakam\'s source has Local/Imported Beers in column one; Bali Craft Beers, Ciders, Soju, Wine and Milkshake in column two; Mocktails, Soft, Water, Juice and Chocolate in column three; and Tea, Coffee and Healthy Drink in column four. Use that arrangement as a visual starting point while respecting current saved order. Do not import Kuningan\'s Matcha, Smoothies or Signature Latte sections unless they actually exist in the current Mahakam menu.\n')
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding='utf-8')
(target / 'assets').mkdir()
shutil.copy2(Path('C:/Users/Owner/Downloads/Mahakam Fingerfood Drinks Standart Menu November.pdf'), target / 'assets/mahakam-drinks-original.pdf')
shutil.copy2(root / 'tmp/drinks-import/2-0.png', target / 'assets/mahakam-drinks-reference.png')
shutil.copy2(root / 'dist/menu-icons.js', target / 'assets/menu-icons.js')
print(target)
