"""Desktop entry point: keep startup failures visible when no console is attached."""
import atexit
import os
from pathlib import Path
import sys
import tempfile
import traceback


def log_path():
    base = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'Library/Logs' if sys.platform == 'darwin' else Path.home() / '.local/state'))
    folder = base / 'ATP ROA Studio'
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        folder = Path(tempfile.gettempdir())
    return folder / 'startup.log'


def run():
    path = log_path()
    stream = path.open('a', encoding='utf-8', buffering=1)
    atexit.register(stream.close)
    if sys.stdout is None or os.environ.get('ATP_STUDIO_DESKTOP') == '1':
        sys.stdout = stream
    if sys.stderr is None or os.environ.get('ATP_STUDIO_DESKTOP') == '1':
        sys.stderr = stream
    try:
        from atp_studio.gui import main
        main()
    except Exception:
        traceback.print_exc(file=stream)
        stream.flush()
        message = 'The application could not start. / 起動できませんでした。\n\nDetails / 詳細:\n' + str(path)
        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, 'ATP ROA Studio', 0x10)
        elif sys.platform == 'darwin':
            import subprocess
            subprocess.run(['/usr/bin/osascript', '-e', 'on run argv\ndisplay alert "ATP ROA Studio" message (item 1 of argv) as critical\nend run', '--', message], check=False)
        else:
            print(message, file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    run()
