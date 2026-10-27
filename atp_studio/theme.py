"""Bundled IBM Plex fonts, available without a system font installation."""
from PySide6 import QtGui as G
from .common import ROOT


def install_fonts(app):
    if app.property('glia_fonts_loaded'):
        return
    for path in sorted((ROOT / 'assets/fonts').glob('*.ttf')):
        if G.QFontDatabase.addApplicationFont(str(path)) < 0:
            raise RuntimeError(f'Could not load bundled font: {path.name}')
    font = G.QFont('IBM Plex Sans', 10)
    font.setFamilies(['IBM Plex Sans', 'IBM Plex Sans JP'])
    app.setFont(font)
    app.setProperty('glia_fonts_loaded', True)
