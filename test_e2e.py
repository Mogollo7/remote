"""Prueba de punta a punta: relay + agente reales, celular simulado. Uso: python test_e2e.py"""
import asyncio, os, subprocess, sys, tempfile
import aiohttp

PORT = 8791
tmp = tempfile.mkdtemp()
env = {**os.environ, "PORT": str(PORT), "RELAY_DB": os.path.join(tmp, "r.json"), "PCREMOTE_HOME": tmp,
       "PCREMOTE_SERVER": f"ws://127.0.0.1:{PORT}", "PYTHONUNBUFFERED": "1"}


async def main():
    relay = subprocess.Popen([sys.executable, "relay/relay.py"], env=env)
    await asyncio.sleep(1.5)
    agent = subprocess.Popen([sys.executable, "agent/agent.py"], env=env, stdout=subprocess.PIPE, text=True)
    try:
        code = (await asyncio.get_running_loop().run_in_executor(None, agent.stdout.readline)).split()[-1]
        async with aiohttp.ClientSession() as s:
            bad = await s.post(f"http://127.0.0.1:{PORT}/pair", json={"code": "000000"})
            assert bad.status == 400, "código falso debe fallar"
            r = await (await s.post(f"http://127.0.0.1:{PORT}/pair", json={"code": code})).json()
            assert r["online"], r
            reuse = await s.post(f"http://127.0.0.1:{PORT}/pair", json={"code": code})
            assert reuse.status == 400, "el código es de un solo uso"
            noauth = await s.get(f"http://127.0.0.1:{PORT}/ws/phone?token=malo")
            assert noauth.status == 401
            async with s.ws_connect(f"http://127.0.0.1:{PORT}/ws/phone?token={r['token']}") as ws:
                assert (await ws.receive_json())["t"] == "presence"
                await ws.send_json({"t": "cmd", "a": "info"})
                msg = await ws.receive_json()
                assert msg["t"] == "info" and "cpu" in msg, msg
                await ws.send_json({"t": "cmd", "a": "open", "app": "no-existe"})
                assert (await ws.receive_json())["ok"] is False, "app fuera de la lista debe rechazarse"
        print("OK: emparejamiento, info y lista blanca funcionan")
    finally:
        agent.kill(); relay.kill()


asyncio.run(main())
