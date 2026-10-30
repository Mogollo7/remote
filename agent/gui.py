"""Ventana del ejecutable: réplica del diseño de Figma (Estado / Aplicaciones / Ajustes)."""
import asyncio, json, os, subprocess, sys, threading, time, tkinter as tk
from tkinter import filedialog
import segno
from PIL import Image, ImageTk
import agent

INK, PAPER, PANEL, ORG, MUT, GRN = "#111111", "#E9E9E4", "#F5F5F1", "#FF5F1F", "#6B6B66", "#2DBE6C"
HEAD = ("Bahnschrift SemiBold", 20)  # ancho, parecido a Syncopate; si falta, Tk usa otra
mono = lambda n, b=False: ("Consolas", n, "bold" if b else "normal")
BASE = getattr(sys, "_MEIPASS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets"))
URL = agent.SERVER.replace("wss://", "https://").replace("ws://", "http://")
WEB = agent._WEB or URL  # donde vive la app del celular
RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
# una sola copia: dos agentes con la misma identidad se echan del servidor uno a otro (conexión intermitente)
SHOW_FLAG = os.path.join(agent.HOME, "show.flag")
if os.name == "nt":
    import ctypes
    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _mutex = _k32.CreateMutexW(None, False, r"Local\PCRemoteAgent")
    if ctypes.get_last_error() == 183:  # ya hay una abierta: le pide que muestre su ventana y se va
        open(SHOW_FLAG, "w").close()
        sys.exit(0)
if os.path.exists(SHOW_FLAG):  # aviso viejo de una corrida anterior
    os.remove(SHOW_FLAG)
threading.Thread(target=lambda: asyncio.run(agent.run()), daemon=True).start()


class CB(tk.Canvas):  # botón con esquinas cortadas
    def __init__(s, parent, text, w, h, cmd, fill=PANEL, fg=INK, fs=10):
        super().__init__(parent, width=w, height=h, bg=parent["bg"], highlightthickness=0, cursor="hand2")
        s.create_polygon(2, 2, w - 12, 2, w - 2, 12, w - 2, h - 2, 12, h - 2, 2, h - 12, fill=fill, outline=INK, width=2)
        s.create_text(w / 2, h / 2, text=text, font=mono(fs, True), fill=fg)
        s.bind("<Button-1>", lambda e: cmd())


class Toggle(tk.Canvas):
    def __init__(s, parent, on, cmd):
        super().__init__(parent, width=46, height=24, bg=parent["bg"], highlightthickness=0, cursor="hand2")
        s.on, s.cmd = on, cmd
        s.bind("<Button-1>", s.flip)
        s.draw()

    def draw(s):
        s.delete("all")
        s.create_rectangle(2, 2, 44, 22, fill=ORG if s.on else PANEL, outline=INK, width=2)
        x = 28 if s.on else 6
        s.create_rectangle(x, 6, x + 12, 18, fill=INK, width=0)

    def flip(s, _):
        s.on = not s.on
        s.draw()
        s.cmd(s.on)


def tag(p, t, bg=INK, fg=PAPER):
    return tk.Label(p, text=f" {t} ", font=mono(9, True), bg=bg, fg=fg)


def panel(p):
    return tk.Frame(p, bg=PANEL, highlightbackground=INK, highlightthickness=1)


def kv(p, k, v, last=False):
    r = tk.Frame(p, bg=PANEL)
    r.pack(fill="x", padx=14)
    tk.Label(r, text=k, font=mono(10), bg=PANEL, fg=MUT).pack(side="left", pady=8)
    lb = tk.Label(r, text=v, font=mono(11, True), bg=PANEL, fg=INK)
    lb.pack(side="right")
    if not last:
        tk.Frame(p, bg="#CFCFCB", height=1).pack(fill="x", padx=14)
    return lb


def autostart(on=None):
    if os.name != "nt":
        return False
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN) as k:
        if on is None:
            try:
                winreg.QueryValueEx(k, "PCRemote")
                return True
            except FileNotFoundError:
                return False
        if on and getattr(sys, "frozen", False):
            winreg.SetValueEx(k, "PCRemote", 0, winreg.REG_SZ, f'"{sys.executable}" --bg')
        elif not on:
            try:
                winreg.DeleteValue(k, "PCRemote")
            except FileNotFoundError:
                pass


def allow(key):
    def f(on):
        agent.cfg.setdefault("allow", {})[key] = on
        agent.save()
    return f


