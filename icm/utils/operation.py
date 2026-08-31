import json
import pandas as pd
from typing import List
from pydantic import BaseModel
from icm.constants import InterfaceField
from icm.utils.config import Configuration
from icm.utils.log import log


SUFFIX_OLD = "_old"
SUFFIX_NEW = "_new"
HEADER_RESPONSE_INTERFACES_CHANGES = [
    InterfaceField.ID + SUFFIX_OLD,
    InterfaceField.IP + SUFFIX_OLD,
    InterfaceField.COMMUNITY + SUFFIX_OLD,
    InterfaceField.SYSNAME + SUFFIX_OLD,
    InterfaceField.IFINDEX + SUFFIX_OLD,
    InterfaceField.IFNAME + SUFFIX_OLD,
    InterfaceField.IFDESCR + SUFFIX_OLD,
    InterfaceField.IFALIAS + SUFFIX_OLD,
    InterfaceField.IFHIGHSPEED + SUFFIX_OLD,
    InterfaceField.IFOPERSTATUS + SUFFIX_OLD,
    InterfaceField.IFADMINSTATUS + SUFFIX_OLD,
    InterfaceField.ID + SUFFIX_NEW,
    InterfaceField.IP + SUFFIX_NEW,
    InterfaceField.COMMUNITY + SUFFIX_NEW,
    InterfaceField.SYSNAME + SUFFIX_NEW,
    InterfaceField.IFINDEX + SUFFIX_NEW,
    InterfaceField.IFNAME + SUFFIX_NEW,
    InterfaceField.IFDESCR + SUFFIX_NEW,
    InterfaceField.IFALIAS + SUFFIX_NEW,
    InterfaceField.IFHIGHSPEED + SUFFIX_NEW,
    InterfaceField.IFOPERSTATUS + SUFFIX_NEW,
    InterfaceField.IFADMINSTATUS + SUFFIX_NEW,
]


