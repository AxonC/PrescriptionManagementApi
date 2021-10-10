""" Module handling queries pertaining to bloodwork """
import uuid
from datetime import datetime

from models.medication import MedicationBloodworkTypes
from database.connection import get_cursor

def get_requests_by_practice(practice_id: str, completed: bool = False):
    """ Get the requests in a practice. """
    query = ''
    if completed:
        query = """SELECT request_id, request_type, br.prescription_id, practice_id, completed_at, rp.username, md.medication_name, u.name, i.name as pharmacy_name
                FROM blood_requests br
                JOIN repeat_prescriptions rp USING (prescription_id)
                JOIN medications md USING(medication_id)
                JOIN users u USING (username)
                JOIN institutions i on br.practice_id = i.institution_id
                WHERE practice_id = %s;"""
    else:
        query = """SELECT request_id, request_type, br.prescription_id, practice_id, completed_at, rp.username, md.medication_name, u.name, i.name as pharmacy_name
                FROM blood_requests br
                JOIN repeat_prescriptions rp USING (prescription_id)
                JOIN medications md USING(medication_id)
                JOIN users u USING (username)
                JOIN institutions i on br.practice_id = i.institution_id
                WHERE practice_id = %s AND completed_at IS NULL;"""
    with get_cursor() as cursor:
        cursor.execute(query, (practice_id,))
        return cursor.fetchall()

def get_request_by_id(request_id: str) -> dict:
    """ Get bloodwork request by its ID """
    with get_cursor() as cursor:
        cursor.execute("""SELECT request_id, request_type, prescription_id, practice_id, completed_at FROM blood_requests
                        WHERE request_id = %s;""", (request_id,))
        return cursor.fetchone()

def get_request_by_id_in_practice(request_id: str, practice_id: str) -> dict:
    """ Get bloodwork request by its ID in a given practice """
    with get_cursor() as cursor:
        cursor.execute("""SELECT request_id, request_type, br.prescription_id, practice_id, completed_at, rp.username, md.medication_name, u.name, i.name as pharmacy_name
                FROM blood_requests br
                JOIN repeat_prescriptions rp USING (prescription_id)
                JOIN medications md USING(medication_id)
                JOIN users u USING (username)
                JOIN institutions i on br.practice_id = i.institution_id
                        WHERE request_id = %s AND practice_id = %s;""", (request_id, practice_id))
        return cursor.fetchone()

def create_bloodwork_request(
    prescription_id: str,
    practice_id: str,
    request_type: MedicationBloodworkTypes
) -> str:
    """ Create a request for bloodwork to be completed """
    with get_cursor() as cursor:
        request_id = str(uuid.uuid4())
        cursor.execute("""INSERT INTO blood_requests 
                        (request_id, request_type, prescription_id, practice_id)
                        VALUES (%s, %s, %s, %s);""",
                        (request_id, request_type, prescription_id, practice_id)
                    )
        return request_id

def mark_bloodwork_request_complete(request_id: str):
    """ Mark a blood work request as complete """
    with get_cursor() as cursor:
        completed_at = datetime.utcnow().isoformat()
        cursor.execute("""UPDATE blood_requests SET completed_at = %s WHERE request_id = %s;""", (completed_at, request_id,))