root = tk.Tk()
root.title("PC_REMOTE_SERVER.EXE")
root.configure(bg=PAPER)
root.geometry("960x620")
root.resizable(False, False)
with Image.open(os.path.join(BASE, "gato-icono.webp")) as _cat:  # solo los tamaños que se usan, no la de 512 px
    pic = {s: ImageTk.PhotoImage(_cat.resize((s, s), Image.LANCZOS)) for s in (40, 64, 73, 102)}
root.iconphoto(True, pic[64])

side = tk.Frame(root, bg=PANEL, width=210, highlightbackground=INK, highlightthickness=1)
side.pack(side="left", fill="y")
side.pack_propagate(False)
content = tk.Frame(root, bg=PAPER)
content.pack(side="left", fill="both", expand=True, padx=28, pady=24)

lg = tk.Frame(side, bg=PANEL)
lg.pack(fill="x", padx=16, pady=(20, 16))
small = pic[40]
tk.Label(lg, image=small, bg=PANEL).pack(side="left")
lt = tk.Frame(lg, bg=PANEL)
lt.pack(side="left", padx=8)
tk.Label(lt, text="PC REMOTE", font=("Bahnschrift SemiBold", 11), bg=PANEL, fg=INK).pack(anchor="w")
tk.Label(lt, text="SERVER v1.0", font=mono(8), bg=PANEL, fg=MUT).pack(anchor="w")

views, navs = {}, {}


def show(n):
    for k, v in views.items():
        v.pack_forget()
        navs[k].config(bg=PANEL, fg=INK)
    views[n].pack(fill="both", expand=True)
    navs[n].config(bg=INK, fg=PAPER)


for n in ("ESTADO", "APLICACIONES", "CELULARES", "AJUSTES"):
    navs[n] = tk.Label(side, text=n, font=mono(11, True), bg=PANEL, fg=INK, anchor="w", padx=20, pady=13, cursor="hand2")
    navs[n].pack(fill="x", pady=2)
    navs[n].bind("<Button-1>", lambda e, n=n: show(n))
    views[n] = tk.Frame(content, bg=PAPER)
foot = tk.Frame(side, bg=PANEL)
foot.pack(side="bottom", fill="x", padx=16, pady=14)
led = tk.Label(foot, text="●", font=mono(10), bg=PANEL, fg=ORG)
led.pack(side="left")
led_t = tk.Label(foot, text="SIN CONEXIÓN", font=mono(9, True), bg=PANEL, fg=INK)
led_t.pack(side="left", padx=6)

# ---------------- ESTADO
v = views["ESTADO"]
tk.Label(v, text="ESTADO_", font=HEAD, bg=PAPER, fg=INK).pack(anchor="w")
row = tk.Frame(v, bg=PAPER)
row.pack(fill="x", pady=18)
qp = panel(row)
qp.pack(side="left", anchor="n")
tag(qp, "ESCANEA CON EL CELULAR").pack(anchor="w", padx=14, pady=(14, 8))
qr = tk.Canvas(qp, width=220, height=220, bg="white", highlightthickness=0)
qr.pack(padx=14)
tk.Label(qp, text="O ESCRIBE EL CÓDIGO", font=mono(8), bg=PANEL, fg=MUT).pack(pady=(8, 14))
col = tk.Frame(row, bg=PAPER)
col.pack(side="left", fill="both", expand=True, padx=(20, 0))
cp = panel(col)
cp.pack(fill="x")
tag(cp, "CÓDIGO DE ACCESO · VÁLIDO 10 MIN").pack(anchor="w", padx=14, pady=(14, 4))
code = tk.Label(cp, font=("Consolas", 40, "bold"), bg=PANEL, fg=INK)
code.pack(anchor="w", padx=14)
CB(cp, "NUEVO CÓDIGO", 170, 36, agent.new_code, fs=10).pack(anchor="w", padx=14, pady=(2, 14))
up = panel(col)
up.pack(fill="x", pady=12)
tag(up, "URL DEL CELULAR").pack(anchor="w", padx=14, pady=(12, 4))
tk.Label(up, text=WEB, font=mono(12, True), bg=PANEL, fg=INK).pack(anchor="w", padx=14, pady=(0, 12))
sp = panel(col)
sp.pack(fill="x")
st_v = kv(sp, "ESTADO", "")
ph_v = kv(sp, "CELULARES CONECTADOS", "0")
kv(sp, "EQUIPO", agent.platform.node(), last=True)
tk.Label(col, image=pic[73], bg=PAPER).pack(anchor="e", pady=(8, 0))

