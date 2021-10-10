""" Medical practice queries """
from typing import Generator
import uuid

from database.connection import get_cursor
from models.base import BaseInstitution, InstitutionTypes

def get_medical_practices() -> Generator:
    """ Retrieve all medical practices from the database """
    with get_cursor() as cursor:
        cursor.execute("""SELECT institution_id, institution_type, name, address_line_1,
                address_line_2, address_line_3, address_line_4, 
                city, state, postcode
                FROM institutions
                WHERE institution_type = %s
                """, (InstitutionTypes.MEDICAL_PRACTICE.value,))
        yield from cursor.fetchall()

def create_medical_practice(medical_practice: BaseInstitution):
    """ Insert a medical practice into the database. """

    practice_id = str(uuid.uuid4())
    with get_cursor() as cursor:
        CREATE_STMT = """INSERT INTO institutions (
                institution_id, institution_type, name, address_line_1, 
                address_line_2, address_line_3, address_line_4, 
                city, state, postcode
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(
            CREATE_STMT,
            (
                practice_id,
                InstitutionTypes.MEDICAL_PRACTICE.value,
                medical_practice.name,
                medical_practice.address_line_1,
                medical_practice.address_line_2,
                medical_practice.address_line_3,
                medical_practice.address_line_4,
                medical_practice.city,
                medical_practice.state,
                medical_practice.postcode,
            )
        )
    return practice_id

def get_medical_practice(practice_id: str):
    """ Get a medical practice by its UUID """
    with get_cursor() as cursor:
        SELECT_STMT = """SELECT institution_id, institution_type, name, address_line_1, 
                address_line_2, address_line_3, address_line_4, 
                city, state, postcode FROM institutions
                WHERE institution_type = %s
                AND institution_id = %s;"""
        cursor.execute(SELECT_STMT, (InstitutionTypes.MEDICAL_PRACTICE.value, practice_id))
        return cursor.fetchone()

def assign_gp_to_practice(practice_id: str, username: str):
    with get_cursor() as cursor:
        SELECT_STMT = """INSERT INTO institutions (institution_id, username)
                         VALUES (%s, %s);"""
        cursor.execute(SELECT_STMT, (practice_id, username))
