"""Uso: python build.py remote.midominio.com [https://usuario.github.io/repo]
Genera dist/PCRemote.exe (con el dominio dentro) y dist/pcremote-server.zip (para el VPS)."""
import os, subprocess, sys, zipfile
from PIL import Image

domain = sys.argv[1].replace("https://", "").replace("wss://", "").strip("/")
web = sys.argv[2].strip("/") if len(sys.argv) > 2 else ""  # p. ej. https://mogollo7.github.io/remote
root = os.path.dirname(os.path.abspath(__file__))
os.chdir(root)
os.makedirs("dist", exist_ok=True)

# iconos desde el gato 512
im = Image.open("assets/icono-gato-512.png").convert("RGBA")
im.save("assets/icono.ico", sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])
for s in (192, 512):
    im.resize((s, s), Image.LANCZOS).save(f"relay/web/icon-{s}.png")
im.resize((192, 192), Image.LANCZOS).save("relay/web/icon-192.webp", quality=90, method=6)
os.makedirs("build", exist_ok=True)
im.resize((128, 128), Image.LANCZOS).save("build/gato-128.png")  # el instalador usa Tk puro (sin webp)

# ejecutable
open("agent/_server.py", "w").write(f'SERVER = "wss://{domain}"\nWEB = "{web}"\n')
A = lambda p: os.path.join(root, p)
pyi = lambda *a: subprocess.check_call([sys.executable, "-m", "PyInstaller", "--onefile", "--noconsole", "--clean",
                                        "--icon", A("assets/icono.ico"), "--distpath", A("dist"),
                                        "--workpath", A("build"), "--specpath", A("build"), *a])
pyi("--name", "PCRemote", "--paths", A("agent"), "--add-data", f"{A('assets/icono-gato.webp')};.",
    "--add-data", f"{A('assets/gato-base.webp')};.", "--hidden-import", "PIL._tkinter_finder", A("agent/gui.py"))
# instalador: lleva dentro PCRemote.exe y el gato
pyi("--name", "PCRemote-Setup", "--add-data", f"{A('dist/PCRemote.exe')};.",
    "--add-data", f"{A('build/gato-128.png')};.", A("installer/setup.py"))
# descargas que sirve el relay (el .apk, si existe en dist/, también)
import shutil
os.makedirs("relay/web/downloads", exist_ok=True)
for f in ("PCRemote-Setup.exe", "PCRemote.apk"):
    if os.path.exists(f"dist/{f}"):
        shutil.copy(f"dist/{f}", "relay/web/downloads")
# servidor
with zipfile.ZipFile("dist/pcremote-server.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in ["relay.py", "requirements.txt", "pcremote-relay.service", "Caddyfile", "CONFIGURACION.md"]:
        z.write(f"relay/{f}", f)
    for d, _, fs in os.walk("relay/web"):
        for f in fs:
            p = os.path.join(d, f)
            z.write(p, os.path.relpath(p, "relay"))

print("LISTO: dist/PCRemote-Setup.exe, dist/PCRemote.exe y dist/pcremote-server.zip")
