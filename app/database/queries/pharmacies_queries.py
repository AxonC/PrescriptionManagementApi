""" Module containing all queries for pharmacies """
from typing import Generator
import uuid

from database.connection import get_cursor
from models.base import BaseInstitution, InstitutionTypes

def create_pharmacy(pharmacy: BaseInstitution) -> str:
    """ Insert a medical practice into the database. """

    pharmacy_id = str(uuid.uuid4())
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
                pharmacy_id,
                InstitutionTypes.PHARMACY.value,
                pharmacy.name,
                pharmacy.address_line_1,
                pharmacy.address_line_2,
                pharmacy.address_line_3,
                pharmacy.address_line_4,
                pharmacy.city,
                pharmacy.state,
                pharmacy.postcode,
            )
        )
    return pharmacy_id

def get_pharmacies() -> Generator:
    """ Get a list of all pharmacies """
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT institution_id, institution_type, name, address_line_1, 
                    address_line_2, address_line_3, address_line_4, 
                    city, state, postcode
                FROM institutions
                WHERE institution_type = %s
            """, (InstitutionTypes.PHARMACY.value,))
        yield from cursor.fetchall()

def get_pharmacy(pharmacy_id: str) -> dict:
    """ Get the details of a pharmacy """
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT institution_id, institution_type, name, address_line_1, 
                address_line_2, address_line_3, address_line_4, 
                city, state, postcode
            FROM institutions
            WHERE institution_id = %s
            AND institution_type = %s;""", (pharmacy_id, InstitutionTypes.PHARMACY.value)
        )
        return cursor.fetchone()

def delete_pharmacy(pharmacy_id: str):
    """ Delete a pharmacy from the institutions table """
    with get_cursor() as cursor:
        cursor.execute(
            """DELETE FROM institutions WHERE institution_id = %s AND institution_type = %s""",
            (pharmacy_id, InstitutionTypes.PHARMACY.value))

def set_users_pharmacy(pharmacy_id: str, username: str):
    """ Insert or update users' pharmacy assignment """
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO pharmacy_assignments (username, institution_id)
                VALUES(%s, %s)
                ON CONFLICT (username, institution_id)
                DO UPDATE SET institution_id = EXCLUDED.institution_id;
            """,
            (username, pharmacy_id)
        )

def get_users_pharmacy_assignment(username: str):
    """ Get the preferred pharmacy of a user """
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT username, institution_id FROM pharmacy_assignments
                WHERE username = %s;""",
            (username,)
        )
        return cursor.fetchone()
