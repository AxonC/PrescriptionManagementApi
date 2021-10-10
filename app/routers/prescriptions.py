""" Module containing API functions relating to prescriptions """
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Path
from uuid import UUID

from metomi.isodatetime.parsers import TimeRecurrenceParser
from metomi.isodatetime.exceptions import ISO8601SyntaxError

from database.queries.bloodwork_queries import create_bloodwork_request, get_request_by_id_in_practice
from database.queries.medication_queries import get_medication_by_id
from database.queries.medical_practice_queries import get_medical_practice
from database.queries.user_queries import get_user_by_username
from database.queries.pharmacies_queries import get_pharmacy, get_users_pharmacy_assignment
from database.queries.prescriptions_queries import (
    create_prescription,
    get_prescription,
    update_prescription,
    delete_prescription,
    get_prescriptions_of_institution,
    mark_prescription_approved,
    get_bloodwork_request_for_prescription,
    mark_prescription_issued,
    get_prescription_by_code
)
from models.auth import User
from models.base import Response
from models.medication import Medication
from models.prescriptions import (
    BasePrescription,
    PrescriptionCreatedResponse,
    PrescriptionModifyRequest,
    Prescription,
    PrescriptionListing
)
from models.base import Institution, InstitutionTypes
from permissions import PermissionsChecker

from helpers import check_valid_uuid, UUIDPathChecker

router = APIRouter()

LOGGER = logging.getLogger(__name__)

def check_medication(medication_id: str) -> Medication:
    """ Check for the existence of a given medication """
    if (medication := get_medication_by_id(medication_id)) is None:
        LOGGER.info('Medication with id %s not found', medication_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Medication invalid.')
    return Medication(**medication)


def check_iso8601_time_statement(time_statement: str) -> str:
    """ Check a given timestatement meats the ISO requirements for syntax """
    try:
        # validates the time statement as a valid ISO8061 time recurrence statement.
        parsed_statement = TimeRecurrenceParser().parse(time_statement)
    except ISO8601SyntaxError as exc:
        LOGGER.exception('Time statement not valid %s', time_statement)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Time statement invalid.'
        ) from exc
    return str(parsed_statement)


@router.get('',
    response_model=Response[List[PrescriptionListing]]
)
def get_prescriptions_for_users_institution(
    user: User = Depends(PermissionsChecker(['prescription.list']))
):
    """ List the prescriptions created in the institution of the requesting user """
    return {'data': [PrescriptionListing(**pl)
        for pl in get_prescriptions_of_institution(user.institution_id)]}

