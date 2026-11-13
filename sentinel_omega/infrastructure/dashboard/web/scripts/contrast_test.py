#!/usr/bin/env python3
"""
Contrast WCAG AA test for dashboard palette
"""
import re
css_path = 'src/index.css'
txt = open(css_path).read()
vars = dict(re.findall(r'--color-([\w-]+):\s*(#[0-9a-fA-F]{6});', txt))
def lum(hexc):
    r,g,b = [int(hexc[i:i+2],16)/255 for i in (1,3,5)]
    def f(c):
        return c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4
    return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)
def ratio(a,b):
    la,lb = lum(a),lum(b)
    return (max(la,lb)+0.05)/(min(la,lb)+0.05)
fg = vars.get('foreground','#f0f4f8')
bg = '#050607'
print('Foreground vs background', ratio(fg,bg))
for name in ['calma','atencion','aviso','critico']:
    col = vars.get(name)
    if col:
        print(name, ratio(col, bg))
print('OK' if ratio(fg,bg)>=4.5 else 'FAIL')
