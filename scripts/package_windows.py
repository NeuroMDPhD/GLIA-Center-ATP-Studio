"""Assemble the portable Windows x64 directory after runtime download and wheel resolution.
This builds a distributable layout on macOS; it does not claim to execute Windows binaries.
"""
from pathlib import Path
import hashlib,json,shutil,zipfile,subprocess,re

root=Path(__file__).resolve().parents[1]
out=root/'dist/ATP-ROA-Studio-Windows-x64'
assert (out/'python/python.exe').is_file()
assert (out/'python/pythonw.exe').is_file()
assert (out/'ATP ROA Studio.exe').is_file()
assert (out/'runtime/jre/bin/java.exe').is_file()
assert (out/'python/Lib/site-packages/PySide6/QtWidgets.pyd').is_file()
for name in ('atp_studio','java','docs','assets','launcher'):
    shutil.copytree(root/name,out/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
# Keep real-recording QA details and screenshots local. Manual illustrations may ship.
if (out/'docs/images').exists():shutil.rmtree(out/'docs/images')
report=out/'docs/validation.html'
shutil.copy2(root/'docs/validation-status.html',report)
shutil.copytree(root/'runtime/java-libs',out/'runtime/java-libs',dirs_exist_ok=True)
shutil.copytree(root/'vendor/AQuA2-Fiji',out/'vendor/AQuA2-Fiji',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git'))
for name in ('launch.py','START.bat','README.txt','README.md','LICENSE','THIRD_PARTY_NOTICES.txt','requirements.txt','requirements-dev.txt','DEPENDENCIES.json'):
    shutil.copy2(root/name,out/name)
for name in ('START.bat',):
    p=out/name;s=p.read_text();p.write_bytes(s.replace('\r\n','\n').replace('\n','\r\n').encode('utf-8'))
(out/'scripts').mkdir(exist_ok=True)
for name in ('build_java.py','build_launchers.py','bootstrap_engine.py','build_manual.py','manual_screenshot.py'):
    shutil.copy2(root/'scripts'/name,out/'scripts'/name)
shutil.copytree(root/'tests',out/'tests',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
# Store checksums of every shipped file. No project data, source OIR or local venv enters this tree.
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
files=[p for p in out.rglob('*') if p.is_file() and p.name!='PACKAGE_MANIFEST.json']
for p in files:
    if p.suffix=='.oir' or p.name=='project.json':raise RuntimeError('Acquisition data must not be packaged')
manifest={'app_version':'0.1.0','target':'Windows 10/11 x64','entry_point':'ATP ROA Studio.exe','native_windows_tested':False,
          'tested_platform':'macOS arm64','file_count':len(files),'files':{str(p.relative_to(out)):digest(p) for p in files}}
(out/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
archive=root/'dist/ATP-ROA-Studio-Windows-x64.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in out.rglob('*'):
        if p.is_file():z.write(p,Path(out.name)/p.relative_to(out))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert not any(n.lower().endswith('.oir') for n in z.namelist())
(archive.with_suffix('.zip.sha256')).write_text(digest(archive)+'  '+archive.name+'\n')
print(json.dumps({'archive':str(archive),'size_bytes':archive.stat().st_size,'files':len(files),'sha256':digest(archive)},indent=2))
