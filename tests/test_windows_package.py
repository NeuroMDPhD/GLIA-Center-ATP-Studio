"""Regression coverage for Explorer error 0x80010135 in the release ZIP."""
import pytest
from scripts.package_windows import ARCHIVE_ROOT, shipped_path, check_archive_paths


def test_reported_qml_object_is_excluded_but_runtime_and_licenses_remain():
    prefix = 'python/Lib/site-packages/PySide6/'
    for config in ('Debug', 'RelWithDebInfo'):
        assert not shipped_path(prefix + 'qml/Qt/labs/assetdownloader/objects-' + config
                                + '/QmlAssetDownloaderPrivate_resources_1/.qt/rcc/'
                                + 'qrc_qmake_Qt_labs_assetdownloader_init.cpp.obj')
    for path in ('QtWidgets.pyd', 'Qt6Widgets.dll', 'Qt6Core.dll', 'Qt6Gui.dll',
                 'plugins/platforms/qwindows.dll', 'plugins/imageformats/qjpeg.dll'):
        assert shipped_path(prefix + path)
    assert shipped_path('python/Lib/site-packages/pyside6_essentials-6.12.0.dist-info/licenses/LICENSES.json')
    assert shipped_path('runtime/jre/bin/java.exe')
    assert shipped_path('runtime/java-libs/atp-aqua2-engine.jar')


def test_path_budget_rejects_long_paths_and_counts_utf16_units():
    base = ARCHIVE_ROOT + '/'
    assert check_archive_paths([base + 'a' * (140 - len(base))])['max_archive_path_units'] == 140
    with pytest.raises(ValueError, match='exceeds'):
        check_archive_paths([base + 'a' * (141 - len(base))])
    # Windows counts a character outside the BMP as two UTF-16 code units.
    with pytest.raises(ValueError, match='exceeds'):
        check_archive_paths([base + '\U0001f52c' * 66])


def test_short_root_leaves_space_for_a_typical_japanese_onedrive_destination():
    longest = (ARCHIVE_ROOT + '/python/Lib/site-packages/pyqtgraph/colors/maps/'
               'CC0 legal code - applies to virids, magma, plasma, inferno and cividis.txt')
    assert check_archive_paths([longest])['max_archive_path_units'] == 130
    destination = ('C:\\Users\\研究者\\OneDrive - University of Yamanashi\\Desktop\\'
                   'GLIA-Center-ATP-Studio-Windows-x64\\')
    assert len((destination + longest).encode('utf-16-le')) // 2 < 260
    assert not shipped_path('atp_studio/__pycache__/gui.cpython-312.pyc')


def test_archive_paths_must_stay_under_the_short_root():
    for name in ('/GLIA-ATP/launch.py', 'GLIA-ATP/../launch.py', 'old-long-root/launch.py'):
        with pytest.raises(ValueError, match='Unexpected'):
            check_archive_paths([name])
