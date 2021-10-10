""" Medication queries """
from typing import List

from database.connection import get_cursor

def get_medications() -> List[dict]:
    """ Get a list of all medications """
    with get_cursor() as cursor:
        cursor.execute("SELECT medication_id, medication_name, bloodwork_requirement FROM medications")
        return cursor.fetchall()

def get_medication_by_id(medication_id: str) -> dict:
    """ Get medication by its UUID """
    with get_cursor() as cursor:
        cursor.execute("SELECT medication_id, medication_name, bloodwork_requirement FROM medications WHERE medication_id = %s;", (medication_id,))
        return cursor.fetchone()
