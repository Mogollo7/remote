// Servidor de conexión (relay). Si esta página la sirve el propio relay, RELAY queda vacío (mismo origen).
window.RELAY = /^(localhost|127\.)/.test(location.hostname) ? "" : "https://remote.juanlabs.me";
window.RELEASES = "https://github.com/Mogollo7/remote/releases/latest/download/";
