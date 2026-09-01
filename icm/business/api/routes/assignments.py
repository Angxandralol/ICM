from pydantic import BaseModel
from fastapi import APIRouter
from icm.access import ReassignmentModel
from icm.business.api.dependencies import AssignPermissionUser, CurrentUser
from icm.business.constants.tags import ApiTags
from icm.business.controllers.assignment import AssignmentController
from icm.business.models.response import MessageResponse
from icm.business.models.assignment import NewAssignmentModel, UpdateAssignmentModel


router = APIRouter(prefix="/assignments", tags=[ApiTags.ASSIGNMENTS])


class RequestAutomaticAssignment(BaseModel):
    usernames: list[str]


@router.post("/new", status_code=201, response_model=MessageResponse)
def new_assignments(assignments: list[NewAssignmentModel], user: AssignPermissionUser):
    """Create new assignments."""
    AssignmentController.new_assignment(assignments=assignments)
    return MessageResponse(message="Assignments created successfully")


@router.post("/reassign", response_model=MessageResponse)
def reassign_assignments(assignments: list[ReassignmentModel], user: AssignPermissionUser):
    """Reassign assignments."""
    AssignmentController.reassign(assignments=assignments)
    return MessageResponse(message="Assignments reassigned successfully")


@router.post("/automatic", status_code=201, response_model=MessageResponse)
def automatic_assignment(request: RequestAutomaticAssignment, user: AssignPermissionUser):
    """Automatically distribute unassigned changes across the given usernames."""
    AssignmentController.automatic_assignment(assign_by=user.username, usernames=request.usernames)
    return MessageResponse(message="Assignments automatic assigned successfully")


@router.post("/status", response_model=MessageResponse)
def update_assignments_status(assignments: list[UpdateAssignmentModel], user: CurrentUser):
    """Update assignments status."""
    AssignmentController.update_status_assignment(assignments=assignments, username=user.username)
    return MessageResponse(message="Assignments status updated successfully")
