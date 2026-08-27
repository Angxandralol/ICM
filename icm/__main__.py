import click
import rich
from datetime import datetime
from icm.business import UserCLI, UpdaterHandler
from icm.data import Database
from icm.utils import Configuration, log

Configuration()


@click.group()
def cli():
    """INTERFACE CHANGE MONITOR

    System for monitoring interface changes of devices across the entire available network.
    """
    pass


@cli.command(help="Update information of interfaces")
@click.option("--reload", is_flag=True, help="Reload interface changes")
def updater(reload: bool):
    if not reload:
        log.info("Updating information of interfaces...")
        rich.print(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [gold1]Updating information of interfaces..."
        )
        system = UpdaterHandler()
        status = system.update()
        if status:
            log.info("Updater finished")
            rich.print(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [green3]Updater finished"
            )
        else:
            log.error("Updater failed")
            rich.print(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [red3]Updater failed"
            )
    else:
        log.info("Reloading interface changes...")
        rich.print(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [gold1]Reloading interface changes..."
        )
        system = UpdaterHandler()
        status = system.reload_changes()
        if status:
            log.info("Reloading interface changes finished")
            rich.print(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [green3]Reloading interface changes finished"
            )
        else:
            log.error("Reloading interface changes failed")
            rich.print(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [red3]Reloading interface changes failed"
            )


@cli.command(help="Database administrator")
@click.option("--start", is_flag=True, help="Create database tables")
@click.option("--drop", is_flag=True, help="Drop database tables with its data")
def database(start: bool, drop: bool):
    database = Database()
    if start:
        rich.print(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [gold1]Creating database tables..."
        )
        status = database.ensure_database_exists() and database.initialize()
        if status:
            rich.print(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [green3]Database tables created"
            )
        else:
            rich.print(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [red3]Database tables not created"
            )
    elif drop:
        rich.print(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [gold1]Dropping database tables..."
        )
        status = database.drop()
        if status:
            rich.print(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [green3]Database tables dropped"
            )
        else:
            rich.print(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [red3]Database tables not dropped"
            )


@cli.command(help="System administrator")
@click.option("--register", is_flag=True, help="Register a new user")
@click.option("--restore", is_flag=True, help="Restart password of a user")
def system(register: bool, restore: bool):
    if register:
        UserCLI.register()
    elif restore:
        UserCLI.restore_password()


if __name__ == "__main__":
    cli()

