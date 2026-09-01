import shlex
import pandas as pd
from abc import ABC, abstractmethod
from icm.constants import InterfaceField, EMPTY_FIELD_PLACEHOLDER, SnmpModeTypes
from icm.utils import log, Configuration
from icm.business.updater.libs.ssh import SshHandler
from icm.business.updater.constants import (
    SnmpOid,
    IF_TABLE_COLUMNS,
    IF_X_TABLE_COLUMNS,
    SSH_COMMAND_TIMEOUT_SECONDS,
)


class SnmpClient(ABC):
    """Strategy interface to query interface information over SNMP."""

    @abstractmethod
    def get_sysname(self, host: str, community: str) -> str:
        """Get the sysName of a device."""

    @abstractmethod
    def get_if_table(self, host: str, community: str) -> pd.DataFrame:
        """Get ifIndex, ifDescr, ifAdminStatus and ifOperStatus of all interfaces."""

    @abstractmethod
    def get_if_x_table(self, host: str, community: str) -> pd.DataFrame:
        """Get ifIndex, ifName, ifHighSpeed and ifAlias of all interfaces."""


class ShellSnmpClient(SnmpClient):
    """SNMP implementation using the shell `snmpwalk` command executed remotely over SSH."""

    _command: str

    def __init__(self):
        self._command = Configuration().system.snmp.commands.snmp

    def _execute(self, host: str, community: str, oid: str) -> str:
        ssh = SshHandler()
        ssh.connect()
        if not ssh.isConnected:
            log.error(f"SNMP handler error. No SSH connection available to query {host}.")
            return ""
        client = ssh.get_client()
        safe_host = shlex.quote(host)
        safe_community = shlex.quote(community)
        command = f"{self._command} -v 2c -c {safe_community} {safe_host} {oid}"
        _stdin, stdout, _stderr = client.exec_command(
            command, timeout=SSH_COMMAND_TIMEOUT_SECONDS
        )
        if stdout.channel.recv_exit_status() != 0:
            return ""
        return stdout.read().decode("utf-8")

    def _parse_table(self, response: str, columns: dict[str, str]) -> pd.DataFrame:
        rows: dict[int, dict[str, str]] = {}
        for line in response.splitlines():
            if "=" not in line:
                continue
            name_part, _, value_part = line.partition("=")
            segments = name_part.strip().split(".")
            if len(segments) < 2:
                continue
            column_name = segments[0].split("::")[-1]
            field = columns.get(column_name)
            if not field:
                continue
            try:
                row_index = int(segments[1])
            except ValueError:
                continue
            value = value_part.split(":", 1)[-1].strip() if ":" in value_part else value_part.strip()
            value = value.replace("\\", "") or EMPTY_FIELD_PLACEHOLDER
            rows.setdefault(row_index, {})[field] = value
        df = pd.DataFrame.from_dict(rows, orient="index")
        df = df.reindex(columns=list(columns.values()))
        df.index.name = InterfaceField.IFINDEX
        return df.reset_index()

    def get_sysname(self, host: str, community: str) -> str:
        """Get the sysName of a device."""
        try:
            response = self._execute(host, community, SnmpOid.SYSNAME)
            if not response:
                return ""
            return response.split("= STRING:")[1].strip()
        except Exception:
            log.exception("SNMP handler error. Failed to get sysname.")
            return ""

    def get_if_table(self, host: str, community: str) -> pd.DataFrame:
        """Get ifIndex, ifDescr, ifAdminStatus and ifOperStatus of all interfaces."""
        try:
            response = self._execute(host, community, SnmpOid.IF_TABLE)
            if not response:
                return pd.DataFrame()
            return self._parse_table(response, IF_TABLE_COLUMNS)
        except Exception:
            log.exception("SNMP handler error. Failed to get ifTable.")
            return pd.DataFrame()

    def get_if_x_table(self, host: str, community: str) -> pd.DataFrame:
        """Get ifIndex, ifName, ifHighSpeed and ifAlias of all interfaces."""
        try:
            response = self._execute(host, community, SnmpOid.IF_X_TABLE)
            if not response:
                return pd.DataFrame()
            return self._parse_table(response, IF_X_TABLE_COLUMNS)
        except Exception:
            log.exception("SNMP handler error. Failed to get ifXTable.")
            return pd.DataFrame()


def get_snmp_client() -> SnmpClient:
    """Return the SNMP strategy configured for the system."""
    mode = Configuration().system.snmp.mode
    if mode == SnmpModeTypes.LEGACY:
        return ShellSnmpClient()
    raise NotImplementedError(f"SNMP mode '{mode}' is not implemented yet")
