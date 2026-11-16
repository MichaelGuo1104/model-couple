"""Package editable Vue source and offline runtime; no development cache."""
from pathlib import Path
import zipfile, hashlib, json, tempfile
root=Path(__file__).resolve().parents[1]
out=root.parent
manifest=[]
for p in sorted((root/'dist').rglob('*')):
 if p.is_file():manifest.append({'file':p.relative_to(root/'dist').as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
for p in (root/'public/assets').rglob('*.png'):
 q=root/'dist/assets'/p.relative_to(root/'public/assets')
 assert q.read_bytes()==p.read_bytes()
(root/'dist/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(root/'dist/README.txt').write_text('优秀情侣奖 · Vue 3 离线运行版\n用Edge或Chrome打开index.html。无需安装依赖或联网。请复制完整文件夹。\n公文依赖系统宋体，无宋体时自动回退。存档在浏览器中，不随文件复制。\n',encoding='utf-8')
for kind in ['source','offline']:
 archive=out/f'any-award-vue-{kind}.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  if kind=='source':
   for p in sorted(root.rglob('*')):
    rel=p.relative_to(root)
    if any(part in ['node_modules','.git','__pycache__'] for part in rel.parts) or rel.name=='isolation-entry.txt' or not p.is_file():continue
    z.write(p,Path('any-award-vue')/rel)
  else:
   for p in sorted((root/'dist').rglob('*')):
    if p.is_file():z.write(p,Path('any-award-vue-offline')/p.relative_to(root/'dist'))
 print(archive,archive.stat().st_size)
target=Path(tempfile.mkdtemp(prefix='any-award-vue-offline-'))
with zipfile.ZipFile(out/'any-award-vue-offline.zip') as z:z.extractall(target)
entry=target/'any-award-vue-offline/index.html'
(root/'isolation-entry.txt').write_text(str(entry),encoding='utf-8')
print('Isolation test entry:',entry)
