from pathlib import Path
import subprocess, os, shutil
root=Path(__file__).resolve().parents[1]
sources=list((root/'vendor/AQuA2-Fiji/src/main/java').rglob('*.java'))+list((root/'java').glob('*.java'))
classes=root/'runtime/classes'; classes.mkdir(parents=True,exist_ok=True)
subprocess.run(['javac','-encoding','UTF-8','-source','8','-target','8','-cp',str(root/'runtime/java-libs/*'),'-d',str(classes)]+[str(p) for p in sources],check=True)
for p in (root/'vendor/AQuA2-Fiji/src/main/resources').iterdir(): shutil.copy2(p,classes/p.name)
subprocess.run(['jar','cf',str(root/'runtime/java-libs/atp-aqua2-engine.jar'),'-C',str(classes),'.'],check=True)
print('Built pinned AQuA2 source and adapters')
