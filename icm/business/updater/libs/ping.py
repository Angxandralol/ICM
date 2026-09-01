import shlex
from abc import ABC, abstractmethod
from paramiko import ChannelFile
from icm.constants import SnmpModeTypes
from icm.utils import log, Configuration
from icm.business.updater.libs.ssh import SshHandler
from icm.business.updater.constants import SSH_COMMAND_TIMEOUT_SECONDS


class PingClient(ABC):
    """Strategy interface to check whether a host is alive."""

    @abstractmethod
    def is_alive(self, host: str) -> bool:
        """Check whether the given host responds to a ping."""


class ShellPingClient(PingClient):
    """Ping implementation using the shell `ping` command executed remotely over SSH."""

    def _lost_package(self, stdout: ChannelFile) -> bool:
        try:
            if stdout.channel.recv_exit_status() == 0:
                response_str = stdout.read().decode("utf-8")
                if (
                    "1 received, 0% packet loss" in response_str
                    or "is alive" in response_str
                ):
                    return False
            return True
        except Exception:
            log.exception("Ping error. Failed to check if package is lost.")
            return True

    def is_alive(self, host: str) -> bool:
        """Ping the host through the SSH jump chain."""
        try:
            config = Configuration()
            command_ping = config.system.snmp.commands.ping
            safe_host = shlex.quote(host)
            ssh = SshHandler()
            ssh.connect()
            if not ssh.isConnected:
                log.error(f"Ping error. No SSH connection available to ping {host}.")
                return False
            client = ssh.get_client()
            _stdin, stdout, stderr = client.exec_command(
                f"{command_ping} -c 1 -W 2 {safe_host}",
                timeout=SSH_COMMAND_TIMEOUT_SECONDS,
            )
            if stderr.channel.recv_exit_status() != 0:
                response_str = stderr.read().decode("utf-8")
                if "/usr/sbin/ping: illegal option -- W" in response_str:
                    _stdin, stdout, _stderr = client.exec_command(
                        f"{command_ping} {safe_host}",
                        timeout=SSH_COMMAND_TIMEOUT_SECONDS,
                    )
            return not self._lost_package(stdout)
        except Exception:
            log.exception("Ping error. Failed to execute ping command.")
            return False


def get_ping_client() -> PingClient:
    """Return the ping strategy configured for the system."""
    mode = Configuration().system.snmp.mode
    if mode == SnmpModeTypes.LEGACY:
        return ShellPingClient()
    raise NotImplementedError(f"Ping mode '{mode}' is not implemented yet")
