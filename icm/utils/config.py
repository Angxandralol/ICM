import os
import json
import random
import string
from pydantic import BaseModel
from dotenv import load_dotenv, dotenv_values
from icm.constants import SnmpModeTypes
from icm.utils.log import log


load_dotenv(override=True)


class ConfigCommands(BaseModel):
    ping: str
    snmp: str


class ConfigSnmpCredentials(BaseModel):
    host: str
    user: str
    password: str
    port: int


class ConfigSnmp(BaseModel):
    mode: str = SnmpModeTypes.LEGACY
    commands: ConfigCommands
    credentials: list[ConfigSnmpCredentials]


class ConfigUsers(BaseModel):
    root: bool
    admin: bool
    user: bool
    soport: bool


class ConfigInterface(BaseModel):
    ifName: bool
    ifDescr: bool
    ifAlias: bool
    ifHighSpeed: bool
    ifOperStatus: bool
    ifAdminStatus: bool


class ConfigModel(BaseModel):
    snmp: ConfigSnmp
    can_assign: ConfigUsers
    can_receive_assignment: ConfigUsers
    view_information_global: ConfigUsers
    notification_changes: ConfigInterface


URI_POSTGRES = "URI_POSTGRES"
SECRET_KEY = "SECRET_KEY"
HOST_FRONTEND = "HOST_FRONTEND"
SYSTEM_FILENAME = "system.json"
CONFIG_SYSTEM_BASE = ConfigModel(
    snmp=ConfigSnmp(
        mode=SnmpModeTypes.LEGACY,
        commands=ConfigCommands(ping="ping", snmp="snmpwalk"),
        credentials=[
            ConfigSnmpCredentials(
                host="127.0.0.1", user="public", password="public", port=22
            )
        ],
    ),
    can_assign=ConfigUsers(root=True, admin=True, user=False, soport=False),
    can_receive_assignment=ConfigUsers(root=False, admin=True, user=True, soport=False),
    view_information_global=ConfigUsers(root=True, admin=True, user=False, soport=True),
    notification_changes=ConfigInterface(
        ifName=True,
        ifDescr=True,
        ifAlias=True,
        ifHighSpeed=True,
        ifOperStatus=False,
        ifAdminStatus=False,
    ),
)


class Configuration:
    """Class to manage operations related to system configuration."""

    _instance: "Configuration | None" = None
    uri_postgres: str
    system: ConfigModel
    key: str
    host_frontend: str

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Configuration, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self.read_env()
            self.read_config_system()

    def _get_base_path(self) -> str:
        """Get base path of project."""
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        return base_path

    def __create_base_config(self) -> None:
        """Create base configuration."""
        try:
            path = self._get_base_path()
            if not os.path.exists(f"{path}/{SYSTEM_FILENAME}"):
                with open(f"{path}/{SYSTEM_FILENAME}", "w") as file:
                    json.dump(CONFIG_SYSTEM_BASE.model_dump(), file, indent=4)
        except Exception as error:
            log.error(f"Failed system configuration. {error}")
            exit(1)

    def read_env(self):
        """Read environment variables."""
        path = self._get_base_path()
        try:
            if os.path.exists(f"{path}/.env.development"):
                env = dotenv_values(f"{path}/.env.development")
            elif os.path.exists(f"{path}/.env.production"):
                env = dotenv_values(f"{path}/.env.production")
            elif os.path.exists(f"{path}/.env"):
                env = dotenv_values(f"{path}/.env")
            else:
                raise FileNotFoundError("No .env file found")
        except FileNotFoundError as error:
            log.error(f"Failed system configuration. {error}")
            exit(1)
        try:
            uri_postgres = env.get(URI_POSTGRES)
            if not uri_postgres:
                raise ValueError(f"{URI_POSTGRES} not found in .env file")
            key = env.get("SECRET_KEY")
            if not key:
                raise ValueError(f"{SECRET_KEY} not found in .env file")
            host_frontend = env.get("HOST_FRONTEND")
            if not host_frontend:
                raise ValueError(f"{HOST_FRONTEND} not found in .env file")
        except ValueError as error:
            log.error(f"Failed system configuration. {error}")
            exit(1)
        else:
            self.uri_postgres = uri_postgres
            self.key = key
            self.host_frontend = host_frontend

    def read_config_system(self) -> None:
        """Read configuration system."""
        try:
            path = self._get_base_path()
            if not os.path.exists(f"{path}/{SYSTEM_FILENAME}"):
                self.__create_base_config()
            with open(f"{path}/{SYSTEM_FILENAME}", "r") as file:
                system = json.load(file)
            self.system = ConfigModel.model_validate(system)
        except Exception as error:
            log.error(f"Failed system configuration. {error}")
            exit(1)

    def generate_default_password(self) -> str:
        """Generate a new password."""
        characters = string.ascii_letters + string.digits
        password = "".join(random.choice(characters) for i in range(10))
        return password

    def save(
        self,
        can_assign: ConfigUsers,
        can_receive_assignment: ConfigUsers,
        view_information_global: ConfigUsers,
        notification_changes: ConfigInterface,
    ) -> bool:
        """Save a new configuration of system.

        :param can_assign: Can assign.
        :type can_assign: ConfigUsers
        :param can_receive_assignment: Can receive assignment.
        :type can_receive_assignment: ConfigUsers
        :param view_information_global: View information global.
        :type view_information_global: ConfigUsers
        :param notification_changes: Notification changes.
        :type notification_changes: ConfigInterface
        :return: True if the configuration was saved successfully, False otherwise.
        :rtype: bool
        """
        try:
            new_config = ConfigModel(
                snmp=self.system.snmp.model_dump(),
                can_assign=can_assign.model_dump(),
                can_receive_assignment=can_receive_assignment.model_dump(),
                view_information_global=view_information_global.model_dump(),
                notification_changes=notification_changes.model_dump(),
            )
            with open(f"{self._get_base_path()}/{SYSTEM_FILENAME}", "w") as file:
                json.dump(new_config.model_dump(), file, indent=4)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Config controller error. Failed to save config. {error}")
            return False
        else:
            return True


if __name__ == "__main__":
    config = Configuration()
    print(config._get_base_path())
