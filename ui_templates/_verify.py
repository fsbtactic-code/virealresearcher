"""Verify the form restoration."""
html = open('ui_templates/launcher.html', 'r', encoding='utf-8').read()
print('configForm present:', ('id="configForm"' in html))
print('scrape_explore present:', ('scrape_explore' in html))
print('startBtn present:', ('startBtn' in html))
print('authStatusBox present:', ('authStatusBox' in html))
print('Total bytes:', len(html.encode('utf-8')))
