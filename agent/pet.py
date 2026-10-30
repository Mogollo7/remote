"""Mascota flotante (diseño de Figma): gato con ojos que siguen al mouse, se duerme sin actividad,
clic = ventana principal, clic derecho / mantener = menú de apps con iconos filtrados."""
import ctypes, math, os, random, subprocess, sys, time, tkinter as tk
import psutil
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps, ImageTk

INK, PAPER, PANEL, ORG, MUT, GRN = "#111111", "#E9E9E4", "#F5F5F1", "#FF5F1F", "#6B6B66", "#2DBE6C"
KEY = "#010203"  # color que Windows deja transparente
WIN, BASE_PX = 96, 72  # ventana y tamaño de la mascota
K, OX, OY = 0.72, 135 - 135 * 0.72, 135 - 135 * 0.72 + 10  # el gato dentro del disco (espacio de 270 px)
SLEEP_AFTER = 60
mono = lambda n, b=False: ("Consolas", n, "bold" if b else "normal")
head = ("Bahnschrift SemiBold", 12)
rgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def work_area():
    r = (ctypes.c_long * 4)()
    if os.name == "nt" and ctypes.windll.user32.SystemParametersInfoW(48, 0, r, 0):
        return tuple(r)  # izq, arr, der, aba (sin la barra de tareas)
    return (0, 0, 1280, 720)


