"""Build local contact sheets for reviewing the revised gallery images."""
import json
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
HERE=Path(__file__).resolve().parent
files=list(json.loads((HERE/'figure_copy.json').read_text(encoding='utf-8')))
files=[f for f in files if f.endswith('.png')]
out=HERE/'revised_contact_sheets'
out.mkdir(exist_ok=True)
for start in range(0,len(files),6):
    sheet=Image.new('RGB',(1600,1500),'white')
    draw=ImageDraw.Draw(sheet)
    for offset,name in enumerate(files[start:start+6]):
        img=Image.open(HERE/'rendered'/name).convert('RGB')
        img.thumbnail((790,465))
        x=(offset%2)*800; y=(offset//2)*500
        sheet.paste(img,(x+(800-img.width)//2,y+25))
        draw.text((x+8,y+5),name,fill='black')
    sheet.save(out/f'sheet_{start//6+1:02}.jpg',quality=90)
print('Prepared',len(list(out.glob('*.jpg'))),'contact sheets')
