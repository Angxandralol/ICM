from icm.constants import InterfaceField


class SnmpOid:
    """SNMP OIDs consulted by the updater."""

    SYSNAME = "1.3.6.1.2.1.1.5.0"
    IF_TABLE = "1.3.6.1.2.1.2.2.1"
    IF_X_TABLE = "1.3.6.1.2.1.31.1.1.1"


IF_TABLE_COLUMNS = {
    "ifDescr": InterfaceField.IFDESCR,
    "ifAdminStatus": InterfaceField.IFADMINSTATUS,
    "ifOperStatus": InterfaceField.IFOPERSTATUS,
}

IF_X_TABLE_COLUMNS = {
    "ifName": InterfaceField.IFNAME,
    "ifHighSpeed": InterfaceField.IFHIGHSPEED,
    "ifAlias": InterfaceField.IFALIAS,
}

SSH_CONNECT_TIMEOUT_SECONDS = 10
SSH_COMMAND_TIMEOUT_SECONDS = 15