@router.post('/{username}/create',
    response_model=PrescriptionCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user_repeat_prescription(
    username: str,
    prescription: BasePrescription,
    requesting_user: User = Depends(PermissionsChecker(['prescription.create'])),
):
    """ Create a repeat prescription for a given user.

        Time statement given must be a valid ISO8601 recurring time interval.

        Exceptions:
            400 - Given user is not found.
            400 - Institution is either invalid or not found.
            400 - When medication is not found.

        Returns:
            UUID of prescription created.
    """
    LOGGER.info('Request to create prescription for %s', username)
    if (user := next(get_user_by_username(username), None)) is None:
        LOGGER.info('User %s not found to create prescription for', username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User not found.')
    user: User = User(**user)

    # Check that the requesting user's institution is a medical practice.
    if get_medical_practice(requesting_user.institution_id) is None:
        LOGGER.debug('Institution %s is not a medical practice or not found', requesting_user.institution_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Institution invalid.')

    # if the user does not belong to a pharmacy
    if (pharmacy_assignment := get_users_pharmacy_assignment(user.username)) is None:
        LOGGER.debug('User does not have a pharmacy assignment %s', user.username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Pharmacy assignment not found.')

    # if the user the prescription is being filed against is not part of a medical practice
    if get_medical_practice(user.institution_id) is None:
        LOGGER.debug('User does not belong to medical practice %s', user.institution_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User does not belong to medical practice.')

    medication: Medication = check_medication(prescription.medication_id)

    recurrance_string = check_iso8601_time_statement(prescription.time_statement)

    # update the prescription with the validated string.
    prescription.time_statement = str(recurrance_string)

    LOGGER.debug('Creating prescription')
    prescription_id = create_prescription(
        prescription=prescription, 
        institution_id=pharmacy_assignment[1], 
        created_by_institution_id=requesting_user.institution_id,
        username=user.username
    )
    LOGGER.info('Prescription created with id %s', prescription_id)

    request_id = None
    if medication.bloodwork_requirement is not None:
        LOGGER.info('Medication %s requires bloodwork', medication.medication_id)
        request_id = create_bloodwork_request(
            prescription_id=prescription_id,
            practice_id=requesting_user.institution_id, # create the request within the medical practice.
            request_type=medication.bloodwork_requirement.value
        )

    return {'prescription_id': prescription_id, 'bloodwork_request_id': request_id}

def _get_prescription(prescription_id = Path(...)) -> Prescription:
    """ Get a prescription by its ID """
    if (prescription := get_prescription(prescription_id=prescription_id)) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Prescription not found.')
    return Prescription(**prescription)

@router.get('/code/{short_code}',
    response_model=Prescription,
    dependencies=[Depends(PermissionsChecker(['prescription.short-code']))]
)
def get_prescription_by_short_code(short_code: str):
    """ Get the prescription by its short code """
    try:
        prescription_id = get_prescription_by_code(short_code)['prescription_id']
    except TypeError as exc: # TypeError thrown if the query returns a NoneType
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Prescription not found.'
        ) from exc

    return _get_prescription(prescription_id=prescription_id)

@router.patch('/{prescription_id}',
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(PermissionsChecker(['prescription.modify'])),
        Depends(UUIDPathChecker(['prescription_id']))
    ]
)
def modify_existing_prescription(
    prescription_changes: PrescriptionModifyRequest,
    prescription: Prescription = Depends(_get_prescription),
):
    """ Modify the time statement or medication of an existing prescription """
    LOGGER.info('Request received to modify prescription')

    if prescription_changes.medication_id is not None:
        check_medication(medication_id=prescription_changes.medication_id)

    if prescription_changes.time_statement is not None:
        check_iso8601_time_statement(time_statement=prescription_changes.time_statement)

    # update the attributes if they have been provided.
    LOGGER.debug('Changing %s attributes on prescription %s', prescription_changes.dict(exclude_unset=True), prescription.prescription_id)
    updated_prescription = prescription.copy(update=prescription_changes.dict(exclude_unset=True))

    # pass fields to update query
    update_prescription(updated_prescription)

    return {'prescription_id': updated_prescription.prescription_id}

@router.patch('/{prescription_id}/approve',
    dependencies=[
        Depends(UUIDPathChecker(['prescription_id'])),
        Depends(PermissionsChecker(['prescription.approve']))
    ],
    status_code=status.HTTP_204_NO_CONTENT
)
def mark_prescription_as_approved(prescription: Prescription = Depends(_get_prescription)):
    """ Mark a prescription as being approved """
    LOGGER.info('Request to approve prescription %s', prescription.prescription_id)
    if prescription.approved_at is not None:
        LOGGER.info('Prescription %s already approved', prescription.prescription_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Prescription already approved.'
        )

    bloodwork_request_details = get_bloodwork_request_for_prescription(prescription_id=prescription.prescription_id)
    # if bloodwork is mandated via a linked requests, and it is in complete
    if bloodwork_request_details['request_id'] is not None and bloodwork_request_details['completed_at'] is None:
        LOGGER.info('Bloodwork incomplete for %s', prescription.prescription_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Bloodwork incomplete.')

    mark_prescription_approved(prescription_id=prescription.prescription_id)
    LOGGER.debug('Prescription %s marked as approved', prescription.prescription_id)

    return {}

@router.patch('/{prescription_id}/issue',
    dependencies=[Depends(UUIDPathChecker(['prescription_id']))],
    status_code=status.HTTP_204_NO_CONTENT
)
def mark_prescription_as_issued(
    prescription: Prescription = Depends(_get_prescription),
    issuing_user: User = Depends(PermissionsChecker(['prescription.issue']))
):
    """ Mark a prescription as issued and record the issuing user """
    LOGGER.info('Request to issue medication for prescription %s', prescription.prescription_id)

    if prescription.institution_id != issuing_user.institution_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Wrong institution.')

    if prescription.issued_at is not None or prescription.issued_by is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Prescription already issued.')

    if prescription.approved_at is None:
        LOGGER.info('Prescription %s not approved for issue', prescription.prescription_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Prescription not approved for issue.')

    mark_prescription_issued(
        prescription_id=prescription.prescription_id,
        issuing_user=issuing_user.username
    )

    return {}

@router.delete('/{prescription_id}',
    dependencies=[
        Depends(PermissionsChecker(['prescription.delete'])),
        Depends(UUIDPathChecker(['prescription_id']))
    ],
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user_repeat_prescription(
    prescription: Prescription = Depends(_get_prescription)
):
    """ Delete a repeat prescription with the given prescription_id.

        Exceptions:
            404 - Prescription is not found.
            500 - Connection to the database is lost.
    """
    LOGGER.info('Request to delete prescription with id %s', prescription.prescription_id)

    if delete_prescription(prescription_id=prescription.prescription_id):
        LOGGER.info('Prescription deleted with id %s', prescription.prescription_id)
    else:
        LOGGER.error('Failed to perform deletion operation for prescription with id %s', prescription.prescription_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Lost connection to the database')
