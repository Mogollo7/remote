# PC Remote

Controla tu PC con Windows desde el celular: abrir apps de una lista, apagar, reiniciar, suspender, bloquear y ver CPU/RAM/disco.

```
[PC: PCRemote.exe] --wss--> [Relay en tu VPS] <--wss-- [Celular: /app o APK]
```

Nadie abre puertos: PC y celular se conectan hacia afuera al relay, que solo reenvía mensajes.

| Carpeta | Qué es |
|---|---|
| `relay/` | Servidor (aiohttp). Sirve la landing `/`, la app móvil `/app/`, `/downloads/` y los WebSockets |
| `agent/` | Programa del PC (agente + ventana tkinter) |
| `installer/` | Instalador de Windows |
| `build.py` | Genera `dist/PCRemote-Setup.exe`, `PCRemote.exe` y `pcremote-server.zip` |
| `test_e2e.py` | Prueba de emparejamiento, info y lista blanca |

> **Antes de publicar, lee [DESPLIEGUE.md](DESPLIEGUE.md)**: qué activar y qué cambiar.

## Configuración
- **Servidor:** `relay/CONFIGURACION.md` (VPS + Caddy + systemd).
- **Compilar:** `pip install -r requirements.txt pyinstaller pillow segno` y `python build.py remote.tudominio.com`.
  Copia `dist/PCRemote.apk` (si lo tienes) antes de compilar: se publica con el instalador en `/downloads/`.
- **Usar:** instala el `.exe`, abre `https://tudominio/app/` en el celular y escribe el código.

## QA
- `python test_e2e.py` → emparejamiento, código de un solo uso, token inválido, info y lista blanca (OK).
- Pendiente: probar energía (apagar/reiniciar/suspender/bloquear) en Windows real, tráfico real con HTTPS, Wake-on-LAN (no implementado) y "olvidar celular".

## GitHub sirve la web, el servidor solo conecta
- **GitHub Pages** (workflow `pages.yml`) publica `relay/web` en `https://mogollo7.github.io/remote/`: landing y app del celular.
  Actívalo una vez: *Settings → Pages → Source: GitHub Actions*.
- **GitHub Releases** (workflow `release.yml`, sin probar): al subir un tag `v1.0` compila `PCRemote-Setup.exe` en Windows y lo adjunta; la landing lo descarga de ahí.
- **remote.juanlabs.me** solo hace de relay (`/ws/pc`, `/ws/phone`, `/pair`, `/health`). Permite CORS desde `ALLOWED_ORIGINS` (por defecto `https://mogollo7.github.io`).
- `python build.py remote.juanlabs.me https://mogollo7.github.io/remote` hornea ambas URLs en el .exe (el QR apunta a Pages).
- La URL del relay para la web está en `relay/web/config.js`.