shown = {"code": object()}


def draw_qr(text):
    qr.delete("all")
    if not text:
        qr.create_text(110, 110, text="···", font=mono(20), fill=MUT)
        return
    m = list(segno.make(f"{WEB}/app/?c={text}", error="m").matrix)
    u = 220 / (len(m) + 4)
    for y, r in enumerate(m):
        for x, b in enumerate(r):
            if b:
                qr.create_rectangle((x + 2) * u, (y + 2) * u, (x + 3) * u, (y + 3) * u, fill=INK, width=0)


# ---------------- APLICACIONES
v = views["APLICACIONES"]
hd = tk.Frame(v, bg=PAPER)
hd.pack(fill="x")
tk.Label(hd, text="APLICACIONES_", font=HEAD, bg=PAPER, fg=INK).pack(side="left")
body = tk.Frame(v, bg=PAPER)
body.pack(fill="both", expand=True, pady=16)
form = panel(body)
form.pack(side="right", anchor="n", padx=(20, 0))
lst = panel(body)
lst.pack(side="left", fill="both", expand=True, anchor="n")
tag(form, "NUEVA APP", ORG, INK).pack(anchor="w", padx=16, pady=(16, 8))
name_v, path_v = tk.StringVar(), tk.StringVar()
for t, var in (("NOMBRE", name_v), ("RUTA .EXE", path_v)):
    tag(form, t).pack(anchor="w", padx=16, pady=(6, 2))
    tk.Entry(form, textvariable=var, font=mono(11), relief="solid", bd=1, width=26).pack(padx=16, ipady=5)


def browse():
    p = filedialog.askopenfilename(filetypes=[("Programas", "*.exe"), ("Todos", "*.*")])
    if p:
        path_v.set(p.replace("/", "\\"))
        name_v.set(name_v.get() or os.path.splitext(os.path.basename(p))[0])


def save_app():
    n, p = name_v.get().strip(), path_v.get().strip()
    if n and os.path.exists(p):
        agent.cfg["apps"] = [a for a in agent.cfg["apps"] if a["name"] != n] + [{"name": n, "path": p}]
        agent.save()
        name_v.set("")
        path_v.set("")
        draw_apps()


START_APPS = r"""[Console]::OutputEncoding=[Text.Encoding]::UTF8
$pk=@{}; Get-AppxPackage | ForEach-Object { $pk[$_.PackageFamilyName]=$_.InstallLocation }
Get-StartApps | ForEach-Object { $id=$_.AppID; $exe=$null
  if ($id -match '^(.+)!(.+)$') { $loc=$pk[$matches[1]]; $aid=$matches[2]
    if ($loc) { try { [xml]$m=Get-Content (Join-Path $loc 'AppxManifest.xml')
      $x=$m.Package.Applications.Application | Where-Object Id -eq $aid; if ($x.Executable) { $exe=Split-Path $x.Executable -Leaf } } catch {} } }
  elseif ($id -like '*.exe') { $exe=Split-Path $id -Leaf }
  [pscustomobject]@{name=$_.Name; id=$id; exe=$exe} } | ConvertTo-Json -Compress"""


def pick_installed():  # lista del menú Inicio: evita elegir un .exe ayudante y sirve para apps de la Store
    w = tk.Toplevel(root, bg=PAPER)
    w.title("APPS INSTALADAS")
    w.geometry("440x540")
    w.transient(root)
    q = tk.StringVar()
    tk.Entry(w, textvariable=q, font=mono(12), relief="solid", bd=1).pack(fill="x", padx=16, pady=(16, 8), ipady=6)
    lb = tk.Listbox(w, font=mono(11), relief="solid", bd=1, activestyle="none", selectbackground=ORG, selectforeground=INK)
    lb.pack(fill="both", expand=True, padx=16)
    lb.insert("end", "Cargando apps instaladas…")
    data, shown = [], []

    def fill(*_):
        lb.delete(0, "end")
        shown[:] = [a for a in data if q.get().lower() in a["name"].lower()]
        for a in shown:
            lb.insert("end", a["name"])

    def load():
        try:
            out = subprocess.run(["powershell", "-NoProfile", "-Command", START_APPS], capture_output=True,
                                 creationflags=0x08000000, timeout=90).stdout.decode("utf-8", "replace")
            r = json.loads(out or "[]")
            data[:] = sorted([r] if isinstance(r, dict) else r, key=lambda a: a["name"].lower())
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
        root.after(0, fill)

    def add(*_):
        if lb.curselection() and shown:
            a = shown[lb.curselection()[0]]
            agent.cfg["apps"] = [x for x in agent.cfg["apps"] if x["name"] != a["name"]] +                 [{"name": a["name"], "path": agent.SHELL + a["id"], "exe": a.get("exe") or ""}]
            agent.save()
            draw_apps()
            w.destroy()
    q.trace_add("write", fill)
    lb.bind("<Double-Button-1>", add)
    CB(w, "[ AÑADIR ]", 200, 40, add, fill=ORG, fs=11).pack(pady=14)
    threading.Thread(target=load, daemon=True).start()


