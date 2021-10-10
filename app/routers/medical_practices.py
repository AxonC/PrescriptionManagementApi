import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Response, Path
from psycopg2.errors import UniqueViolation

from models.base import Response, BaseInstitution, Institution, InstitutionCreateResponse, InstitutionTypes, RegistrationType
from models.auth import BaseUser, User
from mail.send import send_mail
from mail.templates import EmailTemplates

from database.queries.medical_practice_queries import (
    create_medical_practice,
    get_medical_practices,
    get_medical_practice
)
from database.queries.token_queries import create_registration_token
from database.queries.user_queries import create_pending_user

from auth import check_user_by_permissions, get_current_user, NOT_ALLOWED_EXCEPTION

from config import MAIL_FROM_ADDRESS, FRONT_END_BASE_URL
from helpers import check_valid_uuid
from common_functions import _handle_create_pending_user, _generate_email_template_signup_url

from permissions import PermissionsChecker

router = APIRouter()

LOGGER = logging.getLogger(__name__)

LIST_PERMISSIONS = [
    'practices.all'
]


@router.post("",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionsChecker(['practices.create']))],
    response_model=InstitutionCreateResponse
)
def create_new_medical_practice(
    medical_practice: BaseInstitution,
    master_user: BaseUser
):
    """ Create a new medical practice along with the master user and the
        registration token  to finish the process.
    """
    LOGGER.info('Request made to create medical practice %s', medical_practice.name)
    LOGGER.debug('Medical practice information: %s', medical_practice)
    try:
        institution_id = create_medical_practice(medical_practice=medical_practice)
    except UniqueViolation as exception:
        LOGGER.info('Practice with that name already found')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Practice already exists') from exception

    LOGGER.debug('Created institution with id %s', institution_id)

    _handle_create_pending_user(master_user, institution_id=institution_id)

    registration_token = next(
        create_registration_token(username=master_user.username, token_type=RegistrationType.MEDICAL_PRACTICE_ADMINISTRATOR.value)
    )

    template_object = _generate_email_template_signup_url(registration_token["token_id"])

    send_mail(master_user.email, master_user.name, EmailTemplates.MEDICAL_PRACTICE_SIGNUP.value, template_object)

    return {'institution_id': institution_id}


@router.get("",
    response_model=Response[List[Institution]],
    dependencies=[Depends(PermissionsChecker(LIST_PERMISSIONS))]
)
def get_all_medical_practices():
    """ Retrieve a list of all medical practices """
    return {"data": get_medical_practices()}


def _get_medical_practice(practice_id: str = Path(...)):
    """ Check the valid UUID for a medical practice & return it if found """
    practice_not_found_exception = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail='Practice not found'
    )

    LOGGER.debug(practice_id)
    if not check_valid_uuid(uuid=practice_id):
        LOGGER.info('Invalid uuid %s passed', practice_id)
        raise practice_not_found_exception

    practice_id = str(UUID(practice_id))
    if (practice := get_medical_practice(practice_id)) is None:
        LOGGER.debug('Medical practice %s not found', practice_id)
        raise practice_not_found_exception
    return Institution(**practice)

@router.post("/register/{entity}",
    status_code=status.HTTP_201_CREATED,
)
def register_to_medical_practice(
    user: BaseUser,
    entity: RegistrationType,
    requesting_user: User = Depends(get_current_user)
):
    """ Register a new GP in the specified medical practice """
    practice: Institution = _get_medical_practice(practice_id=requesting_user.institution_id)
    LOGGER.info('Request made to add %s to medical practice %s', entity.value, practice.institution_id)

    entity_required_permissions = {
        RegistrationType.GP: 'practice.register-gps',
        RegistrationType.PATIENT: 'practice.register-patients'
    }

    try:
        required_permissions = entity_required_permissions[entity]
        LOGGER.debug('Required permission selected: %s', required_permissions)
    except KeyError as exc:
        LOGGER.warning('Entity %s has no permissions assigned', entity)
        raise NOT_ALLOWED_EXCEPTION from exc

    check_user_by_permissions(permissions=[required_permissions], user=requesting_user)

    _handle_create_pending_user(user, institution_id=practice.institution_id)

    registration_token = next(
        create_registration_token(username=user.username, token_type=entity.value)
    )

    template_object = _generate_email_template_signup_url(registration_token['token_id'])

    # select the email template based upon the intended audience.
    templates = {
        RegistrationType.GP: EmailTemplates.GP_SIGNUP.value,
        RegistrationType.PATIENT: EmailTemplates.PATIENT_SIGNUP.value
    }

    # select the email template based upon the intended audience.
    templates = {
        RegistrationType.GP: EmailTemplates.GP_SIGNUP.value,
        RegistrationType.PATIENT: EmailTemplates.PATIENT_SIGNUP.value
    }

    send_mail(user.email, user.name, templates[entity], template_object)

    return {'username': user.username}
