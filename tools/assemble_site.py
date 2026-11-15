import sys, json, shutil, os
tpl, site, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
idx = open(os.path.join(site, 'index.json'), encoding='utf-8').read()
json.loads(idx)
idx = idx.replace('</', '<\\/')
html = open(tpl, encoding='utf-8').read().replace('/*__INDEX__*/', idx)
open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(html)
shutil.copy(os.path.join(site, 'articles.json'), os.path.join(out, 'articles.json'))
print(len(html), os.path.getsize(os.path.join(out, 'articles.json')))
