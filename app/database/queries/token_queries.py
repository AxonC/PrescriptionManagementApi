from typing import Generator
import uuid

from database.connection import get_cursor
from models.base import RegistrationType

def get_active_token(token_id: str) -> Generator:
    with get_cursor() as cursor:
        SELECT_STMT = """SELECT token_id, token_type, username FROM registration_tokens
                         WHERE token_id = %s;"""
        cursor.execute(SELECT_STMT, (token_id,))
        yield cursor.fetchone()

def create_registration_token(username: str, token_type: RegistrationType) -> Generator:
    """ Create token with a given type of user to be resolved upon conversion. """
    token_id = uuid.uuid4()
    with get_cursor() as cursor:
        INSERT_STMT = """INSERT INTO registration_tokens (token_id, token_type, username)
                         VALUES(%s, %s, %s)
                         RETURNING token_id;"""
        cursor.execute(INSERT_STMT, (str(token_id), token_type, username))
        yield cursor.fetchone()
