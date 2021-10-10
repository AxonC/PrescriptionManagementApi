from typing import Generator

from database.connection import get_cursor
from models.auth import User, BaseUser

def get_user_by_username(username: str) -> Generator:
    """ Get a user from the database by its username """
    with get_cursor() as cursor:
        cursor.execute("SELECT username, password, email, name, institution_id FROM users WHERE username = %s", (username,))
        yield cursor.fetchone()

def get_pending_user_by_username(username: str) -> Generator:
    """ Get a user from the pending users table by its username with the type of institution """
    with get_cursor() as cursor:
        cursor.execute("""SELECT pu.username, pu.name, pu.email, i.institution_id, i.institution_type FROM pending_users as pu
        JOIN institutions as i USING (institution_id)
        WHERE username = %s""", (username,))
        yield cursor.fetchone()

def create_pending_user(user: BaseUser, institution_id: str) -> None:
    """ Create a user pending the registration process """
    with get_cursor() as cursor:
        CREATE_STMT = """INSERT INTO pending_users (username, name, email, institution_id)
                         VALUES (%s, %s, %s, %s);"""
        cursor.execute(CREATE_STMT, (user.username, user.name, user.email, institution_id))

def delete_pending_user(username: str) -> None:
    """ Delete a pending user """
    with get_cursor() as cursor:
        DELETE_STMT = "DELETE FROM pending_users WHERE username = %s;"
        cursor.execute(DELETE_STMT, (username,))

def get_users() -> Generator:
    """ Get all users stored in the database returning a generator"""
    with get_cursor() as cursor:
        cursor.execute("SELECT username, name FROM users")
        yield from cursor.fetchall()

def create_user(user: User, institution_id: str = None) -> Generator:
    """ Create a user in the database. Password should be pre-hashed before being
        passed into this function.

        Returns the new user if successfully created.
    """
    CREATE_STMT = """INSERT INTO users (username, name, email, password, institution_id)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING (username)"""
    with get_cursor() as cursor:
        cursor.execute(CREATE_STMT, (user.username, user.name, user.email, user.password, institution_id))
        yield cursor.fetchone()

def get_user_permissions(username: str) -> Generator:
    """ Get the users permissions based upon their assigned roles

        Returns the list of permissions (id, name).
    """
    QUERY = """SELECT DISTINCT(p.permission_id), p.name FROM roles as r
                JOIN role_by_user rbu USING(role_id)
                JOIN permissions_by_role pbr USING(role_id)
                JOIN permissions p USING(permission_id)
                WHERE rbu.username = %s;
            """
    with get_cursor() as cursor:
        cursor.execute(QUERY, (username,))
        yield from cursor.fetchall()


def get_user_by_username_with_permissions(username: str) -> Generator:
    """ Query the details for a role and merge with its permissions """
    SELECT_USER_DETAILS = """SELECT username, email, name FROM users WHERE username = %s"""

    SELECT_ROLE_PERMISSIONS = """SELECT p.permission_id, p.name FROM users as u, roles as r
                JOIN role_by_user rbu USING(role_id)
                JOIN permissions_by_role pbr USING(role_id)
                JOIN permissions p USING(permission_id)
                WHERE u.username = %s AND rbu.username = %s;
            """
    with get_cursor() as cursor:
        cursor.execute(SELECT_USER_DETAILS, (username,))
        user_details = cursor.fetchone()
        if user_details is None:
            yield None

        cursor.execute(SELECT_ROLE_PERMISSIONS, (username, username,))
        role_permissions = cursor.fetchall()

        yield {**user_details, 'permissions': [dict(rp) for rp in role_permissions]}

def get_users_by_institution_with_roles(institution_id: str):
    """ Get the details of users in an institution with an array of their roles
        aggregated.
    """
    with get_cursor() as cursor:
        cursor.execute("""SELECT username, users.name, users.email, array_agg(roles.name) roles FROM users
                    JOIN role_by_user USING(username)
                    JOIN roles USING (role_id)
                    WHERE institution_id = %s
                    GROUP BY username""",
                    (institution_id,)
                )
        yield from cursor.fetchall()
