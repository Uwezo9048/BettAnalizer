# save as test_ocr.py
from PIL import Image, ImageDraw, ImageFont

# Create a simple image with text
img = Image.new('RGB', (800, 200), color='white')
d = ImageDraw.Draw(img)
d.text((50, 50), "Liverpool vs Arsenal - Home @ 2.10", fill='black')
d.text((50, 100), "Real Madrid vs Barcelona - Draw @ 3.40", fill='black')
img.save('test_betslip.png')
print("Created test_betslip.png")