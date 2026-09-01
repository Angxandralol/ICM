from pydantic import BaseModel


class UserModel(BaseModel):
    username: str
    password: str
    name: str
    lastname: str
    status: str
    role: str
    created_at: str | None
    updated_at: str | None


class UserPublicModel(BaseModel):
    """`UserModel` without `password` -- the shape returned to HTTP clients."""

    username: str
    name: str
    lastname: str
    status: str
    role: str
    created_at: str | None
    updated_at: str | None


class UserLoggedModel(BaseModel):
    username: str
    name: str
    lastname: str
    status: str
    role: str
    can_assign: bool
    can_receive_assignment: bool
    view_information_global: bool


class UpdateUserModel(BaseModel):
    username: str
    name: str
    lastname: str
    status: str
    role: str


class UpdatePasswordModel(BaseModel):
    password: str