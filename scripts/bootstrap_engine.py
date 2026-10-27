"""Fetch checksum-pinned engine sources and JARs for a source checkout."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def download(spec,path):
    if path.is_file() and digest(path)==spec['sha256']:return
    path.parent.mkdir(parents=True,exist_ok=True)
    fd=tempfile.NamedTemporaryFile(dir=path.parent,suffix='.partial',delete=False)
    temporary=Path(fd.name)
    try:
        with fd,urllib.request.urlopen(spec['url'],timeout=120) as response:
            shutil.copyfileobj(response,fd)
        if digest(temporary)!=spec['sha256']:raise ValueError('Checksum mismatch: '+spec['url'])
        temporary.replace(path)
    finally:temporary.unlink(missing_ok=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--destination',type=Path,default=ROOT,help='Optional isolated engine-build directory.')
    args=parser.parse_args();dest=args.destination.resolve()
    manifest=json.loads((ROOT/'DEPENDENCIES.json').read_text(encoding='utf-8'))
    source=manifest['aqua2_source'];archive=dest/'build-cache/aqua2-source.zip'
    download(source,archive)
    vendor=dest/'vendor/AQuA2-Fiji';vendor.parent.mkdir(parents=True,exist_ok=True)
    prefix='AQuA2-Fiji-'+source['commit']+'/'
    with zipfile.ZipFile(archive) as z:
        members=[m for m in z.infolist() if m.filename.startswith(prefix) and not m.is_dir()]
        if not members:raise ValueError('Empty or unexpected upstream archive')
        if vendor.exists():
            # Never reset or overwrite a developer's changes to the engine.
            for member in members:
                relative=Path(member.filename[len(prefix):]);target=vendor/relative
                if not target.is_file() or hashlib.sha256(target.read_bytes()).digest()!=hashlib.sha256(z.read(member)).digest():
                    raise ValueError('Upstream source differs from the pinned archive; preserved without changes: '+str(target))
        else:
            with tempfile.TemporaryDirectory(dir=vendor.parent) as staging:
                stage=Path(staging)/'AQuA2-Fiji';stage.mkdir()
                for member in members:
                    relative=Path(member.filename[len(prefix):])
                    if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe source archive path')
                    target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(member))
                stage.rename(vendor)
    for item in manifest['java_libraries']:
        download(item,dest/'runtime/java-libs'/item['filename'])
    print('Pinned AQuA2 source and six dependency JARs verified at '+str(dest))

if __name__=='__main__':main()
