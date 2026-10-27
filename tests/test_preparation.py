import csv
from pathlib import Path
import numpy as np
import pytest
import tifffile
from atp_studio.common import Job, Cancelled, sha256
from atp_studio.project import create_project, Project, PREPARATION_FORMATS, publish_preparation_files

@pytest.fixture
def conversion(tmp_path,monkeypatch):
    source=tmp_path/'recording.oir';source.write_bytes(b'untouched source fixture')
    movie=np.arange(40*32*40,dtype=np.uint16).reshape(40,32,40)
    metadata=dict(source_path=str(source),used_files=[str(source)],series=0,channel=1,z=0,series_count=1,channels=2,z_planes=1,
                  shape=list(movie.shape),dtype='uint16',little_endian=True,plane_times_s=[i*2 for i in range(40)],interval_s=2,pixel_x_um=.75,pixel_y_um=.75)
    settings=dict(interval_s=2,pixel_x_um=.75,pixel_y_um=.75,include_experiment=False)
    monkeypatch.setattr('atp_studio.project.java_command',lambda *args:['fake-java'])
    class Converter(Job):
        def run(self,args,log_path=None):
            assert args[1]=='convert';movie.astype('<u2').tofile(args[-1]);return ''
    return source,movie,metadata,settings,Converter

@pytest.mark.parametrize('selected',[(),('mp4',),('tif',),('csv',),('png',),('mp4','csv'),PREPARATION_FORMATS])
def test_independent_formats_same_folder_and_valid_contents(conversion,selected):
    source,movie,meta,settings,Converter=conversion;before=sha256(source)
    formats={k:k in selected for k in PREPARATION_FORMATS}
    p=Project(create_project(meta,'',{**settings,'prepare_formats':formats},Converter()))
    assert p.path.parent==source.parent and p.manifest['status']=='prepared'
    assert p.manifest['preparation']['formats']==formats
    assert np.array_equal(p.movie(),movie) and sha256(source)==before
    assert set(x.name for x in (p.path/'raw').iterdir())=={'movie.ome.tif','time_s.npy'}
    outputs=p.manifest['preparation']['files']
    assert {x['format'] for x in outputs}==set(selected)
    assert len(outputs)==sum(3 if k=='png' else 1 for k in selected)
    assert {x.name for x in source.parent.iterdir() if x.is_file()}=={source.name,*[x['name'] for x in outputs]}
    for output in outputs:
        path=source.parent/output['name'];assert path.stat().st_size>0 and sha256(path)==output['sha256']
        assert '_S1_C2_Z1' in path.name
        if output['format']=='tif':
            assert np.array_equal(tifffile.imread(path),movie)
            with tifffile.TiffFile(path) as tif:assert 'PhysicalSizeX="0.75"' in tif.ome_metadata
        if output['format']=='csv':
            with path.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
            assert len(rows)==40 and float(rows[1]['time_s'])==2
            assert float(rows[0]['mean_intensity'])==np.mean(movie[0])
        if output['format']=='png':
            from PIL import Image
            with Image.open(path) as image:image.verify()
        if output['format']=='mp4':
            import imageio.v2 as imageio
            with imageio.get_reader(path) as reader:assert reader.count_frames()==40


def test_repeat_conversion_preserves_existing_exports(conversion):
    source,movie,meta,settings,Converter=conversion
    settings['prepare_formats']={k:k=='csv' for k in PREPARATION_FORMATS}
    first=Project(create_project(meta,None,settings,Converter()))
    original=source.parent/first.manifest['preparation']['files'][0]['name'];digest=sha256(original)
    second=Project(create_project(meta,None,settings,Converter()))
    assert first.path!=second.path and sha256(original)==digest
    assert first.manifest['preparation']['files'][0]['name']!=second.manifest['preparation']['files'][0]['name']


def test_publish_collision_and_cancellation_preserve_existing_files(tmp_path):
    staging=tmp_path/'staging';staging.mkdir();source=staging/'data';source.write_bytes(b'x'*100)
    original=tmp_path/'existing.csv';original.write_text('keep this')
    files=[(source,'first.csv','csv'),(source,'existing.csv','csv')]
    with pytest.raises(FileExistsError):publish_preparation_files(files,tmp_path,Job())
    assert not (tmp_path/'first.csv').exists() and original.read_text()=='keep this'
    class CancelDuringCopy(Job):
        calls=0
        def check(self):
            self.calls+=1
            if self.calls==2:raise Cancelled('cancelled')
    with pytest.raises(Cancelled):publish_preparation_files([(source,'partial.csv','csv')],tmp_path,CancelDuringCopy())
    assert not (tmp_path/'partial.csv').exists() and original.read_text()=='keep this'


def test_custom_destination_and_optional_files_not_needed_to_reopen(conversion,tmp_path):
    import os
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6 import QtWidgets as W
    from atp_studio.gui import MainWindow
    source,movie,meta,settings,Converter=conversion
    custom=tmp_path/'chosen folder';settings['prepare_formats']=dict.fromkeys(PREPARATION_FORMATS,False)
    p=Project(create_project(meta,custom,settings,Converter()))
    assert p.path.parent==custom
    app=W.QApplication.instance() or W.QApplication([]);window=MainWindow(p.path)
    assert window.movie.shape==movie.shape and window.project.path==p.path
    assert not any(w.isChecked() for w in window.output_formats.values())
    assert window.destination.text()==str(custom)
    window.close()
