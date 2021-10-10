""" Module to store the connection cursor for the database """
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import DictCursor

from config import DBConfig


@contextmanager
def get_cursor():
    """ Get a database cursor for the configured database.
        Yields:
            cursor - cursor to the database.
    """
    connection = psycopg2.connect(
        database=DBConfig.NAME,
        user=DBConfig.USERNAME,
        password=DBConfig.PASSWORD,
        host=DBConfig.ADDRESS
    )

    with connection:
        connection.autocommit = True
        with connection.cursor(cursor_factory=DictCursor) as cursor:
            yield cursor

    connection.close()
