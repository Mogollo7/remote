# PC Remote — Configuración del servidor

El servidor es un **relay compartido**: empareja PCs con celulares y reenvía mensajes. No guarda
tu contraseña ni ejecuta comandos. Un solo servidor sirve a todos los que usen el `.exe`.
También entrega la app del celular (PWA) en `https://TU-DOMINIO`.

## Requisitos
- VPS Linux (Ubuntu/Debian) con Python 3.9+ y acceso `root`/sudo.
- Un dominio (ej. `remote.juanlabs.me`) con registro **A** apuntando a la IP del VPS.
- Puertos **80 y 443** abiertos (los usa Caddy para el certificado HTTPS automático).

## Instalación (copiar y pegar)

Reemplaza `remote.juanlabs.me` por tu dominio. Sube `pcremote-server.zip` al VPS (`scp`).

```bash
# 1) Usuario y carpeta
sudo useradd -r -m -d /opt/pcremote pcremote
sudo apt update && sudo apt install -y python3-venv unzip caddy

# 2) Código
sudo unzip -o ~/pcremote-server.zip -d /opt/pcremote
sudo mkdir -p /opt/pcremote/data
cd /opt/pcremote
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt
sudo chown -R pcremote:pcremote /opt/pcremote

# 3) Servicio del relay
sudo cp /opt/pcremote/pcremote-relay.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pcremote-relay

# 4) HTTPS con Caddy (sustituye el dominio)
echo 'remote.juanlabs.me {
	reverse_proxy 127.0.0.1:8080
}' | sudo tee /etc/caddy/Caddyfile
sudo systemctl restart caddy
```

> Si ya usas Caddy/nginx para otros sitios, añade solo el bloque `reverse_proxy 127.0.0.1:8080`
> para tu dominio. El proxy debe permitir WebSocket (Caddy y nginx con `Upgrade` lo hacen).

## Verificar
```bash
systemctl status pcremote-relay          # debe decir active (running)
curl -I https://remote.juanlabs.me/    # debe responder 200
```

## Configuración
| Qué | Dónde | Valor por defecto |
|---|---|---|
| Puerto interno | `Environment=PORT=` en el `.service` | `8080` |
| Webs permitidas (CORS) | `Environment=ALLOWED_ORIGINS=` | `https://mogollo7.github.io` |
| Base de datos | `Environment=RELAY_DB=` | `/opt/pcremote/data/relay.json` |

`relay.json` guarda los PCs registrados y los celulares emparejados (solo hashes). **Haz copia de ese
archivo**: si se borra, todos tendrán que volver a emparejarse.

## Actualizar
```bash
sudo unzip -o ~/pcremote-server.zip -d /opt/pcremote
sudo chown -R pcremote:pcremote /opt/pcremote
sudo systemctl restart pcremote-relay
```

## Usar
1. **PC:** ejecuta `PCRemote.exe`. Muestra un código de 6 dígitos (vale 10 min, un solo uso).
   Con **+ AÑADIR APP** eliges los programas que el celular podrá abrir.
2. **Celular:** abre `https://remote.juanlabs.me`, escribe el código. Para instalarla como app:
   Chrome → menú ⋮ → *Instalar aplicación*; iPhone: Safari → Compartir → *Añadir a pantalla de inicio*.
3. Cada compañero hace lo mismo con su PC y su celular; no comparten nada entre sí.

## Seguridad
- El relay limita intentos de código (5 por minuto por IP).
- El PC solo ejecuta: info, abrir apps de **su** lista, apagar, reiniciar, suspender, bloquear.
- Si alguien pierde el celular: borra su entrada de `phones` en `relay.json` y reinicia el servicio.

## Problemas comunes
- **El PC aparece "SIN CONEXIÓN":** revisa que el `.exe` se compiló con tu dominio y que `curl -I` responde.
- **Caddy no emite certificado:** el registro A del dominio aún no propaga o el puerto 80/443 está cerrado.
- **Logs:** `journalctl -u pcremote-relay -f`
