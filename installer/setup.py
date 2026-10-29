"""Instalador/desinstalador de PC Remote (sin permisos de administrador). Se empaqueta con build.py.
Con el argumento /uninstall actúa como desinstalador (se copia a la carpeta de instalación)."""
import os, shutil, subprocess, sys, tkinter as tk, winreg
from tkinter import filedialog, messagebox

INK, PAPER, PANEL, ORG, MUT = "#111111", "#E9E9E4", "#F5F5F1", "#FF5F1F", "#6B6B66"
BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
UNINST = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PCRemote"
RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
MENU = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs", "PC Remote.lnk")
DESK = os.path.join(os.environ["USERPROFILE"], "Desktop", "PC Remote.lnk")
NOWIN = 0x08000000


def sh(*cmd):
    subprocess.run(cmd, creationflags=NOWIN, capture_output=True)


def shortcut(lnk, target):
    sh("powershell", "-NoProfile", "-Command",
       f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');$s.TargetPath='{target}';"
       f"$s.WorkingDirectory='{os.path.dirname(target)}';$s.Save()")


def install(folder, desk, auto, step):
    exe = os.path.join(folder, "PCRemote.exe")
    step(0.1, "Cerrando versión anterior…")
    sh("taskkill", "/f", "/im", "PCRemote.exe")
    os.makedirs(folder, exist_ok=True)
    step(0.35, "Copiando programa…")
    shutil.copy(os.path.join(BASE, "PCRemote.exe"), exe)
    uninst = os.path.join(folder, "Uninstall.exe")
    if getattr(sys, "frozen", False):
        shutil.copy(sys.executable, uninst)
    step(0.6, "Creando accesos directos…")
    shortcut(MENU, exe)
    if desk:
        shortcut(DESK, exe)
    step(0.8, "Registrando en Windows…")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINST) as k:
        for n, v in [("DisplayName", "PC Remote"), ("Publisher", "PC Remote"), ("InstallLocation", folder),
                     ("DisplayIcon", exe), ("UninstallString", f'"{uninst}" /uninstall')]:
            winreg.SetValueEx(k, n, 0, winreg.REG_SZ, v)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN) as k:
        if auto:
            winreg.SetValueEx(k, "PCRemote", 0, winreg.REG_SZ, f'"{exe}"')
        else:
            try:
                winreg.DeleteValue(k, "PCRemote")
            except FileNotFoundError:
                pass
    step(1, "Instalación completa")
    return exe


def uninstall():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINST) as k:
        folder = winreg.QueryValueEx(k, "InstallLocation")[0]
    sh("taskkill", "/f", "/im", "PCRemote.exe")
    for f in (MENU, DESK):
        if os.path.exists(f):
            os.remove(f)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN, 0, winreg.KEY_SET_VALUE) as k:
        try:
            winreg.DeleteValue(k, "PCRemote")
        except FileNotFoundError:
            pass
    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINST)
    # el desinstalador se está ejecutando desde esa carpeta: se borra cuando termina
    subprocess.Popen(f'cmd /c ping -n 3 127.0.0.1 >nul & rmdir /s /q "{folder}"', creationflags=NOWIN)


def window(title):
    r = tk.Tk()
    r.title(title)
    r.configure(bg=PAPER)
    r.geometry("560x420")
    r.resizable(False, False)
    return r


mono = lambda n, b=False: ("Consolas", n, "bold" if b else "normal")


def run_uninstall():
    r = window("Desinstalar PC Remote")
    r.withdraw()
    if messagebox.askyesno("Desinstalar PC Remote", "¿Quitar PC Remote de este equipo?\n(Se conservan tus apps guardadas en AppData.)"):
        try:
            uninstall()
            messagebox.showinfo("PC Remote", "Desinstalado.")
        except OSError as e:
            messagebox.showerror("PC Remote", f"No se pudo desinstalar: {e}")


