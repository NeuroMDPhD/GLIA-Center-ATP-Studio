"""Run with the extracted Windows package's Python; no recordings are needed."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    assert sys.platform == 'win32', 'This check requires native Windows'
    assert Path(sys.executable).resolve() == (ROOT / 'python/python.exe').resolve()
    report_path = Path(sys.argv[1]).resolve()
    manifest = json.loads((ROOT / 'PACKAGE_MANIFEST.json').read_text())
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()
              and '__pycache__' not in p.parts and p.name != 'PACKAGE_MANIFEST.json'}
    assert actual == set(manifest['files']), 'Extracted file list differs from the manifest'
    for name, expected in manifest['files'].items():
        with (ROOT / name).open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected, name
    assert not (ROOT / 'python/Lib/site-packages/PySide6/qml').exists()
    max_path = max(len(str(ROOT / name).encode('utf-16-le')) // 2 for name in actual)
    assert max_path < 260, f'Extraction paths exceeded MAX_PATH: {max_path}'

    # Exercise the native DLLs used for imaging, quantitative results and media.
    import numpy as np
    import scipy.ndimage
    import h5py
    import tifffile
    import imageio_ffmpeg
    from PIL import Image
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        pixels = np.arange(64, dtype=np.uint16).reshape(8, 8)
        tifffile.imwrite(folder / 'pixels.tif', pixels)
        assert np.array_equal(tifffile.imread(folder / 'pixels.tif'), pixels)
        with h5py.File(folder / 'pixels.h5', 'w') as f:
            f['pixels'] = pixels
        with h5py.File(folder / 'pixels.h5') as f:
            assert np.array_equal(f['pixels'][:], pixels)
        assert scipy.ndimage.median_filter(pixels, size=3).shape == pixels.shape
        Image.fromarray(pixels).save(folder / 'pixels.png')
        with Image.open(folder / 'pixels.png') as image:
            image.verify()
    java = subprocess.run([str(ROOT / 'runtime/jre/bin/java.exe'), '-version'],
                          check=True, capture_output=True, text=True, timeout=30)
    ffmpeg = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-version'],
                            check=True, capture_output=True, text=True, timeout=30)

    # Use the real Windows Qt platform plugin, not the offscreen substitute.
    os.environ.pop('QT_QPA_PLATFORM', None)
    from PySide6 import QtCore, QtWidgets
    from atp_studio.gui import MainWindow
    from atp_studio.theme import install_fonts
    from atp_studio import __version__
    assert __version__ == manifest['app_version']
    app = QtWidgets.QApplication([])
    install_fonts(app)
    assert app.platformName() == 'windows'
    window = MainWindow()
    window.show()
    assert window.processing.movie.isValid() and window.processing.movie.frameCount() == 6
    window.processing.start()
    app.processEvents()
    assert window.isVisible() and window.stack.count() == 4
    report_path.parent.mkdir(parents=True, exist_ok=True)
    assert window.grab().save(str(report_path.with_suffix('.png')))
    QtCore.QTimer.singleShot(500, app.quit)
    assert app.exec() == 0
    window.processing.stop()
    window.close()
    report = {'app_version': __version__, 'platform': sys.platform,
              'verified_file_count': len(actual), 'max_extracted_path_units': max_path,
              'qt_platform': app.platformName(), 'native_gui_created': True,
              'tiff_hdf5_png_scipy_checked': True,
              'java': java.stderr.splitlines()[0], 'ffmpeg': ffmpeg.stdout.splitlines()[0]}
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
