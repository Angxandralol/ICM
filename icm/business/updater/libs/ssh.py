import paramiko
import threading
import time
from icm.utils import Configuration, log
from icm.business.updater.constants import SSH_CONNECT_TIMEOUT_SECONDS


class SshHandler:
    """Class to manage ssh connection."""

    _instance: "SshHandler | None" = None
    _config: Configuration
    client: paramiko.SSHClient
    _client: list[paramiko.SSHClient]
    _last_used: float
    _lock: threading.Lock
    isConnected: bool = False

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(SshHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._config = Configuration()
            self.isConnected = False
            self._client = []
            self._last_used = 0
            self._lock = threading.Lock()
            self._initialized = True

    def _ssh_jump(self) -> None:
        """Connect through the chain of SSH jump hosts, cleaning up any partial jump on failure."""
        try:
            credentials = self._config.system.snmp.credentials
            sock: paramiko.Channel | None = None
            jumps: int = len(credentials) - 1
            for i, credential in enumerate(credentials):
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(
                    username=credential.user,
                    password=credential.password,
                    hostname=credential.host,
                    port=credential.port,
                    sock=sock,
                    timeout=SSH_CONNECT_TIMEOUT_SECONDS,
                    banner_timeout=SSH_CONNECT_TIMEOUT_SECONDS,
                    auth_timeout=SSH_CONNECT_TIMEOUT_SECONDS,
                )
                self._client.append(client)
                if i == jumps:
                    break
                transport = client.get_transport()
                if not transport:
                    raise ValueError("The SSH jump transport failed. Transport is None")
                next_credential = credentials[i + 1]
                dest_addr = (next_credential.host, next_credential.port)
                local_addr = ("127.0.0.1", 0)
                sock = transport.open_channel("direct-tcpip", dest_addr, local_addr)
        except Exception:
            while self._client:
                self._client.pop().close()
            raise

    def get_client(self) -> paramiko.SSHClient:
        return self._client[-1]

    def connect(self) -> None:
        try:
            with self._lock:
                if self.isConnected:
                    self._last_used = time.time()
                    return
                if not self._config:
                    raise ValueError("SSH Configuration not set")
                self._ssh_jump()
                self.isConnected = True
                self._last_used = time.time()
        except ValueError as error:
            self.isConnected = False
            log.error(f"SSH Connection - {error}")
        except Exception:
            self.isConnected = False
            log.exception("SSH Connection: Failed to connect to server")

    def disconnect(self) -> None:
        try:
            if self.isConnected:
                while len(self._client) > 0:
                    client = self._client.pop()
                    client.close()
        except Exception:
            log.exception("SSH Connection: Failed to disconnect from server")
        else:
            self.isConnected = False
