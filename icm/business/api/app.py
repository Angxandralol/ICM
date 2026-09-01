from typing import Annotated
from datetime import timedelta
from fastapi import FastAPI, Depends, Request, status as http_status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from icm.business.api.routes.changes import router as ChangesRouter
from icm.business.api.routes.assignments import router as AssignmentsRouter
from icm.business.api.routes.statistics import router as StatisticsRouter
from icm.business.api.routes.history import router as HistoryRouter
from icm.business.api.routes.user import router as UserRouter
from icm.business.api.routes.configuration import router as ConfigurationRouter
from icm.business.constants.tags import ApiTags
from icm.business.controllers.security import SecurityController
from icm.business.exceptions import BusinessError
from icm.business.models.token import TokenModel
from icm.utils import Configuration


OPENAPI_TAGS = [
    {"name": ApiTags.AUTH, "description": "Authenticate and obtain an access token."},
    {"name": ApiTags.USERS, "description": "Manage user accounts and the logged-in user's profile."},
    {"name": ApiTags.ASSIGNMENTS, "description": "Create, reassign and update the status of interface-change assignments."},
    {"name": ApiTags.CHANGES, "description": "Interfaces with changes detected in the network."},
    {"name": ApiTags.HISTORY, "description": "Historical view of assignments by user and by month."},
    {"name": ApiTags.STATISTICS, "description": "Aggregated statistics of assignments."},
    {"name": ApiTags.CONFIGURATION, "description": "System-wide configuration (permissions and change notifications)."},
]

app = FastAPI(openapi_tags=OPENAPI_TAGS)
config = Configuration()
origins = [
    config.host_frontend,
    f"{config.host_frontend}:80",
    f"{config.host_frontend}:8000",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(UserRouter)
app.include_router(AssignmentsRouter)
app.include_router(HistoryRouter)
app.include_router(StatisticsRouter)
app.include_router(ChangesRouter)
app.include_router(ConfigurationRouter)


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.post("/token", tags=[ApiTags.AUTH])
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> TokenModel:
    """Authenticate a user and issue an access token."""
    security = SecurityController()
    user = security.authenticate_user(username=form_data.username, password=form_data.password)
    if not user:
        raise BusinessError(http_status.HTTP_401_UNAUTHORIZED, "User incorrect")
    access_token_expires = timedelta(minutes=security.access_token_expire_minutes)
    access_token = security.create_access_token(data={"sub": user.username})
    return TokenModel(access_token=access_token, token_type=security.token_type_access)