def drop(i):
    del agent.cfg["apps"][i]
    agent.save()
    draw_apps()


CB(form, "EXAMINAR", 222, 34, browse, fs=10).pack(padx=16, pady=(10, 4))
CB(form, "[ GUARDAR ]", 222, 42, save_app, fill=INK, fg=PAPER, fs=11).pack(padx=16, pady=(4, 16))
CB(hd, "+ AÑADIR APP", 150, 38, pick_installed, fill=ORG, fs=10).pack(side="right")
rows = tk.Frame(lst, bg=PANEL)
rows.pack(fill="both", expand=True, padx=16, pady=6)


def draw_apps():
    for w in rows.winfo_children():
        w.destroy()
    if not agent.cfg["apps"]:
        tk.Label(rows, text="Aún no hay apps.\nPulsa EXAMINAR para añadir una.", font=mono(10), bg=PANEL, fg=MUT, justify="left").pack(anchor="w", pady=16)
    for i, a in enumerate(agent.cfg["apps"]):
        r = tk.Frame(rows, bg=PANEL)
        r.pack(fill="x", pady=7)
        ic = tk.Frame(r, bg=ORG if i == 0 else PAPER, highlightbackground=INK, highlightthickness=2, width=38, height=38)
        ic.pack(side="left")
        ic.pack_propagate(False)
        tk.Label(ic, text=a["name"][0].upper(), font=("Bahnschrift SemiBold", 12), bg=ic["bg"], fg=INK).pack(expand=True)
        t = tk.Frame(r, bg=PANEL)
        t.pack(side="left", padx=12)
        tk.Label(t, text=a["name"].upper(), font=("Bahnschrift SemiBold", 11), bg=PANEL, fg=INK).pack(anchor="w")
        p = a["path"]
        bad = not p.startswith("shell:") and not os.path.exists(p)
        txt = "APP INSTALADA (MENÚ INICIO)" if p.startswith("shell:") else ("⚠ YA NO EXISTE · " if bad else "") + (p if len(p) < 46 else p[:44] + "…")
        tk.Label(t, text=txt, font=mono(9), bg=PANEL, fg=ORG if bad else MUT).pack(anchor="w")
        x = tk.Label(r, text="QUITAR", font=mono(9, True), bg=PANEL, fg=INK, cursor="hand2")
        x.pack(side="right")
        x.bind("<Button-1>", lambda e, i=i: drop(i))
        tk.Frame(rows, bg="#CFCFCB", height=1).pack(fill="x")


# ---------------- CELULARES
v = views["CELULARES"]
tk.Label(v, text="CELULARES_", font=HEAD, bg=PAPER, fg=INK).pack(anchor="w")
tk.Label(v, text="Celulares emparejados con este PC. OLVIDAR corta el acceso al instante.", font=mono(10), bg=PAPER, fg=MUT).pack(anchor="w", pady=(2, 0))
pl = panel(v)
pl.pack(fill="both", expand=True, pady=16)
prow = tk.Frame(pl, bg=PANEL)
prow.pack(fill="both", expand=True, padx=16, pady=6)
mascot = pic[102]
drawn = {"p": None}


def forget_phone(pid):
    agent.forget(pid)
    drawn["p"] = None  # se redibuja cuando el relay confirme


