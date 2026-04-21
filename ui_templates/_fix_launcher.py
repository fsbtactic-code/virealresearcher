"""
Fix launcher.html: restore the missing configForm block.
The form body was stripped by remove_emojis.py in a previous session.
"""

form_block = open('ui_templates/_form_block.html', 'r', encoding='utf-8').read()
html = open('ui_templates/launcher.html', 'r', encoding='utf-8').read()

# Check if form already exists
if 'id="configForm"' in html:
    print("Form already present — no action needed")
    exit(0)

# Find the scroll-area opening div and inject the form right inside it
scroll_area_tag = 'class="scroll-area"'
idx = html.find(scroll_area_tag)
if idx == -1:
    print("ERROR: scroll-area not found")
    exit(1)

# Move past the closing > of the scroll-area div
end_of_opening_tag = html.find('>', idx) + 1

# Inject form right after the scroll-area opening tag
new_html = html[:end_of_opening_tag] + '\n' + form_block + html[end_of_opening_tag:]
open('ui_templates/launcher.html', 'w', encoding='utf-8').write(new_html)
print(f"SUCCESS: form injected at byte {end_of_opening_tag}, total {len(new_html)} bytes")
