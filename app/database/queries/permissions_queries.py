from typing import Generator
from uuid import UUID

from database.connection import get_cursor

def get_all_permissions() -> Generator:
    """ Get all permissions """
    SELECT_STMT = """SELECT permission_id, name FROM permissions;"""

    with get_cursor() as cursor:
        cursor.execute(SELECT_STMT)
        yield from cursor.fetchall()

def get_permission_by_id(permssion_id: UUID) -> Generator:
    """ Get a permission by its UUID """
    SELECT_STMT = """SELECT permisssion_id, name FROM permissions
                     WHERE permission_id = %s;"""

    with get_cursor() as cursor:
        cursor.execute(SELECT_STMT, (str(permssion_id),))
        yield cursor.fetchone()
