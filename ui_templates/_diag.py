"""Find the scroll-area div in HTML and print its position."""
import re

html = open('ui_templates/launcher.html', 'r', encoding='utf-8').read()
pattern = re.compile(r'<div[^>]+class="scroll-area"')
matches = list(pattern.finditer(html))
print('scroll-area divs:', [(m.start(), m.group()[:60]) for m in matches])

# Also check what's at char 12485
print('At 12485:', repr(html[12400:12600]))
