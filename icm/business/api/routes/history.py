from pydantic import BaseModel
from fastapi import APIRouter
from icm.business.api.dependencies import CurrentUser
from icm.business.constants.tags import ApiTags
from icm.business.controllers.assignment import AssignmentController
from icm.business.models.assignment import AssignmentModel

router = APIRouter(prefix="/history", tags=[ApiTags.HISTORY])


class StatusRequest(BaseModel):
    status: str


class MonthRequest(BaseModel):
    date: str
    usernames: list[str]


@router.post("/assignments", response_model=list[AssignmentModel])
def get_assignments(request: StatusRequest, user: CurrentUser):
    """Get assignments from a user by status."""
    return AssignmentController.get_user_assignments_filter_by_status(username=user.username, status=request.status)


@router.get("/user", response_model=list[AssignmentModel])
def get_user_history(date: str, user: CurrentUser):
    """Get user history by a date (YYYY-MM)."""
    return AssignmentController.get_user_assignments_completed_in_month(username=user.username, date=date)


@router.post("/all", response_model=list[AssignmentModel])
def get_all_history(request: MonthRequest, user: CurrentUser):
    """Get user histories by a date (YYYY-MM)."""
    return AssignmentController.get_users_assignments_completed_in_month(usernames=request.usernames, date=request.date)


@router.get("/available", response_model=list[str])
def get_date_available_to_consult_history(user: CurrentUser):
    """Get the months (YYYY-MM) that have at least one assignment available to consult."""
    return AssignmentController.get_date_available_to_consult_history()
