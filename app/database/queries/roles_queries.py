from typing import Generator

import uuid

from database.connection import get_cursor
from models.permissions_roles import Role

def get_roles() -> Generator:
    """ Get all roles contained in the application """
    SELECT_STMT = "SELECT role_id, name, description FROM roles;"

    with get_cursor() as cursor:
        cursor.execute(SELECT_STMT)
        yield from cursor.fetchall()

def get_role_by_id(role_id: uuid.UUID) -> Generator:
    """ Get a role by its UUID """
    SELECT_ROLE_DETAILS = """SELECT role_id, name, description FROM roles
                            WHERE role_id = %s;"""
    with get_cursor() as cursor:
        cursor.execute(SELECT_ROLE_DETAILS, (str(role_id),))
        role_details = cursor.fetchone()
        yield role_details if role_details is not None else None


def get_role_with_permissions(role_id: uuid.UUID) -> Generator:
    """ Query the details for a role and merge with its permissions """
    SELECT_ROLE_DETAILS = """SELECT role_id, name, description FROM roles
                             WHERE role_id = %s;"""

    SELECT_ROLE_PERMISSIONS = """SELECT p.name, p.permission_id from roles
                                INNER JOIN permissions_by_role pbr USING(role_id)
                                INNER JOIN permissions p USING (permission_id)
                                WHERE role_id = %s;"""

    with get_cursor() as cursor:
        cursor.execute(SELECT_ROLE_DETAILS, (str(role_id),))
        role_details = cursor.fetchone()
        if role_details is None:
            yield None

        cursor.execute(SELECT_ROLE_PERMISSIONS, (str(role_id),))
        role_permissions = cursor.fetchall()

        yield {**role_details, 'permissions': [dict(rp) for rp in role_permissions]}

def create_role(name: str, description: str) -> Generator:
    """ Insert a new role into the database. """
    role_id = uuid.uuid4()
    INSERT_STMT = """INSERT INTO roles (role_id, name, description)
                     VALUES (%s, %s, %s)
                     RETURNING (role_id);"""
    with get_cursor() as cursor:
        cursor.execute(INSERT_STMT, (str(role_id), name, description))
        yield from cursor.fetchone()

def add_permission_to_role(role_id: uuid.UUID, permission_id: uuid.UUID):
    """ Associate a permission with a role. The check forexistence of
        the permission should be performed before calling this function
    """
    INSERT_STMT = """INSERT INTO permissions_by_role (permission_id, role_id)
                     VALUES (%s, %s);"""

    with get_cursor() as cursor:
        cursor.execute(INSERT_STMT, (str(permission_id), str(role_id)))

def remove_existing_permissions_for_role(role_id: uuid.UUID):
    """ Reset a users' permissions """
    DELETE_STMT = """DELETE FROM permissions_by_role
                     WHERE role_id = %s;"""

    with get_cursor() as cursor:
        cursor.execute(DELETE_STMT, (str(role_id),))

def add_role_to_user(username: str, role_id: uuid.UUID):
    """ Associate a role with a user """
    INSERT_STMT = """INSERT INTO role_by_user (role_id, username)
                     VALUES(%s, %s);"""
    with get_cursor() as cursor:
        cursor.execute(INSERT_STMT, (str(role_id), username))

def remove_existing_roles_for_user(username: str):
    """ Delete all role assignments for a user. """
    DELETE_STMT = """DELETE FROM role_by_user
                     WHERE username = %s;"""

    with get_cursor() as cursor:
        cursor.execute(DELETE_STMT, (username,))
