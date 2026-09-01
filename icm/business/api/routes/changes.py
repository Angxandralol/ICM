from fastapi import APIRouter, Query
from icm.business.api.dependencies import AssignPermissionUser
from icm.business.constants.tags import ApiTags
from icm.business.controllers.change import ChangeController
from icm.business.models.change import PaginatedChanges


router = APIRouter(tags=[ApiTags.CHANGES])


@router.get("/changes", response_model=PaginatedChanges)
def get_changes(
    user: AssignPermissionUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
):
    """Get interfaces with changes of the day."""
    return ChangeController.get_interfaces_with_changes(page=page, page_size=page_size)