class OperationData:
    """Class to manage operation data."""

    @staticmethod
    def compare(old_data: pd.DataFrame, new_data: pd.DataFrame) -> pd.DataFrame:
        """Compare two data frames.
        
        Parameters
        ----------
        old_data : pd.DataFrame
            Old data frame.
        new_data : pd.DataFrame
            New data frame.

        Returns
        -------
        pd.DataFrame
            Data frame with the differences.

        Example:
        >>> from utils.operation import OperationData
        >>> from pandas import DataFrame
        >>> old_data = DataFrame({"id": [0, 1], "ip": ["192.168.1.1", "192.168.1.2"], "community": ["public", "private"], "sysname": ["switch1", "switch2"], "ifIndex": [1, 2], "ifName": ["eth0", "eth1"], "ifDescr": ["Interface 1", "Interface 2"], "ifAlias": ["Interface 1 alias", "Interface 2 alias"], "ifHighSpeed": [1000, 1000], "ifOperStatus": ["up", "up"], "ifAdminStatus": ["up", "up"], "consulted_at": ["2023-01-01", "2023-01-01"]})
        >>> new_data = DataFrame({"id": [0, 1], "ip": ["192.168.1.1", "192.168.1.2"], "community": ["public", "private"], "sysname": ["switch1", "switch2"], "ifIndex": [1, 2], "ifName": ["eth0.1", "eth1"], "ifDescr": ["Interface 1", "Interface 2"], "ifAlias": ["Interface 1 alias", "Interface 2 alias"], "ifHighSpeed": [1000, 1000], "ifOperStatus": ["up", "up"], "ifAdminStatus": ["up", "up"], "consulted_at": ["2023-01-02", "2023-01-02"]})
        >>> differences = OperationData.compare(old_data=old_data, new_data=new_data)
        >>> print(differences)
           id_old           ip  community  sysname  ifIndex  ifName_old  ifDescr_old        ifAlias_old  ...  id_new ifName_new  ifDescr_new        ifAlias_new  ifHighSpeed_new  ifOperStatus_new  ifAdminStatus_new  consulted_at_new
        0       0  192.168.1.1     public  switch1        1        eth0  Interface 1  Interface 1 alias  ...       0     eth0.1  Interface 1  Interface 1 alias             1000                up                 up        2023-01-02
        """
        try:
            configuration = Configuration()
            key_empty = "CAMPO VACIO"
            old_data = old_data.fillna(key_empty)
            new_data = new_data.fillna(key_empty)
            keys_merge = [InterfaceField.IP, InterfaceField.COMMUNITY, InterfaceField.SYSNAME, InterfaceField.IFINDEX]
            merge = pd.merge(old_data, new_data, on=keys_merge, how="inner", suffixes=(SUFFIX_OLD, SUFFIX_NEW))
            merge[InterfaceField.IP + SUFFIX_OLD] = merge[InterfaceField.IP]
            merge[InterfaceField.IP + SUFFIX_NEW] = merge[InterfaceField.IP]
            merge[InterfaceField.COMMUNITY + SUFFIX_OLD] = merge[InterfaceField.COMMUNITY]
            merge[InterfaceField.COMMUNITY + SUFFIX_NEW] = merge[InterfaceField.COMMUNITY]
            merge[InterfaceField.SYSNAME + SUFFIX_OLD] = merge[InterfaceField.SYSNAME]
            merge[InterfaceField.SYSNAME + SUFFIX_NEW] = merge[InterfaceField.SYSNAME]
            merge[InterfaceField.IFINDEX + SUFFIX_OLD] = merge[InterfaceField.IFINDEX]
            merge[InterfaceField.IFINDEX + SUFFIX_NEW] = merge[InterfaceField.IFINDEX]
            merge = merge.drop(columns=keys_merge)
            merge = merge.reindex(columns=HEADER_RESPONSE_INTERFACES_CHANGES)
            if configuration.system.notification_changes.ifName:
                df_ifName = merge[
                    (merge[InterfaceField.IFNAME + SUFFIX_OLD] != merge[InterfaceField.IFNAME + SUFFIX_NEW]) &
                    (~merge[InterfaceField.IFNAME + SUFFIX_OLD].isin([key_empty])) &
                    (~merge[InterfaceField.IFNAME + SUFFIX_NEW].isin([key_empty]))
                ]
            else:
                df_ifName = pd.DataFrame(columns=HEADER_RESPONSE_INTERFACES_CHANGES)
            if configuration.system.notification_changes.ifDescr:
                df_ifDescr = merge[
                    (merge[InterfaceField.IFDESCR + SUFFIX_OLD] != merge[InterfaceField.IFDESCR + SUFFIX_NEW]) &
                    (~merge[InterfaceField.IFDESCR + SUFFIX_OLD].isin([key_empty])) &
                    (~merge[InterfaceField.IFDESCR + SUFFIX_NEW].isin([key_empty]))
                ]
            else:
                df_ifDescr = pd.DataFrame(columns=HEADER_RESPONSE_INTERFACES_CHANGES)
            if configuration.system.notification_changes.ifAlias:
                df_ifAlias = merge[
                    (merge[InterfaceField.IFALIAS + SUFFIX_OLD] != merge[InterfaceField.IFALIAS + SUFFIX_NEW]) &
                    (~merge[InterfaceField.IFALIAS + SUFFIX_OLD].isin([key_empty])) &
                    (~merge[InterfaceField.IFALIAS + SUFFIX_NEW].isin([key_empty]))
                ]
            else:
                df_ifAlias = pd.DataFrame(columns=HEADER_RESPONSE_INTERFACES_CHANGES)
            if configuration.system.notification_changes.ifHighSpeed:
                df_ifHighSpeed = merge[
                    (
                        merge[InterfaceField.IFHIGHSPEED + SUFFIX_OLD]
                        != merge[InterfaceField.IFHIGHSPEED + SUFFIX_NEW]
                    )
                    & (
                        ~merge[InterfaceField.IFHIGHSPEED + SUFFIX_OLD].isin(
                            [key_empty]
                        )
                    )
                    & (
                        ~merge[InterfaceField.IFHIGHSPEED + SUFFIX_NEW].isin(
                            [key_empty]
                        )
                    )
                    & (
                        (
                            (merge[InterfaceField.IFHIGHSPEED + SUFFIX_OLD] != 0)
                            & (merge[InterfaceField.IFHIGHSPEED + SUFFIX_NEW] != 0)
                        )
                        | (configuration.system.notification_changes.ifOperStatus)
                    )
                ]
            else:
                df_ifHighSpeed = pd.DataFrame(columns=HEADER_RESPONSE_INTERFACES_CHANGES)
            if configuration.system.notification_changes.ifOperStatus:
                df_ifOperStatus = merge[
                    (merge[InterfaceField.IFOPERSTATUS + SUFFIX_OLD] != merge[InterfaceField.IFOPERSTATUS + SUFFIX_NEW]) &
                    (~merge[InterfaceField.IFOPERSTATUS + SUFFIX_OLD].isin([key_empty])) &
                    (~merge[InterfaceField.IFOPERSTATUS + SUFFIX_NEW].isin([key_empty]))
                ]
            else:
                df_ifOperStatus = pd.DataFrame(columns=HEADER_RESPONSE_INTERFACES_CHANGES)
            if configuration.system.notification_changes.ifAdminStatus:
                df_ifAdminStatus = merge[
                    (merge[InterfaceField.IFADMINSTATUS + SUFFIX_OLD] != merge[InterfaceField.IFADMINSTATUS + SUFFIX_NEW]) &
                    (~merge[InterfaceField.IFADMINSTATUS + SUFFIX_OLD].isin([key_empty])) &
                    (~merge[InterfaceField.IFADMINSTATUS + SUFFIX_NEW].isin([key_empty]))
                ]
            else:
                df_ifAdminStatus = pd.DataFrame(columns=HEADER_RESPONSE_INTERFACES_CHANGES)

            differences = pd.concat([df_ifName, df_ifDescr], axis=0)
            differences = differences.drop_duplicates()
            differences = pd.concat([differences, df_ifAlias], axis=0)
            differences = differences.drop_duplicates()
            differences = pd.concat([differences, df_ifHighSpeed], axis=0)
            differences = differences.drop_duplicates()
            differences = pd.concat([differences, df_ifOperStatus], axis=0)
            differences = differences.drop_duplicates()
            differences = pd.concat([differences, df_ifAdminStatus], axis=0)
            differences = differences.drop_duplicates()

            return differences
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Operation data error. Failed to compare data frames. {error}")
            return pd.DataFrame(columns=HEADER_RESPONSE_INTERFACES_CHANGES)
        
    @staticmethod
    def transform_to_json(data: pd.DataFrame | List[BaseModel]) -> List[dict]:
        """Transform data frame to json.
        
        Parameters
        ----------
        data : pd.DataFrame | List[BaseModel]
            Data to transform.

        Returns
        -------
        dict
            Data in json format.
        """
        try:
            if isinstance(data, pd.DataFrame):
                data = data.to_json(orient="records")
                return json.loads(data)
            elif isinstance(data, list):
                return [value.model_dump() for value in data]
            else:
                return []
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Operation data error. Failed to transform data frame to json. {error}")
            return []
