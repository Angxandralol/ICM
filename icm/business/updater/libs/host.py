import pandas as pd
from icm.constants import InterfaceField, EMPTY_FIELD_PLACEHOLDER
from icm.utils import log
from icm.business.updater.libs.ping import PingClient, get_ping_client
from icm.business.updater.libs.snmp import SnmpClient, get_snmp_client


class HostHandler:
    """Class to manage host connection."""

    host: str
    community: str
    isAlive: bool
    _ping_client: PingClient
    _snmp_client: SnmpClient

    def __init__(self, host: str, community: str):
        self.host = host
        self.community = community
        self._ping_client = get_ping_client()
        self._snmp_client = get_snmp_client()
        self.isAlive = self._ping_client.is_alive(host)

    def get_info_interfaces(self) -> pd.DataFrame:
        """Get all interfaces information."""
        try:
            if not self.isAlive:
                log.info(f"{self.host} is not alive")
                return pd.DataFrame()
            if_table = self._snmp_client.get_if_table(self.host, self.community)
            if if_table.empty:
                log.warning(f"{self.host} is alive but no response from SNMP")
                return pd.DataFrame()
            if_x_table = self._snmp_client.get_if_x_table(self.host, self.community)
            data = (
                if_table.merge(if_x_table, on=InterfaceField.IFINDEX, how="left")
                if not if_x_table.empty
                else if_table
            )
            data[InterfaceField.IP] = self.host
            data[InterfaceField.COMMUNITY] = self.community
            data[InterfaceField.SYSNAME] = self._snmp_client.get_sysname(
                self.host, self.community
            )
            data = data.reindex(
                columns=[
                    InterfaceField.IP,
                    InterfaceField.COMMUNITY,
                    InterfaceField.SYSNAME,
                    InterfaceField.IFINDEX,
                    InterfaceField.IFNAME,
                    InterfaceField.IFDESCR,
                    InterfaceField.IFALIAS,
                    InterfaceField.IFHIGHSPEED,
                    InterfaceField.IFOPERSTATUS,
                    InterfaceField.IFADMINSTATUS,
                ]
            )
            data = data.drop_duplicates(
                subset=[
                    InterfaceField.IP,
                    InterfaceField.COMMUNITY,
                    InterfaceField.SYSNAME,
                    InterfaceField.IFINDEX,
                ]
            )
            data = data.fillna(EMPTY_FIELD_PLACEHOLDER)
            data = data.replace("", EMPTY_FIELD_PLACEHOLDER)
            return data.reset_index(drop=True)
        except Exception:
            log.exception("Host handler error. Failed to get all interfaces information.")
            return pd.DataFrame()
