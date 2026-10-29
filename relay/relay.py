"""Relay compartido: empareja PCs con celulares y reenvía mensajes. No interpreta comandos.
Correr detrás de un proxy TLS (Caddy/nginx -> 127.0.0.1:8080)."""
import hashlib, json, os, secrets, time
from aiohttp import web, WSMsgType

DB = os.environ.get("RELAY_DB", "relay.json")
os.makedirs(os.path.dirname(os.path.abspath(DB)), exist_ok=True)
db = json.load(open(DB)) if os.path.exists(DB) else {"pcs": {}, "phones": {}}
for _k, _v in db["phones"].items():  # formato viejo: solo el id del PC
    if isinstance(_v, str):
        db["phones"][_k] = {"pc": _v, "name": "Celular", "seen": 0}
h = lambda s: hashlib.sha256(s.encode()).hexdigest()
save = lambda: json.dump(db, open(DB, "w"))
codes, pc_ws, phone_ws, tries = {}, {}, {}, {}  # codigo->(pc,exp), pc->ws, pc->{ws}, ip->[t]


async def to_phones(pc, msg):
    for w in list(phone_ws.get(pc, ())):
        try:
            await w.send_json(msg)
        except ConnectionError:
            pass


def phones_of(pc):  # celulares emparejados de un PC: {hash: {"pc","name","seen"}}
    return {k: v for k, v in db["phones"].items() if v["pc"] == pc}


async def tell_pc(pc):  # el PC muestra los celulares emparejados y cuáles están conectados
    if pc in pc_ws:
        live = set(phone_ws.get(pc, {}).values())
        lst = [{"id": k[:12], "name": v["name"], "online": k in live, "seen": v["seen"]} for k, v in phones_of(pc).items()]
        await pc_ws[pc].send_json({"t": "phones", "n": len(live), "list": lst})


async def forget(pc, pid):
    for k in [k for k in phones_of(pc) if k[:12] == pid]:
        del db["phones"][k]
        for w in [w for w, i in phone_ws.get(pc, {}).items() if i == k]:
            await w.send_json({"t": "forgotten"})
            await w.close()
    save()
    await tell_pc(pc)


async def ws_pc(req):
    ws = web.WebSocketResponse(heartbeat=25, max_msg_size=65536)
    await ws.prepare(req)
    pc = None
    async for m in ws:
        if m.type != WSMsgType.TEXT:
            continue
        d = json.loads(m.data)
        if pc is None:
            if d.get("t") != "hello":
                break
            known = db["pcs"].get(d.get("id"))
            if known and known["secret"] == h(d.get("secret", "")):
                pc = d["id"]
            elif not d.get("id"):
                pc, sec = secrets.token_hex(8), secrets.token_urlsafe(24)
                db["pcs"][pc] = {"secret": h(sec), "name": "PC"}
                await ws.send_json({"t": "welcome", "id": pc, "secret": sec})
            else:
                await ws.send_json({"t": "error", "e": "auth"})
                break
            db["pcs"][pc]["name"] = str(d.get("name", "PC"))[:40]
            save()
            if pc_ws.get(pc) not in (None, ws):
                await pc_ws[pc].close()
            pc_ws[pc] = ws
            await to_phones(pc, {"t": "presence", "online": True})
            await tell_pc(pc)
        elif d.get("t") == "forget":
            await forget(pc, str(d.get("id")))
        elif d.get("t") == "code":
            code = f"{secrets.randbelow(10**6):06d}"
            codes[code] = (pc, time.time() + 600)
            await ws.send_json({"t": "code", "code": code, "ttl": 600})
        else:
            await to_phones(pc, d)
    if pc and pc_ws.get(pc) is ws:
        del pc_ws[pc]
        await to_phones(pc, {"t": "presence", "online": False})
    return ws


async def pair(req):
    # ponytail: X-Forwarded-For solo es fiable detrás de nuestro proxy
    ip = req.headers.get("X-Forwarded-For", req.remote).split(",")[0].strip()
    now = time.time()
    t = [x for x in tries.get(ip, []) if now - x < 60]
    if len(t) >= 5:
        return web.json_response({"e": "rate"}, status=429)
    tries[ip] = t + [now]
    try:
        body = await req.json()
        code = str(body.get("code"))
    except Exception:
        return web.json_response({"e": "bad"}, status=400)
    c = codes.pop(code, None)
    if not c or c[1] < now:
        return web.json_response({"e": "code"}, status=400)
    tok = secrets.token_urlsafe(32)
    name = str(body.get("name") or "Celular")[:40]
    db["phones"][h(tok)] = {"pc": c[0], "name": name, "seen": int(now)}
    save()
    return web.json_response({"token": tok, "name": db["pcs"][c[0]]["name"], "online": c[0] in pc_ws})


async def ws_phone(req):
    ph = h(req.query.get("token", ""))
    pc = db["phones"].get(ph, {}).get("pc")
    if not pc:
        return web.Response(status=401)
    db["phones"][ph]["seen"] = int(time.time())
    ws = web.WebSocketResponse(heartbeat=25, max_msg_size=65536)
    await ws.prepare(req)
    phone_ws.setdefault(pc, {})[ws] = ph
    await tell_pc(pc)
    await ws.send_json({"t": "presence", "online": pc in pc_ws, "name": db["pcs"][pc]["name"]})
    async for m in ws:
        if m.type == WSMsgType.TEXT and pc in pc_ws:
            await pc_ws[pc].send_str(m.data)
    phone_ws[pc].pop(ws, None)
    await tell_pc(pc)
    return ws


WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")  # landing + app del celular (PWA) + descargas
page = lambda *p: (lambda _: web.FileResponse(os.path.join(WEB, *p, "index.html")))
health = lambda _: web.json_response({"ok": True, "pcs_online": len(pc_ws), "phones_online": sum(map(len, phone_ws.values()))})
ORIGINS = os.environ.get("ALLOWED_ORIGINS", "https://mogollo7.github.io").split(",")  # webs que pueden usar /pair y /health


@web.middleware
async def cors(req, handler):  # la landing/app pueden vivir en GitHub Pages; este servidor solo conecta
    o = req.headers.get("Origin")
    r = web.Response() if req.method == "OPTIONS" else await handler(req)
    if o in ORIGINS:
        r.headers.update({"Access-Control-Allow-Origin": o, "Access-Control-Allow-Headers": "content-type", "Vary": "Origin"})
    return r


app = web.Application(middlewares=[cors])
app.add_routes([web.get("/ws/pc", ws_pc), web.get("/ws/phone", ws_phone), web.post("/pair", pair), web.get("/health", health), web.options("/pair", health), web.options("/health", health),
                web.get("/", page()), web.get("/app/", page("app")), web.get("/app", lambda _: web.HTTPFound("/app/"))])
app.router.add_static("/", WEB)

if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=int(os.environ.get("PORT", 8080)))
