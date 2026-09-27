#!/usr/bin/env python3
"""Render one PNG to argv[1]. Requires Pillow and DejaVu Sans."""
import sys
from PIL import Image, ImageDraw, ImageFont

image = Image.new('RGB', (1200, 680), '#f5f6fa')
draw = ImageDraw.Draw(image)
font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
title = ImageFont.truetype(font, 42)
body = ImageFont.truetype(font, 26)
draw.text((80, 60), 'Inlay — the source stays with the picture', font=title, fill='#203047')
for x, label, color in [(80, 'Edit source', '#3176bd'), (460, 'Render', '#318568'), (840, 'Save PNG', '#865ac1')]:
    draw.rounded_rectangle((x, 260, x+280, 400), radius=22, fill=color)
    draw.text((x+140, 330), label, anchor='mm', font=body, fill='white')
for x in (380, 760):
    draw.line((x, 330, x+60, 330), fill='#708096', width=5)
    draw.polygon([(x+60, 330), (x+45, 320), (x+45, 340)], fill='#708096')
draw.text((80, 530), 'One picture. One script. No project required.', font=body, fill='#526077')
image.save(sys.argv[1])
