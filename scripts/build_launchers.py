"""Create platform icons and desktop launchers; no recording data is read."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def build_icons():
    # The official site's app icon is already designed for a light background.
    # Only file format and resolution change; retain the complete logo.
    source = ROOT / 'assets/yamanashi-glia-touch.png'
    icon = Image.open(source).convert('RGBA').resize((1024, 1024), Image.Resampling.LANCZOS)
    icon.save(ROOT / 'assets/atp-studio.ico', sizes=[(n, n) for n in (16, 24, 32, 48, 64, 128, 256)])
    icon.save(ROOT / 'assets/atp-studio.icns')
    manifest = json.loads((ROOT / 'assets/logo-provenance.json').read_text())
    manifest['application_icons'] = {
        'source_file': source.name,
        'operation': 'Resolution and container conversion only; official logo retained in full.',
        'files': {name: hashlib.sha256((ROOT / 'assets' / name).read_bytes()).hexdigest()
                  for name in ('atp-studio.ico', 'atp-studio.icns')},
    }
    (ROOT / 'assets/logo-provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')


def build_windows(zig):
    output = ROOT / 'build-cache/windows-launcher'
    output.mkdir(parents=True, exist_ok=True)
    resource = output / 'launcher.res'
    binary = ROOT / 'dist/GLIA-Center-ATP-Studio-Windows-x64/GLIA Center ATP Studio.exe'
    binary.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([zig, 'rc', '/c', '65001', '/fo', str(resource), 'windows_launcher.rc'],
                   cwd=ROOT / 'launcher', check=True)
    subprocess.run([zig, 'cc', '-target', 'x86_64-windows-gnu', '-Os', '-s', '-municode',
                    '-Wl,--subsystem,windows', '-Wall', '-Wextra', '-Wno-unused-parameter',
                    str(ROOT / 'launcher/windows_launcher.c'), str(resource),
                    '-luser32', '-o', str(binary)], check=True)
    print(binary)


def build_mac():
    bundle = ROOT / 'GLIA Center ATP Studio.app/Contents'
    (bundle / 'MacOS').mkdir(parents=True, exist_ok=True)
    (bundle / 'Resources').mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'assets/atp-studio.icns', bundle / 'Resources/atp-studio.icns')
    info = {'CFBundleName': 'GLIA Center ATP Studio', 'CFBundleDisplayName': 'GLIA Center ATP Studio',
            'CFBundleExecutable': 'GLIA Center ATP Studio', 'CFBundleIconFile': 'atp-studio.icns',
            'CFBundleIdentifier': 'org.gliacenter.atpstudio.desktop', 'CFBundlePackageType': 'APPL',
            'CFBundleVersion': '0.4.0', 'CFBundleShortVersionString': '0.4.0',
            'LSMinimumSystemVersion': '11.0', 'NSHighResolutionCapable': True}
    (bundle / 'Info.plist').write_bytes(plistlib.dumps(info))
    subprocess.run(['clang', '-Os', '-Wall', '-Wextra', str(ROOT / 'launcher/macos_launcher.c'),
                    '-framework', 'CoreFoundation', '-o', str(bundle / 'MacOS/GLIA Center ATP Studio')], check=True)
    subprocess.run(['codesign', '--force', '--sign', '-', str(bundle.parent)], check=True)
    print(bundle.parent)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--zig', default=os.environ.get('ZIG') or shutil.which('zig'))
    parser.add_argument('--mac', action='store_true', help='Create a launcher for this Mac, using the local .venv.')
    args = parser.parse_args()
    build_icons()
    if args.zig:
        build_windows(str(Path(args.zig).resolve()))
    if args.mac:
        if sys.platform != 'darwin':
            parser.error('--mac requires macOS')
        build_mac()