def run_install():
    r = window("Instalar PC Remote")
    bar = tk.Frame(r, bg=INK)
    bar.pack(fill="x")
    tk.Label(bar, text="PC_REMOTE // SETUP V1.0", font=mono(10, True), bg=INK, fg=PAPER).pack(side="left", padx=16, pady=8)
    tk.Label(bar, text="●", font=mono(10), bg=INK, fg="#2DBE6C").pack(side="right", padx=16)

    body = tk.Frame(r, bg=PAPER)
    body.pack(fill="both", expand=True, padx=28, pady=18)
    img = tk.PhotoImage(file=os.path.join(BASE, "icono-gato-512.png")).subsample(4, 4)
    tk.Label(body, image=img, bg=PAPER).grid(row=0, column=0, rowspan=3, sticky="n", padx=(0, 18))
    tk.Label(body, text="INSTALAR\nPC REMOTE", font=("Consolas", 20, "bold"), bg=PAPER, fg=INK, justify="left").grid(row=0, column=1, sticky="w")
    tk.Label(body, text="Controla tu PC desde el celular.", font=mono(10), bg=PAPER, fg=MUT).grid(row=1, column=1, sticky="w")

    box = tk.Frame(body, bg=PANEL, highlightbackground=INK, highlightthickness=1)
    box.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 0))
    body.columnconfigure(1, weight=1)
    tk.Label(box, text=" CARPETA ", font=mono(9, True), bg=INK, fg=PAPER).pack(anchor="w", padx=12, pady=(10, 4))
    row = tk.Frame(box, bg=PANEL)
    row.pack(fill="x", padx=12)
    folder = tk.StringVar(value=r"D:\PCRemote" if os.path.exists("D:\\") else os.path.join(os.environ["LOCALAPPDATA"], "PCRemote"))
    tk.Entry(row, textvariable=folder, font=mono(11), relief="solid", bd=1).pack(side="left", fill="x", expand=True, ipady=4)
    tk.Button(row, text="EXAMINAR", font=mono(9, True), bg=PANEL, relief="solid", bd=1,
              command=lambda: folder.set((filedialog.askdirectory() or folder.get()).replace("/", "\\"))).pack(side="left", padx=(8, 0))
    desk, auto = tk.BooleanVar(value=True), tk.BooleanVar(value=True)
    for t, v in (("Crear acceso directo en el escritorio", desk), ("Iniciar con Windows", auto)):
        tk.Checkbutton(box, text=t, variable=v, font=mono(10), bg=PANEL, activebackground=PANEL, anchor="w").pack(fill="x", padx=12)
    tk.Frame(box, height=8, bg=PANEL).pack()

    msg = tk.Label(body, text="", font=mono(10, True), bg=PAPER, fg=INK, anchor="w")
    msg.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 2))
    prog = tk.Canvas(body, height=10, bg=PANEL, highlightbackground=INK, highlightthickness=1)
    prog.grid(row=5, column=0, columnspan=2, sticky="ew")
    btns = tk.Frame(body, bg=PAPER)
    btns.grid(row=6, column=0, columnspan=2, sticky="e", pady=14)
    go = tk.Button(btns, text="[ INSTALAR > ]", font=mono(11, True), bg=ORG, fg=INK, relief="solid", bd=2, padx=12, pady=4)
    go.pack(side="right")
    tk.Button(btns, text="CANCELAR", font=mono(10, True), bg=PAPER, relief="solid", bd=1, command=r.destroy, padx=8, pady=4).pack(side="right", padx=8)

    def step(p, t):
        prog.delete("all")
        prog.create_rectangle(0, 0, prog.winfo_width() * p, 10, fill=ORG, width=0)
        msg.config(text=t)
        r.update()

    def go_click():
        go.config(state="disabled")
        try:
            exe = install(folder.get(), desk.get(), auto.get(), step)
        except OSError as e:
            msg.config(text=f"Error: {e}", fg="#c00")
            go.config(state="normal")
            return
        go.config(text="[ ABRIR AHORA > ]", state="normal", command=lambda: (subprocess.Popen([exe]), r.destroy()))

    go.config(command=go_click)
    r.mainloop()


if __name__ == "__main__":
    run_uninstall() if "/uninstall" in sys.argv else run_install()
