"""Agente del PC: se conecta al relay, expone el código de emparejamiento y obedece
solo comandos de una lista fija (apps de config.json + energía + info)."""
import asyncio, json, os, platform, socket, subprocess, time, uuid
import psutil, websockets

try:
    from _server import SERVER as _BAKED  # lo escribe build.py con el dominio real
except ImportError:
    _BAKED = "wss://TU-DOMINIO.com"
try:
    from _server import WEB as _WEB  # página de la app (GitHub Pages); si falta se usa el propio servidor
except ImportError:
    _WEB = ""
HOME = os.environ.get("PCREMOTE_HOME") or os.path.join(os.environ.get("APPDATA", "."), "PCRemote")
CFG = os.path.join(HOME, "config.json")
os.makedirs(HOME, exist_ok=True)
cfg = json.load(open(CFG)) if os.path.exists(CFG) else {"apps": []}  # apps: [{"name","path"}]
SERVER = os.environ.get("PCREMOTE_SERVER") or cfg.get("server") or _BAKED  # "server" en config.json: solo para pruebas
save = lambda: json.dump(cfg, open(CFG, "w"), indent=2)
state = {"code": None, "online": False, "ws": None, "loop": None, "phones": 0, "plist": []}  # la ventana lee esto
NT = os.name == "nt"
POWER = {
    "shutdown": ["shutdown", "/s", "/t", "5"],
    "restart": ["shutdown", "/r", "/t", "5"],
    "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
    "lock": ["rundll32.exe", "user32.dll,LockWorkStation"],
}
psutil.cpu_percent()


def my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # UDP: no envía nada
        return s.getsockname()[0]
    except OSError:
        return "?"
    finally:
        s.close()


def info():
    vm, du = psutil.virtual_memory(), psutil.disk_usage(os.path.abspath(os.sep))
    mac = ":".join(f"{(uuid.getnode() >> i) & 255:02X}" for i in range(40, -1, -8))
    return {"t": "info", "host": platform.node(), "os": platform.platform(), "cpu_name": platform.processor(),
            "cpu": psutil.cpu_percent(), "ram": vm.percent, "ram_gb": round(vm.total / 2**30, 1),
            "disk": du.percent, "disk_used_gb": round(du.used / 2**30), "disk_total_gb": round(du.total / 2**30),
            "uptime": int(time.time() - psutil.boot_time()), "ip": my_ip(), "mac": mac}


def handle(d):
    a = d.get("a")
    if a not in ("info", "apps"):
        state["last_cmd"] = time.time()  # la mascota reacciona
    if a == "info":
        return info()
    if a == "apps":
        return {"t": "apps", "list": [x["name"] for x in cfg["apps"]]}
    if a == "open":
        app = next((x for x in cfg["apps"] if x["name"] == d.get("app")), None)
        if app:
            subprocess.Popen([app["path"]])
        return {"t": "ack", "a": a, "app": d.get("app"), "ok": bool(app)}
    if a in POWER and NT and cfg.get("allow", {}).get("sleep_lock" if a in ("sleep", "lock") else a, True):
        subprocess.Popen(POWER[a])
        if a in ("shutdown", "restart"):
            state["alert"] = (a, time.time() + 5)  # cuenta regresiva en la mascota
        return {"t": "ack", "a": a, "ok": True}
    return {"t": "ack", "a": a, "ok": False}


def new_code():  # lo llama la ventana (otro hilo)
    if state["ws"] and state["loop"]:
        asyncio.run_coroutine_threadsafe(state["ws"].send(json.dumps({"t": "code"})), state["loop"])


def forget(pid):  # lo llama la ventana: el relay borra el celular y lo desconecta
    if state["ws"] and state["loop"]:
        asyncio.run_coroutine_threadsafe(state["ws"].send(json.dumps({"t": "forget", "id": pid})), state["loop"])


async def push(ws):
    while True:
        await asyncio.sleep(5)
        await ws.send(json.dumps(info()))


async def run():
    state["loop"] = asyncio.get_running_loop()
    while True:
        try:
            async with websockets.connect(f"{SERVER}/ws/pc", max_size=65536) as ws:
                await ws.send(json.dumps({"t": "hello", "id": cfg.get("id"), "secret": cfg.get("secret"), "name": platform.node()}))
                await ws.send(json.dumps({"t": "code"}))
                state.update(ws=ws, online=True)
                task = asyncio.create_task(push(ws))
                try:
                    async for raw in ws:
                        d = json.loads(raw)
                        if d["t"] == "welcome":
                            cfg.update(id=d["id"], secret=d["secret"])
                            save()
                        elif d["t"] == "code":
                            state["code"] = d["code"]
                            print(f"CODIGO: {d['code']}", flush=True)
                        elif d["t"] == "phones":
                            state.update(phones=d["n"], plist=d.get("list", []))
                        elif d["t"] == "error":
                            cfg.pop("id", None)  # ponytail: PC olvidado por el servidor, se re-registra
                            save()
                        elif d["t"] == "cmd":
                            await ws.send(json.dumps(handle(d)))
                finally:
                    task.cancel()
        except (OSError, websockets.WebSocketException):
            pass
        state.update(ws=None, online=False)
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run())
