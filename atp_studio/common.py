from __future__ import annotations
import csv, hashlib, json, os, queue, shutil, subprocess, sys, threading, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ENGINE_COMMIT = 'ca807872077a736e906698047bd718ce54754eda'

class Cancelled(Exception): pass

def clean(x):
    if isinstance(x, dict): return {str(k): clean(v) for k,v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)): return [clean(v) for v in x]
    if isinstance(x, np.generic): return clean(x.item())
    if isinstance(x, float) and not np.isfinite(x): return None
    if isinstance(x, Path): return str(x)
    return x

def stamp(): return datetime.now(timezone.utc).isoformat()

def save_json(path, data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(clean(data), ensure_ascii=False, indent=2, allow_nan=False),encoding='utf-8')
    os.replace(tmp,path)

def read_json(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''): h.update(block)
    return h.hexdigest()

def write_csv(path, rows, fields=None):
    rows=list(rows)
    fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows:
            row=clean(r)
            for k,v in row.items():
                if isinstance(v,(dict,list)): row[k]=json.dumps(v,ensure_ascii=False)
                # Keep user-entered metadata literal when opening in Excel.
                elif isinstance(v,str) and v.startswith(('=','+','-','@')): row[k]="'"+v
            w.writerow(row)

def java_executable():
    name='java.exe' if os.name=='nt' else 'java'
    candidates=[ROOT/'runtime/jre/bin'/name, ROOT/'runtime/jre/Contents/Home/bin'/name]
    if os.getenv('JAVA_HOME'): candidates.append(Path(os.environ['JAVA_HOME'])/'bin'/name)
    candidates.append(Path(shutil.which('java') or 'missing'))
    for p in candidates:
        if p.is_file(): return str(p)
    raise RuntimeError('Java was not found. Check runtime/jre. / Javaが見つかりません。runtime/jreを確認してください。')

def java_command(main, memory=4):
    return [java_executable(),f'-Xmx{int(memory)}g','-Djava.awt.headless=true','-Dfile.encoding=UTF-8',
            '-cp',str(ROOT/'runtime/java-libs/*'),main]

class Job:
    def __init__(self, notify=None):
        self.cancel=threading.Event(); self.notify=notify or (lambda msg:None)
    def check(self):
        if self.cancel.is_set(): raise Cancelled('Cancelled; originals preserved. / 中止しました。原本は保持されています。')
    def log(self,msg): self.check(); self.notify(str(msg))
    def run(self,args,log_path=None):
        self.check(); lines=[]; q=queue.Queue()
        flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
        proc=subprocess.Popen([str(a) for a in args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              text=True,encoding='utf-8',errors='replace',creationflags=flags)
        def reader():
            for line in proc.stdout: q.put(line)
            q.put(None)
        thread=threading.Thread(target=reader,daemon=True); thread.start()
        f=open(log_path,'a',encoding='utf-8') if log_path else None
        try:
            while True:
                self.check()
                try: line=q.get(timeout=.1)
                except queue.Empty: continue
                if line is None: break
                lines.append(line)
                if f: f.write(line); f.flush()
                if line.startswith(('ATP_PHASE','ATP_FRAME')): self.log(line.strip())
            ret=proc.wait()
            if ret:
                tail=''.join(lines[-16:])
                raise RuntimeError('Engine failed. Check the log. / 解析エンジンが失敗しました。ログを確認してください。\n'+tail)
            return ''.join(lines)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait()
            if f: f.close()

def new_directory(parent,prefix):
    from uuid import uuid4
    p=Path(parent)/(prefix+'_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid4().hex[:6])
    p.mkdir(parents=True,exist_ok=False); return p