def draw_phones():
    lst = agent.state["plist"]
    sig = repr(lst)
    if sig == drawn["p"]:
        return
    drawn["p"] = sig
    for w in prow.winfo_children():
        w.destroy()
    if not lst:
        e = tk.Frame(prow, bg=PANEL)
        e.pack(expand=True)
        tk.Label(e, image=mascot, bg=PANEL).pack(pady=(30, 8))
        tk.Label(e, text="Ningún celular emparejado.\nEscanea el QR de ESTADO con la app.", font=mono(10), bg=PANEL, fg=MUT, justify="center").pack()
    for p in lst:
        r = tk.Frame(prow, bg=PANEL)
        r.pack(fill="x", pady=8)
        tk.Label(r, text="●", font=mono(12), bg=PANEL, fg=GRN if p["online"] else MUT).pack(side="left")
        t = tk.Frame(r, bg=PANEL)
        t.pack(side="left", padx=12)
        nm = tk.Frame(t, bg=PANEL)
        nm.pack(anchor="w")
        tk.Label(nm, text=p["name"].upper(), font=("Bahnschrift SemiBold", 11), bg=PANEL, fg=INK).pack(side="left")
        k = {"apk": ("APP ANDROID", ORG, INK), "pwa": ("PWA", INK, PAPER)}.get(p.get("kind"), ("NAVEGADOR", PAPER, INK))
        tag(nm, k[0], k[1], k[2]).pack(side="left", padx=8)
        ago = time.strftime("%d/%m %H:%M", time.localtime(p["seen"])) if p["seen"] else "—"
        tk.Label(t, text=("CONECTADO AHORA" if p["online"] else "SIN CONEXIÓN") + f" · VISTO {ago}", font=mono(9), bg=PANEL, fg=MUT).pack(anchor="w")
        CB(r, "OLVIDAR", 100, 32, lambda i=p["id"]: forget_phone(i), fill=INK, fg=PAPER, fs=9).pack(side="right")
        tk.Frame(prow, bg="#CFCFCB", height=1).pack(fill="x")


# ---------------- AJUSTES
v = views["AJUSTES"]
tk.Label(v, text="AJUSTES_", font=HEAD, bg=PAPER, fg=INK).pack(anchor="w")
op = panel(v)
op.pack(fill="x", pady=18)
A = agent.cfg.get("allow", {})
for k, d, on, cmd in (
    ("INICIAR CON WINDOWS", "Abre este programa al encender el PC", autostart(), autostart),
    ("PERMITIR APAGAR", "Desde el celular", A.get("shutdown", True), allow("shutdown")),
    ("PERMITIR REINICIAR", "Desde el celular", A.get("restart", True), allow("restart")),
    ("PERMITIR SUSPENDER Y BLOQUEAR", "Desde el celular", A.get("sleep_lock", True), allow("sleep_lock")),
    ("PERMITIR CERRAR APPS", "Solo las de tu lista, cierre normal", A.get("close", True), allow("close")),
):
    r = tk.Frame(op, bg=PANEL)
    r.pack(fill="x", padx=18, pady=10)
    t = tk.Frame(r, bg=PANEL)
    t.pack(side="left")
    tk.Label(t, text=k, font=mono(11, True), bg=PANEL, fg=INK).pack(anchor="w")
    tk.Label(t, text=d, font=mono(9), bg=PANEL, fg=MUT).pack(anchor="w")
    Toggle(r, on, cmd).pack(side="right")
    tk.Frame(op, bg="#CFCFCB", height=1).pack(fill="x", padx=18)
sv = panel(v)
sv.pack(fill="x")
tag(sv, "SERVIDOR").pack(anchor="w", padx=14, pady=(12, 4))
tk.Label(sv, text=URL, font=mono(12, True), bg=PANEL, fg=INK).pack(anchor="w", padx=14, pady=(0, 12))


def tick():
    on = agent.state["online"]
    led.config(fg=GRN if on else ORG)
    led_t.config(text="SERVIDOR ACTIVO" if on else "SIN CONEXIÓN")
    st_v.config(text="● ACTIVO" if on else "○ SIN CONEXIÓN", fg=GRN if on else ORG)
    ph_v.config(text=str(agent.state["phones"]))
    draw_phones()
    if os.path.exists(SHOW_FLAG):  # alguien abrió el programa otra vez
        os.remove(SHOW_FLAG)
        show_main()
    c = agent.state["code"]
    if c != shown["code"]:
        shown["code"] = c
        code.config(text=" ".join(c) if c else "· · · · · ·")
        draw_qr(c)
    root.after(1000, tick)


draw_apps()
show("ESTADO")
tick()
import pet  # mascota flotante: el programa sigue en segundo plano aunque cierres la ventana


def show_main(view="ESTADO"):
    root.deiconify()
    root.lift()
    root.focus_force()
    show(view if isinstance(view, str) else "ESTADO")


pet.start(root, agent, BASE, show_main)
root.protocol("WM_DELETE_WINDOW", root.withdraw)
if "--bg" in sys.argv:
    root.withdraw()
root.mainloop()
