""" Module containing prescription-related queries """
import logging
import uuid
from uuid import UUID
from datetime import datetime
from database.connection import get_cursor
from random import randint, seed

from models.prescriptions import BasePrescription, Prescription

LOGGER = logging.getLogger(__name__)

def create_prescription(
    prescription: BasePrescription,
    institution_id: str,
    username: str,
    created_by_institution_id: str
) -> str:
    """ Create prescription """
    with get_cursor() as cursor:
        prescription_id = str(uuid.uuid4())
        seed(1)
        # generate an 8 digit random number
        short_code = randint(00000000, 99999999)
        cursor.execute(
            """INSERT INTO repeat_prescriptions (
                prescription_id,
                medication_id,
                time_statement,
                institution_id,
                created_by_institution_id,
                username,
                short_code
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s);"""
            ,
            (
                prescription_id,
                str(prescription.medication_id),
                prescription.time_statement,
                institution_id,
                created_by_institution_id,
                username,
                short_code
            )
        )
    return str(prescription_id)

def get_prescription(prescription_id: str) -> dict:
    """ Get a prescription by its UUID """
    with get_cursor() as cursor:
        cursor.execute(
            """SELECT prescription_id, medication_id, time_statement, institution_id, username, approved_at,
                issued_at, issued_by, short_code
                FROM repeat_prescriptions
                WHERE prescription_id = %s;
            """,
            (prescription_id,)
        )
        return cursor.fetchone()

def update_prescription(prescription: Prescription) -> None:
    """ Update a prescription from its model representation.
        Only supports updating:
            time_statement
            medication_id
    """
    with get_cursor() as cursor:
        cursor.execute(
            """UPDATE repeat_prescriptions SET time_statement = %s, medication_id = %s
                WHERE prescription_id = %s""",
            (prescription.time_statement, prescription.medication_id, prescription.prescription_id)
        )

def delete_prescription(prescription_id: str):
    """ Delete prescription """
    try:
        with get_cursor() as cursor:
            cursor.execute(
                """DELETE FROM repeat_prescriptions
                WHERE prescription_id = %s;""",
                (prescription_id,)
            )
        return True
    except Exception as e:
        LOGGER.error(e)
        return False

def get_prescriptions_of_institution(institution_id: str):
    """ Get prescriptions of an institution with their related information """
    with get_cursor() as cursor:
        cursor.execute("""SELECT prescription_id, username, time_statement, m.medication_id, m.medication_name,
                    m.bloodwork_requirement, u.name, br.request_id, rp.institution_id, rp.approved_at, rp.issued_at, rp.short_code
                    FROM repeat_prescriptions rp
                    JOIN medications m USING(medication_id)
                    JOIN users u USING(username)
                    LEFT OUTER JOIN blood_requests br USING(prescription_id)
                    WHERE rp.institution_id = %s OR rp.created_by_institution_id = %s;""",
                (institution_id, institution_id)
            )
        yield from cursor.fetchall()

def mark_prescription_approved(prescription_id: str):
    """ Mark a prescription as having been approved. """
    timestamp = datetime.now().isoformat()
    with get_cursor() as cursor:
        cursor.execute("""UPDATE repeat_prescriptions SET approved_at = %s WHERE prescription_id = %s""", (timestamp, prescription_id))

def get_bloodwork_request_for_prescription(prescription_id: str) -> dict:
    """ Get the bloodwork request for a given prescription """
    with get_cursor() as cursor:
        cursor.execute("""SELECT rp.prescription_id, br.request_id, br.completed_at FROM repeat_prescriptions rp
                FULL JOIN blood_requests br on rp.prescription_id = br.prescription_id
                WHERE rp.prescription_id = %s""", (prescription_id,)
        )
        return cursor.fetchone()

def mark_prescription_issued(prescription_id: str, issuing_user: str):
    timestamp = datetime.now().isoformat()
    with get_cursor() as cursor:
        cursor.execute("""UPDATE repeat_prescriptions
                        SET issued_at = %s, issued_by = %s WHERE prescription_id = %s;""",
                        (timestamp, issuing_user, prescription_id)
                    )

def get_prescriptions_by_user(username: str):
    with get_cursor() as cursor:
        cursor.execute("""SELECT rp.prescription_id, i.name as pharmacy_name, md.medication_name, md.bloodwork_requirement, rp.approved_at, rp.issued_at, br.completed_at as bloodwork_completed_at FROM repeat_prescriptions rp
                        JOIN medications md USING (medication_id)
                        JOIN institutions i USING (institution_id)
                        FULL OUTER JOIN blood_requests br USING (prescription_id)
                        WHERE rp.username = %s""", (username,))
        return cursor.fetchall()

def get_prescription_by_code(short_code: str) -> dict:
    with get_cursor() as cursor:
        cursor.execute("SELECT prescription_id FROM repeat_prescriptions WHERE short_code = %s;", (short_code,))
        return cursor.fetchone()
