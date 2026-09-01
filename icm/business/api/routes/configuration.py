from fastapi import APIRouter
from icm.business.api.dependencies import AssignPermissionUser, RootUser
from icm.business.constants.tags import ApiTags
from icm.business.controllers.config import ConfigController
from icm.business.models.configuration import NewConfigModel
from icm.business.models.response import MessageResponse


router = APIRouter(prefix="/configuration", tags=[ApiTags.CONFIGURATION])


@router.get("", response_model=NewConfigModel)
def get_configuration(user: AssignPermissionUser):
    """Get configuration of the system."""
    return ConfigController.get_config()


@router.post("/new", response_model=MessageResponse)
def new_configuration(new_config: NewConfigModel, user: RootUser):
    """Save new configuration."""
    ConfigController.new_config(new_config)
    return MessageResponse(message="Configuration saved successfully")
