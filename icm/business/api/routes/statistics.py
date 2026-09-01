from pydantic import BaseModel
from fastapi import APIRouter
from icm.access import StatisticsModel
from icm.business.api.dependencies import CurrentUser, ViewGlobalPermissionUser
from icm.business.constants.tags import ApiTags
from icm.business.controllers.assignment import AssignmentController


router = APIRouter(prefix="/statistics", tags=[ApiTags.STATISTICS])


class StatisticsRequest(BaseModel):
    usernames: list[str]


@router.get("/assignments/user", response_model=list[StatisticsModel])
def get_assignments_statistics(user: CurrentUser):
    """Get assignments statistics from a user."""
    return AssignmentController.get_statistics_assignments(usernames=[user.username])


@router.post("/assignments/all", response_model=list[StatisticsModel])
def get_all_assignments_statistics(request: StatisticsRequest, user: ViewGlobalPermissionUser):
    """Get all assignments statistics."""
    return AssignmentController.get_statistics_assignments(usernames=request.usernames)
