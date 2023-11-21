import logging
from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv, find_dotenv
from sqlalchemy.engine import URL


@dataclass
class DatabaseConfig:
    """Database connection variables"""
    load_dotenv(find_dotenv(".env"))
    name: str = getenv("POSTGRES_DB")
    user: str = getenv("POSTGRES_USER", "docker")
    passwd: str = getenv("POSTGRES_PASSWORD", None)
    port: int = getenv("POSTGRES_PORT", 5065)
    host: str = getenv("POSTGRES_HOST", "db")
    driver: str = "asyncpg"
    database_system: str = "postgresql"

    def build_connection_str(self) -> str:
        """
        This function build a connection string
        """
        return URL.create(
            drivername=f"{self.database_system}+{self.driver}",
            username=self.user,
            database=self.name,
            password=self.passwd,
            port=self.port,
            host=self.host
        ).render_as_string(hide_password=False)


@dataclass
class Configuration:
    """All in one configuration's class"""
    debug = bool(getenv("DEBUG"))
    logging_level = int(getenv("LOGGING_LEVEL", logging.INFO))

    db = DatabaseConfig()


conf = Configuration()
