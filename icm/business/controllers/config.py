from fastapi import status as http_status
from icm.constants import RoleTypes
from icm.utils import Configuration, log
from icm.business.exceptions import BusinessError
from icm.business.models.configuration import NewConfigModel


class ConfigController:
    """Class to manage config controller."""

    @staticmethod
    def get_config() -> NewConfigModel:
        """Get config."""
        try:
            configuration = Configuration()
            return NewConfigModel(
                can_assign=configuration.system.can_assign.model_dump(),
                can_receive_assignment=configuration.system.can_receive_assignment.model_dump(),
                view_information_global=configuration.system.view_information_global.model_dump(),
                notification_changes=configuration.system.notification_changes.model_dump(),
            )
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Config controller error. Failed to get config. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get configuration")

    @staticmethod
    def new_config(new_config: NewConfigModel) -> None:
        """Create new config."""
        try:
            configuration = Configuration()
            status_operation = configuration.save(
                can_assign=new_config.can_assign,
                can_receive_assignment=new_config.can_receive_assignment,
                view_information_global=new_config.view_information_global,
                notification_changes=new_config.notification_changes
            )
            if not status_operation:
                raise Exception("Failed to save the new configuration")
            configuration.read_config_system()
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Config controller error. Failed to create config. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to save the new configuration")
        
    @staticmethod
    def can_assign_permission(role: str) -> bool:
        try:
            configuration = Configuration()
            if role == RoleTypes.ROOT:
                return configuration.system.can_assign.root
            elif role == RoleTypes.ADMIN:
                return configuration.system.can_assign.admin
            elif role == RoleTypes.USER:
                return configuration.system.can_assign.user
            elif role == RoleTypes.SOPORT:
                return configuration.system.can_assign.soport
            else:
                return False
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Config controller error. Failed to get config. {error}")
            return False
        
    @staticmethod
    def can_view_information_global_permission(role: str) -> bool:
        try:
            configuration = Configuration()
            if role == RoleTypes.ROOT:
                return configuration.system.view_information_global.root
            elif role == RoleTypes.ADMIN:
                return configuration.system.view_information_global.admin
            elif role == RoleTypes.USER:
                return configuration.system.view_information_global.user
            elif role == RoleTypes.SOPORT:
                return configuration.system.view_information_global.soport
            else:
                return False
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Config controller error. Failed to get config. {error}")
            return False