"""Development-only database seed.

Lives outside `icm/` on purpose: it depends on `icm.data` schemas directly
to insert rows, something the `data/` layer itself must never do (see
REFACTOR.md, bug #13 — the previous `icm/data/sql/setup.py` violated the
layering by importing `business/` controllers). Never run this against a
database that holds real data.
"""

import os
import sys
from datetime import date, timedelta

import click

from icm.constants import RoleTypes, UserStatusTypes
from icm.data import Database, InterfaceSchema, UserSchema


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _refuse_if_production() -> None:
    if os.path.exists(os.path.join(_project_root(), ".env.production")):
        click.echo("Refusing to seed: a .env.production file is present.", err=True)
        sys.exit(1)


def main() -> None:
    _refuse_if_production()
    if not click.confirm(
        "This drops and recreates every table with throwaway data. Continue?",
        default=False,
    ):
        return

    database = Database()
    if not (database.ensure_database_exists() and database.drop() and database.initialize()):
        click.echo("Could not reset the database, see the logs above.", err=True)
        sys.exit(1)

    with database.session() as session:
        session.add_all(
            [
                UserSchema(
                    username="admin",
                    password="admin",
                    name="Admin",
                    lastname="Admin",
                    status=UserStatusTypes.ACTIVE,
                    role=RoleTypes.ADMIN,
                ),
                UserSchema(
                    username="user_a",
                    password="usertest",
                    name="User A",
                    lastname="Test",
                    status=UserStatusTypes.ACTIVE,
                    role=RoleTypes.USER,
                ),
                UserSchema(
                    username="user_b",
                    password="usertest",
                    name="User B",
                    lastname="Test",
                    status=UserStatusTypes.ACTIVE,
                    role=RoleTypes.USER,
                ),
            ]
        )

    # Same interface on two consecutive days, one of them with a status
    # flip, so the updater's comparison step has something to detect.
    devices = [
        ("1.1.1.1", "public1", "equipo1", 1),
        ("2.2.2.2", "public2", "equipo2", 2),
        ("3.3.3.3", "public3", "equipo3", 3),
    ]
    two_days_ago = date.today() - timedelta(days=2)
    one_day_ago = date.today() - timedelta(days=1)
    with database.session() as session:
        for consulted_at in (two_days_ago, one_day_ago):
            for ip, community, sysname, ifIndex in devices:
                session.add(
                    InterfaceSchema(
                        ip=ip,
                        community=community,
                        sysname=sysname,
                        ifIndex=ifIndex,
                        ifName=f"eth{ifIndex}",
                        ifDescr=f"ethernet{ifIndex}",
                        ifAlias=f"eth{ifIndex}",
                        ifHighSpeed=1000,
                        ifOperStatus="down(2)" if consulted_at == one_day_ago else "up(1)",
                        ifAdminStatus="up(1)",
                        consulted_at=consulted_at,
                    )
                )

    click.echo("Seed finished.")


if __name__ == "__main__":
    main()
