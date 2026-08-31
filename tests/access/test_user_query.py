from datetime import date

from icm.access import UserModel, UserQuery
from icm.constants import RoleTypes, UserStatusTypes
from icm.data import Database, UserSchema


def _new_user_model(**overrides) -> UserModel:
    fields = dict(
        username="Weird_Case",
        password="hashed-password",
        name="john",
        lastname="doe",
        status="active",
        role="admin",
        created_at=None,
        updated_at=None,
    )
    fields.update(overrides)
    return UserModel(**fields)


def test_insert_normalizes_casing_of_every_field(database: Database):
    query = UserQuery()
    assert query.insert(_new_user_model()) is True

    with database.session() as session:
        user = session.get(UserSchema, "weird_case")
        assert user is not None
        assert user.name == "John"
        assert user.lastname == "Doe"
        assert user.status == UserStatusTypes.ACTIVE
        assert user.role == RoleTypes.ADMIN


def test_insert_duplicate_username_fails_gracefully(database: Database):
    query = UserQuery()
    assert query.insert(_new_user_model(username="dup_user")) is True
    assert query.insert(_new_user_model(username="dup_user")) is False

    with database.session() as session:
        assert session.query(UserSchema).count() == 1


def test_update_changes_fields_but_not_password(database: Database, existing_user: str):
    query = UserQuery()
    updated = query.update(
        UserModel(
            username=existing_user,
            password="",
            name="renamed",
            lastname="user",
            status=UserStatusTypes.INACTIVE,
            role=RoleTypes.ADMIN,
            created_at=None,
            updated_at=None,
        )
    )
    assert updated is True

    with database.session() as session:
        user = session.get(UserSchema, existing_user)
        assert user.name == "Renamed"
        assert user.status == UserStatusTypes.INACTIVE
        assert user.role == RoleTypes.ADMIN
        assert user.password == "hashed-password"
        assert user.updated_at == date.today()


def test_update_nonexistent_user_returns_false(database: Database):
    query = UserQuery()
    assert (
        query.update(
            UserModel(
                username="ghost",
                password="",
                name="ghost",
                lastname="user",
                status=UserStatusTypes.ACTIVE,
                role=RoleTypes.USER,
                created_at=None,
                updated_at=None,
            )
        )
        is False
    )


def test_update_password_changes_only_the_password(database: Database, existing_user: str):
    query = UserQuery()
    assert query.update_password(existing_user, "new-hashed-password") is True

    with database.session() as session:
        user = session.get(UserSchema, existing_user)
        assert user.password == "new-hashed-password"
        assert user.name == "Fixture"


def test_update_password_nonexistent_user_returns_false(database: Database):
    query = UserQuery()
    assert query.update_password("ghost", "new-hashed-password") is False


def test_delete_removes_only_the_requested_users(
    database: Database, existing_user: str, another_existing_user: str
):
    query = UserQuery()
    assert query.delete([existing_user]) is True

    with database.session() as session:
        assert session.get(UserSchema, existing_user) is None
        assert session.get(UserSchema, another_existing_user) is not None


def test_delete_tolerates_a_nonexistent_username_mixed_in(
    database: Database, existing_user: str
):
    query = UserQuery()
    assert query.delete([existing_user, "ghost"]) is True

    with database.session() as session:
        assert session.get(UserSchema, existing_user) is None


def test_get_roundtrips_expected_fields(database: Database, existing_user: str):
    query = UserQuery()
    user = query.get(existing_user)
    assert user is not None
    assert user.username == existing_user
    assert user.name == "Fixture"
    assert user.status == UserStatusTypes.ACTIVE
    assert user.created_at == date.today().strftime("%Y-%m-%d")
    assert user.updated_at is None


def test_get_nonexistent_user_returns_none(database: Database):
    assert UserQuery().get("ghost") is None


def test_get_all_includes_deleted_users(database: Database):
    query = UserQuery()
    query.insert(_new_user_model(username="active_one", status=UserStatusTypes.ACTIVE))
    query.insert(_new_user_model(username="deleted_one", status=UserStatusTypes.DELETED))

    usernames = {user.username for user in query.get_all()}
    assert usernames == {"active_one", "deleted_one"}


def test_get_users_excludes_deleted(database: Database):
    query = UserQuery()
    query.insert(_new_user_model(username="active_one", status=UserStatusTypes.ACTIVE))
    query.insert(_new_user_model(username="deleted_one", status=UserStatusTypes.DELETED))

    usernames = {user.username for user in query.get_users()}
    assert usernames == {"active_one"}


def test_get_deleted_only_returns_deleted(database: Database):
    query = UserQuery()
    query.insert(_new_user_model(username="active_one", status=UserStatusTypes.ACTIVE))
    query.insert(_new_user_model(username="deleted_one", status=UserStatusTypes.DELETED))

    usernames = {user.username for user in query.get_deleted()}
    assert usernames == {"deleted_one"}


def test_get_users_by_category_filters_status_and_role_together(database: Database):
    query = UserQuery()
    query.insert(
        _new_user_model(username="active_admin", status=UserStatusTypes.ACTIVE, role="admin")
    )
    query.insert(
        _new_user_model(username="active_user", status=UserStatusTypes.ACTIVE, role="user")
    )
    query.insert(
        _new_user_model(username="inactive_admin", status=UserStatusTypes.INACTIVE, role="admin")
    )

    result = query.get_users_by_category(UserStatusTypes.ACTIVE, RoleTypes.ADMIN)
    assert [user.username for user in result] == ["active_admin"]
