"""Render the Japanese–English manual and package a standalone offline copy."""
from pathlib import Path
import hashlib
import zipfile
import markdown

ROOT=Path(__file__).resolve().parents[1]
STYLE='''
@font-face{font-family:Plex;src:url(../assets/fonts/IBMPlexSans-Regular.ttf)}
@font-face{font-family:Plex;src:url(../assets/fonts/IBMPlexSans-SemiBold.ttf);font-weight:600 900}
@font-face{font-family:PlexJP;src:url(../assets/fonts/IBMPlexSansJP-Regular.ttf)}

*{box-sizing:border-box}html{scroll-behavior:smooth}body{font:16px/1.8 Plex,PlexJP,sans-serif;color:#263c50;background:#f3f6fa;margin:0}
main{max-width:1080px;margin:32px auto;padding:40px 48px;background:white;border:1px solid #d9e5e1;border-radius:14px}
h1{font-size:32px;line-height:1.4;color:#062c54}h2{font-size:25px;margin:42px 0 16px;padding-top:14px;border-top:2px solid #deedf8}h3{font-size:20px;margin-top:28px}
p{margin:10px 0 18px}a{color:#007bc1}table{border-collapse:collapse;width:100%;font-size:14px;margin:18px 0}th,td{padding:12px;border:1px solid #dbe5e1;text-align:left;vertical-align:top}th{background:#eaf2f9}
code{font-family:ui-monospace,monospace;font-size:.9em;background:#edf3f8;border-radius:3px;padding:2px 4px;overflow-wrap:anywhere}pre{padding:16px;background:#edf3f8;overflow:auto}
img{max-width:100%;height:auto;border:1px solid #dbe5e1;border-radius:8px}li{margin-bottom:12px}.toc{background:#edf3f8;padding:16px 24px;border-radius:8px}.toc li{margin:3px 0}.toc ul{padding-left:24px}
@media(max-width:720px){main{padding:22px 16px;margin:0;border-radius:0}h1{font-size:26px}table{font-size:12px}th,td{padding:7px}}
@media print{body{background:white}main{border:0;margin:0;padding:0}h2,h3{break-after:avoid}tr,img{break-inside:avoid}a{color:inherit}}
'''

def render(text,toc=False):
    if toc:text=text.replace('## 1.', '[TOC]\n\n## 1.',1)
    body=markdown.markdown(text,extensions=['tables','fenced_code','toc'],extension_configs={'toc':{'toc_depth':'2'}})
    body=body.replace('href="VALIDATION.md"','href="validation-status.html"')
    return '<!doctype html>\n<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GLIA Center ATP Studio — 操作マニュアル / User manual</title><style>'+STYLE+'</style></head><body><main>'+body+'</main></body></html>\n'

def main():
    docs=ROOT/'docs'
    guide=render((docs/'USER_GUIDE.md').read_text(encoding='utf-8'),True)
    status=render((docs/'VALIDATION.md').read_text(encoding='utf-8'))
    (docs/'user-guide.html').write_text(guide,encoding='utf-8')
    (docs/'validation-status.html').write_text(status,encoding='utf-8')
    archive=ROOT/'dist/GLIA-Center-ATP-Studio-Manual-JA-EN.zip';archive.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('manual.html',guide.replace('../THIRD_PARTY_NOTICES.txt','THIRD_PARTY_NOTICES.txt').replace('../assets/fonts/','fonts/'))
        z.writestr('manual.md',(docs/'USER_GUIDE.md').read_text(encoding='utf-8').replace('../THIRD_PARTY_NOTICES.txt','THIRD_PARTY_NOTICES.txt'))
        z.writestr('validation-status.html',status.replace('../assets/fonts/','fonts/'))
        for p in sorted((ROOT/'assets/fonts').iterdir()):z.write(p,'fonts/'+p.name)
        z.write(docs/'VALIDATION.md','VALIDATION.md')
        z.write(ROOT/'THIRD_PARTY_NOTICES.txt','THIRD_PARTY_NOTICES.txt')
        for p in sorted((docs/'screenshots').glob('*.png')):z.write(p,'screenshots/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n',encoding='utf-8')
    print(archive)

if __name__=='__main__':main()
