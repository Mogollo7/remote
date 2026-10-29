# Qué cambiar y activar antes de publicar

Lista de pendientes para quien vea este repo por primera vez. Marca cada punto al terminarlo.

## 1. GitHub (una sola vez)
- [ ] **Settings → Pages → Source: GitHub Actions.** Sin esto la landing y la app web no se publican.
      Quedan en `https://<usuario>.github.io/<repo>/` (hoy: `https://mogollo7.github.io/remote/`).
- [ ] Si el repo o el usuario cambian de nombre, editar `relay/web/config.js` (`RELEASES`) y el enlace del pie de `relay/web/index.html`.
- [ ] Publicar el instalador: crear un tag `v1.0` (`git tag v1.0 && git push --tags`). El workflow `release.yml` compila `PCRemote-Setup.exe`
      en Windows y lo adjunta a la Release. **Ese workflow no se ha probado todavía**; si falla, compilar a mano (punto 3) y subir el `.exe` a mano.

## 2. Servidor de conexión (VPS, `remote.juanlabs.me`)
Solo hace de relay: empareja y reenvía. No sirve la web (aunque puede, como respaldo).
- [ ] Subir la versión nueva de `relay/` y seguir `relay/CONFIGURACION.md`.
- [ ] En el `.service`, `Environment=ALLOWED_ORIGINS=https://mogollo7.github.io` (webs que pueden usar `/pair` y `/health`). Varias, separadas por coma.
- [ ] Comprobar: `curl https://remote.juanlabs.me/health` debe devolver `{"ok": true, ...}`.
- [ ] Si el dominio es otro: cambiarlo en `relay/web/config.js` (`RELAY`) y compilar el exe con ese dominio.

## 3. Compilar el programa de Windows
```bash
pip install -r requirements.txt pyinstaller pillow segno
python build.py remote.juanlabs.me https://mogollo7.github.io/remote
```
Genera `dist/PCRemote-Setup.exe`, `dist/PCRemote.exe` y `dist/pcremote-server.zip`.
El segundo argumento es la web de la app: el QR del exe apunta ahí. Sin él, el QR usa el propio servidor.

## 4. Cosas que aún no están hechas
- [ ] Encender el PC (Wake-on-LAN): hoy el botón solo avisa. Necesita un equipo siempre encendido en casa o un enchufe inteligente.
- [ ] Probar apagar, reiniciar, suspender y bloquear en un Windows real (los tests solo cubren emparejado, info, lista blanca y olvidar celular).
- [ ] APK de Android: la landing lo muestra como "próximamente"; mientras tanto se usa la app web.
- [ ] Probar el flujo completo con HTTPS real (celular → Pages → relay → exe).

## 5. Qué no se sube al repo (ver `.gitignore`)
`dist/`, `build/`, `agent/_server.py` y `assets/icono.ico` se generan con `build.py`. `relay.json` y `config.json` tienen datos de usuarios:
nunca se suben. Las carpetas `.claude/` y `.agents/` son de herramientas del editor.