# ---------- imágenes
def cat_image(base_png, d):
    """Disco de papel con el gato (sin ojos) dentro, sobre el color transparente. d = lado en px."""
    big = 4 * d
    with Image.open(base_png) as src:
        cat = src.convert("RGB").resize((int(big * K), int(big * K)), Image.LANCZOS)
    bgc = cat.getpixel((1, 1))  # mismo color que el fondo del gato: así no se ve un cuadrado dentro del círculo
    disc = Image.new("L", (big, big), 0)
    ImageDraw.Draw(disc).ellipse((2, 2, big - 3, big - 3), fill=255)
    img = Image.new("RGB", (big, big), bgc)
    img.paste(cat, (int(big * OX / 270), int(big * OY / 270)))
    ImageDraw.Draw(img).ellipse((2, 2, big - 3, big - 3), outline=rgb(INK), width=max(2, big // 40))
    out = Image.new("RGB", (big, big), rgb(KEY))
    out.paste(img, mask=disc)
    return out.resize((d, d), Image.LANCZOS)


def tile(letter, size):
    im = Image.new("RGB", (size, size), rgb(ORG))
    try:
        f = ImageFont.truetype("arialbd.ttf", int(size * .55))
    except OSError:
        f = ImageFont.load_default()
    ImageDraw.Draw(im).text((size / 2, size / 2), letter.upper(), fill=rgb(INK), font=f, anchor="mm")
    return im


def filtered(orig, running):
    """Filtro propio: grises, duotono naranja al 55%, scanlines cada 4 px al 12%, marco de 2 px."""
    size = orig.size[0]
    g = ImageOps.autocontrast(ImageOps.grayscale(orig), cutoff=2).convert("RGB")
    f = Image.blend(g, ImageChops.multiply(g, Image.new("RGB", g.size, rgb(ORG))), .55)
    m = Image.new("L", g.size, 0)
    d = ImageDraw.Draw(m)
    for y in range(3, size, 4):
        d.line((0, y, size, y), fill=31)
    f = Image.composite(Image.new("RGB", g.size, rgb(INK)), f, m)
    for im in (f, orig):
        dr = ImageDraw.Draw(im)
        if im is f:
            dr.rectangle((0, 0, size - 1, size - 1), outline=rgb(INK), width=2)
        if running:
            dr.ellipse((size - 11, 2, size - 3, 10), fill=rgb(GRN), outline=rgb(INK))
    return f, orig


class Pet:
    def __init__(s, root, agent, base, show_main):
        s.root, s.agent, s.show_main, s.base = root, agent, show_main, base
        s.win = tk.Toplevel(root)
        s.win.overrideredirect(True)
        s.win.attributes("-topmost", True)
        s.win.configure(bg=KEY)
        s.win.attributes("-transparentcolor", KEY)
        s.cv = tk.Canvas(s.win, width=WIN, height=WIN, bg=KEY, highlightthickness=0, cursor="hand2")
        s.cv.pack()
        s.imgs = {sc: ImageTk.PhotoImage(cat_image(os.path.join(base, "gato-base.webp"), int(BASE_PX * sc))) for sc in (1.0, 1.08)}
        s.small = ImageTk.PhotoImage(cat_image(os.path.join(base, "gato-base.webp"), 28))
        s.last_act = time.time()
        s.last_phones, s.last_cmd_seen = 0, 0
        s.next_blink, s.blink_until = time.time() + 5, 0
        s.sig, s.menu, s.menu_leave, s.press = None, None, None, None
        s.hidden_until = 0
        s.icons = {}  # nombre -> (filtrado, original) ya como PhotoImage
        a = agent.cfg.get("pet")
        L, T, R, B = work_area()
        s.x, s.y = (a["x"], a["y"]) if a else (R - WIN - 12, B - WIN - 4)
        s.place()
        s.cv.bind("<ButtonPress-1>", s.on_press)
        s.cv.bind("<B1-Motion>", s.on_drag)
        s.cv.bind("<ButtonRelease-1>", s.on_release)
        s.cv.bind("<Button-3>", lambda e: s.open_menu())
        s.prefetch()
        s.tick()

    # ---------- posición
    def place(s):
        L, T, R, B = work_area()
        s.x = max(L, min(s.x, R - WIN))
        s.y = max(T, min(s.y, B - WIN))
        s.win.geometry(f"{WIN}x{WIN}+{int(s.x)}+{int(s.y)}")

    def snap(s):
        L, T, R, B = work_area()
        s.x = L + 12 if s.x + WIN / 2 < (L + R) / 2 else R - WIN - 12
        s.y = T + 8 if s.y + WIN / 2 < (T + B) / 2 else B - WIN - 4
        s.place()
        s.agent.cfg["pet"] = {"x": int(s.x), "y": int(s.y)}
        s.agent.save()

    # ---------- ratón: clic, arrastrar, mantener
    def on_press(s, e):
        s.press = (e.x_root, e.y_root, s.x, s.y, False)
        s.hold = s.win.after(500, lambda: (setattr(s, "press", None), s.open_menu()))
        s.wake()

    def on_drag(s, e):
        if not s.press:
            return
        x0, y0, wx, wy, moved = s.press
        if moved or abs(e.x_root - x0) + abs(e.y_root - y0) > 4:
            s.win.after_cancel(s.hold)
            s.press = (x0, y0, wx, wy, True)
            s.x, s.y = wx + e.x_root - x0, wy + e.y_root - y0
            s.place()

    def on_release(s, e):
        if not s.press:
            return
        s.win.after_cancel(s.hold)
        moved = s.press[4]
        s.press = None
        if moved:
            s.snap()
        elif (s.agent.state.get("alert") or (0, 0))[1] > time.time():
            subprocess.Popen(["shutdown", "/a"], creationflags=0x08000000)  # clic en alerta = cancelar
            s.agent.state["alert"] = None
        else:
            s.show_main()

    def wake(s):
        s.last_act = time.time()

    # ---------- dibujo
    def hover(s):
        px, py = s.win.winfo_pointerxy()
        return s.x - 4 <= px <= s.x + WIN + 4 and s.y - 4 <= py <= s.y + WIN + 4

    def tick(s):
        now, st = time.time(), s.agent.state
        if s.hidden_until:
            if now < s.hidden_until:
                s.win.after(5000, s.tick)
                return
            s.hidden_until = 0
            s.win.deiconify()
        hov = s.hover()
        if hov or s.menu or st["phones"] != s.last_phones or st.get("last_cmd", 0) > s.last_cmd_seen or (st.get("alert") or (0, 0))[1] > now:
            s.wake()
        s.last_phones, s.last_cmd_seen = st["phones"], max(s.last_cmd_seen, st.get("last_cmd", 0))
        asleep = now - s.last_act > SLEEP_AFTER
        alert = (st.get("alert") or (0, 0))[1] > now
        px, py = s.win.winfo_pointerxy()
        vx, vy = px - (s.x + WIN / 2), py - (s.y + WIN / 2)
        dist = math.hypot(vx, vy)
        look = (0, 0)
        if not asleep and 0 < dist < 600:
            m = min(dist / 300, 1)
            look = (round(vx / dist * m * 9), round(vy / dist * m * 8))
        if now > s.next_blink:
            s.blink_until, s.next_blink = now + .12, now + random.uniform(4, 6)
        if not st["online"]:
            expr = "SIN CONEXION"
        elif alert:
            expr = "ALERTA"
        elif now - st.get("last_cmd", 0) < 1.5:
            expr = "FELIZ"
        elif asleep:
            expr = "DORMIDO"
        elif now < s.blink_until:
            expr = "PARPADEO"
        else:
            expr = "NEUTRO"
        blink_on = alert and int(now * 4) % 2 == 0
        sig = (expr, look, st["phones"], asleep, hov, alert, blink_on)
        if sig != s.sig:
            s.sig = sig
            s.draw(expr, look, st["phones"], asleep, hov, alert, blink_on)
        # 20 fps solo si el mouse está cerca y despierta; si no, se revisa pocas veces (menos CPU)
        s.win.after(500 if asleep else 50 if dist < 600 or hov else 300, s.tick)

    def P(s, vx, vy):  # coordenada del visor (espacio 270) -> píxel del lienzo
        return (s.c0 + (OX + (63 + vx) * K) * s.u, s.c0 + (OY + (86 + vy) * K) * s.u)

    def pill(s, x, y, w, h, dx, dy):
        x1, y1 = s.P(x + dx, y + dy)
        x2, y2 = s.P(x + dx + w, y + dy + h)
        if h >= w:
            c, r = (x1 + x2) / 2, (x2 - x1) / 2
            s.cv.create_line(c, y1 + r, c, y2 - r, width=max(2, x2 - x1), capstyle="round", fill="white", tags="eye")
        else:
            c, r = (y1 + y2) / 2, (y2 - y1) / 2
            s.cv.create_line(x1 + r, c, x2 - r, c, width=max(2, y2 - y1), capstyle="round", fill="white", tags="eye")

    def draw(s, expr, look, phones, asleep, hov, alert, blink_on):
        sc = 1.08 if hov else 1.0
        d = int(BASE_PX * sc)
        s.u, s.c0 = d / 270, WIN / 2 - d / 2
        cv = s.cv
        cv.delete("all")
        if alert and blink_on or (phones and not asleep and expr != "SIN CONEXION"):
            cv.create_oval(5, 5, WIN - 5, WIN - 5, outline=ORG, width=4 if alert else 3)
        cv.create_image(WIN / 2, WIN / 2, image=s.imgs[sc])
        dx, dy = look
        dx, dy = dx / 1.0, dy / 1.0
        if expr in ("NEUTRO", "MIRA"):
            s.pill(39, 24, 15, 40, dx, dy)
            s.pill(88, 24, 15, 40, dx, dy)
        elif expr == "ALERTA":
            s.pill(36, 17, 21, 54, 0, 0)
            s.pill(85, 17, 21, 54, 0, 0)
        elif expr == "PARPADEO":
            s.pill(36, 41, 21, 7, 0, 0)
            s.pill(85, 41, 21, 7, 0, 0)
        elif expr in ("FELIZ", "DORMIDO"):
            pts = [(0, 14), (9, 0), (18, 14)] if expr == "FELIZ" else [(0, 0), (9, 8), (18, 0)]
            oy = 30 if expr == "FELIZ" else 40
            for ox in (36, 88):
                xy = [c for px, py in pts for c in s.P(ox + px, oy + py)]
                cv.create_line(*xy, smooth=True, width=max(2, 6 * K * s.u), capstyle="round", fill="white")
        elif expr == "SIN CONEXION":
            for ox in (36, 88):
                cv.create_line(*s.P(ox, 36), *s.P(ox + 18, 54), width=2, capstyle="round", fill="white")
                cv.create_line(*s.P(ox + 18, 36), *s.P(ox, 54), width=2, capstyle="round", fill="white")
        if phones:
            cv.create_rectangle(70, 2, 94, 18, fill=INK, outline="")
            cv.create_text(82, 10, text=str(phones), fill=PAPER, font=mono(9, True))
        if asleep:
            cv.create_text(80, 12, text="z z", fill=ORG, font=mono(9, True))
        s.win.attributes("-alpha", .55 if asleep else 1.0)

    # ---------- iconos de las apps
    def icon_path(s, app):
        d = os.path.join(s.agent.HOME, "icons")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "".join(c for c in app["name"] if c.isalnum()) + ".png")

    def prefetch(s):
        import threading

        def work():
            for a in list(s.agent.cfg["apps"]):
                p = s.icon_path(a)
                if not os.path.exists(p) and os.path.exists(a["path"]):
                    ps = ("Add-Type -AssemblyName System.Drawing;[System.Drawing.Icon]::ExtractAssociatedIcon('%s').ToBitmap().Save('%s')"
                          % (a["path"].replace("'", "''"), p.replace("'", "''")))
                    subprocess.run(["powershell", "-NoProfile", "-Command", ps], creationflags=0x08000000, timeout=20)
        threading.Thread(target=work, daemon=True).start()

    def app_icons(s, app, running):
        p = s.icon_path(app)
        try:
            orig = Image.open(p).convert("RGBA")
            bg = Image.new("RGBA", orig.size, rgb(PANEL) + (255,))
            bg.alpha_composite(orig)
            orig = bg.convert("RGB").resize((36, 36), Image.LANCZOS)
        except (OSError, ValueError):
            orig = tile(app["name"][:1], 36)
        f, o = filtered(orig, running)
        return ImageTk.PhotoImage(f), ImageTk.PhotoImage(o)

    # ---------- menú
    def close_menu(s, *_):
        if s.menu:
            s.menu.destroy()
            s.menu = None

    def open_menu(s):
        if s.menu:
            return s.close_menu()
        s.wake()
        s.prefetch()
        ag = s.agent
        run = {os.path.basename(p.info["exe"] or "").lower() for p in psutil.process_iter(["exe"])}
        m = s.menu = tk.Toplevel(s.root)
        m.overrideredirect(True)
        m.attributes("-topmost", True)
        m.configure(bg=INK)
        body = tk.Frame(m, bg=PANEL)
        body.pack(fill="both", expand=True, padx=2, pady=2)
        hd = tk.Frame(body, bg=INK)
        hd.pack(fill="x")
        tk.Label(hd, image=s.small, bg=INK).pack(side="left", padx=(16, 10), pady=10)
        tk.Label(hd, text="PC REMOTE", font=head, bg=INK, fg=PAPER).pack(side="left")
        on = ag.state["online"]
        tk.Label(hd, text="● EN LÍNEA" if on else "○ SIN CONEXIÓN", font=mono(9, True), bg=INK, fg=GRN if on else ORG).pack(side="right", padx=16)

        def sec(t):
            tk.Label(body, text=t, font=mono(9), bg=PANEL, fg=MUT, anchor="w").pack(fill="x", padx=16, pady=(12, 4))

        def row(text, cmd, img=None, hov_img=None, right=""):
            r = tk.Frame(body, bg=PANEL, cursor="hand2", width=326)
            r.pack(fill="x")
            kids = []
            if img:
                lb = tk.Label(r, image=img, bg=PANEL)
                lb.pack(side="left", padx=(16, 12), pady=6)
                kids.append(lb)
            t = tk.Label(r, text=text, font=mono(11, True), bg=PANEL, fg=INK, anchor="w")
            t.pack(side="left", padx=(0 if img else 16, 0), pady=8)
            rt = tk.Label(r, text="", font=mono(9), bg=PANEL, fg=INK)
            rt.pack(side="right", padx=16)
            kids += [t, rt]

            def enter(_):
                for w in [r] + kids:
                    w.config(bg=ORG)
                rt.config(text=right or "")
                if hov_img:
                    kids[0].config(image=hov_img)

            def leave(_):
                for w in [r] + kids:
                    w.config(bg=PANEL)
                rt.config(text="")
                if hov_img:
                    kids[0].config(image=img)
            for w in [r] + kids:
                w.bind("<Enter>", enter)
                w.bind("<Leave>", leave)
                w.bind("<Button-1>", lambda e: (s.close_menu(), cmd()))

        sec("/// APPS")
        s.keep = []
        if not ag.cfg["apps"]:
            tk.Label(body, text="Añade apps en APLICACIONES.", font=mono(10), bg=PANEL, fg=MUT).pack(anchor="w", padx=16, pady=6)
        for a in ag.cfg["apps"]:
            f, o = s.app_icons(a, ag.pname(a) in run)
            s.keep += [f, o]
            row(a["name"].upper(), lambda a=a: ag.handle({"a": "open", "app": a["name"]}), f, o, "ABRIR >")
        sec("/// PC")
        row(f"CELULARES · {ag.state['phones']} CONECTADO", lambda: s.show_main("CELULARES"), right=">")
        row("ABRIR VENTANA", s.show_main)
        row("PAUSAR 1 HORA", s.pause)
        row("SALIR", s.quit)
        tk.Frame(body, bg=PANEL, height=8).pack()
        m.update_idletasks()
        w, h = 330, m.winfo_reqheight()
        L, T, R, B = work_area()
        x = max(L, min(s.x + WIN - w - 6, R - w))
        y = s.y - h - 4 if s.y - h - 4 > T else s.y + WIN + 4
        m.geometry(f"{w}x{h}+{int(x)}+{int(y)}")
        m.focus_force()
        m.bind("<Escape>", s.close_menu)
        m.bind("<FocusOut>", lambda e: s.win.after(150, s.close_menu) if s.menu is m else None)

    def pause(s):
        s.hidden_until = time.time() + 3600
        s.win.withdraw()

    def quit(s):
        s.root.destroy()
        os._exit(0)


inst = None


def start(root, agent, base, show_main):
    global inst
    inst = Pet(root, agent, base, show_main)
    return inst
