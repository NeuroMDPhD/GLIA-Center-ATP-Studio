"""Assemble the portable Windows x64 ZIP from the pre-staged runtime.

The staging directory retains the original wheels. The release omits unused QML
assets and uses a short root so Explorer can extract it at ordinary user paths.
This builder runs on macOS; it does not execute Windows binaries.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = 'GLIA-ATP'
# Include the ZIP's top-level folder in this budget. Leave at least 119 UTF-16
# code units for the extraction destination and separator below MAX_PATH (260).
MAX_ARCHIVE_PATH_UNITS = 140
UNUSED_QML = PurePosixPath('python/Lib/site-packages/PySide6/qml')


def shipped_path(relative):
    """Keep the Widgets runtime, plugins and licenses; omit unused QML assets."""
    path = PurePosixPath(relative)
    return (not path.is_relative_to(UNUSED_QML)
            and '__pycache__' not in path.parts
            and '.git' not in path.parts
            and path.name != '.DS_Store')


def utf16_units(text):
    return len(text.encode('utf-16-le')) // 2


def check_archive_paths(names):
    """Fail the build, rather than ship a new Explorer path-length regression."""
    if not names:
        raise ValueError('The Windows archive is empty')
    longest = max(names, key=utf16_units)
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or path.parts[0] != ARCHIVE_ROOT:
            raise ValueError(f'Unexpected archive path: {name}')
        if utf16_units(name) > MAX_ARCHIVE_PATH_UNITS:
            raise ValueError(f'Windows extraction path exceeds {MAX_ARCHIVE_PATH_UNITS} UTF-16 units: {name}')
    return {'archive_root': ARCHIVE_ROOT, 'max_archive_path_units': utf16_units(longest),
            'longest_archive_path': longest, 'path_budget_units': MAX_ARCHIVE_PATH_UNITS,
            'path_unit': 'UTF-16 code units', 'excluded_directories': [str(UNUSED_QML)]}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    out = ROOT / 'dist/GLIA-Center-ATP-Studio-Windows-x64'
    required = ('python/python.exe', 'python/pythonw.exe', 'GLIA Center ATP Studio.exe',
                'runtime/jre/bin/java.exe', 'python/Lib/site-packages/PySide6/QtWidgets.pyd',
                'python/Lib/site-packages/PySide6/plugins/platforms/qwindows.dll')
    for name in required:
        if not (out / name).is_file():
            raise RuntimeError(f'Missing Windows runtime file: {name}')
    for name in ('atp_studio', 'java', 'docs', 'assets', 'launcher'):
        shutil.copytree(ROOT / name, out / name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    # Keep real-recording QA details and screenshots local. Manual illustrations may ship.
    if (out / 'docs/images').exists():
        shutil.rmtree(out / 'docs/images')
    shutil.copy2(ROOT / 'docs/validation-status.html', out / 'docs/validation.html')
    shutil.copytree(ROOT / 'runtime/java-libs', out / 'runtime/java-libs', dirs_exist_ok=True)
    shutil.copytree(ROOT / 'vendor/AQuA2-Fiji', out / 'vendor/AQuA2-Fiji', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('.git'))
    for name in ('launch.py', 'START.bat', 'README.txt', 'README.md', 'LICENSE',
                 'THIRD_PARTY_NOTICES.txt', 'requirements.txt', 'requirements-dev.txt', 'DEPENDENCIES.json'):
        shutil.copy2(ROOT / name, out / name)
    p = out / 'START.bat'
    p.write_bytes(p.read_text().replace('\r\n', '\n').replace('\n', '\r\n').encode('utf-8'))
    (out / 'scripts').mkdir(exist_ok=True)
    for name in ('build_java.py', 'build_launchers.py', 'bootstrap_engine.py', 'build_manual.py',
                 'manual_screenshot.py', 'package_windows.py', 'windows_smoke.py'):
        shutil.copy2(ROOT / 'scripts' / name, out / 'scripts' / name)
    shutil.copytree(ROOT / 'tests', out / 'tests', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__'))
    files = sorted(p for p in out.rglob('*') if p.is_file() and p.name != 'PACKAGE_MANIFEST.json'
                   and shipped_path(p.relative_to(out).as_posix()))
    for p in files:
        # SciPy's wheel includes synthetic MAT reader fixtures, not recordings.
        scipy_fixture = p.relative_to(out).is_relative_to('python/Lib/site-packages/scipy/io/matlab/tests/data')
        if (p.suffix.lower() in ('.oir', '.oib') or p.name == 'project.json'
                or (p.suffix.lower() == '.mat' and not scipy_fixture)):
            raise RuntimeError(f'Acquisition data must not be packaged: {p.relative_to(out)}')
    names = [f'{ARCHIVE_ROOT}/{p.relative_to(out).as_posix()}' for p in files]
    names.append(f'{ARCHIVE_ROOT}/PACKAGE_MANIFEST.json')
    extraction = check_archive_paths(names)
    # Read the version without importing GUI or platform-dependent dependencies.
    version = (ROOT / 'atp_studio/__init__.py').read_text().split("'")[1]
    manifest = {'app_version': version, 'target': 'Windows 10/11 x64',
                'entry_point': 'GLIA Center ATP Studio.exe', 'native_windows_tested': False,
                'tested_platform': 'macOS arm64 (builder)', 'file_count': len(files),
                'extraction': extraction,
                'files': {p.relative_to(out).as_posix(): digest(p) for p in files}}
    manifest_path = out / 'PACKAGE_MANIFEST.json'
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    archive = ROOT / 'dist/GLIA-Center-ATP-Studio-Windows-x64.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in [*files, manifest_path]:
            z.write(p, f'{ARCHIVE_ROOT}/{p.relative_to(out).as_posix()}')
    with zipfile.ZipFile(archive) as z:
        check_archive_paths(z.namelist())
        if z.testzip() is not None:
            raise RuntimeError('Windows ZIP integrity check failed')
    checksum = digest(archive)
    archive.with_suffix('.zip.sha256').write_text(checksum + '  ' + archive.name + '\n')
    print(json.dumps({'archive': str(archive), 'size_bytes': archive.stat().st_size,
                      'files': len(files), 'sha256': checksum, 'extraction': extraction}, indent=2))


if __name__ == '__main__':
    main()
