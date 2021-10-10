""" Module containing endpoints pertaining to pharmacies """
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, status, Depends, HTTPException, Path
from psycopg2.errors import UniqueViolation

from auth import get_current_user, check_user_by_permissions, NOT_ALLOWED_EXCEPTION
from config import FRONT_END_BASE_URL
from helpers import check_valid_uuid
from common_functions import (
    _handle_create_pending_user,
    _generate_email_template_signup_url
)
from models.base import  (
    BaseInstitution,
    Response,
    Institution,
    InstitutionCreateResponse,
    InstitutionTypes,
    RegistrationType
)
from models.auth import BaseUser, User, UserWithRoles
from database.queries.pharmacies_queries import (
    create_pharmacy,
    get_pharmacy,
    get_pharmacies,
    delete_pharmacy,
    set_users_pharmacy
)
from database.queries.token_queries import create_registration_token
from database.queries.user_queries import create_pending_user, get_users_by_institution_with_roles
from mail.send import send_mail
from mail.templates import EmailTemplates
from permissions import PermissionsChecker

router = APIRouter()

LOGGER = logging.getLogger(__name__)

def _get_pharmacy(pharmacy_id: str = Path(...)) -> Institution:
    """ Helper function to check for a pharmacy from API request.
        Returns the relevant institution model if found.
    """
    pharmacy_not_found_exception = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail='Pharmacy not found.'
    )

    LOGGER.debug('Checking for existence of pharmacy with id %s', pharmacy_id)
    if not check_valid_uuid(uuid=pharmacy_id):
        LOGGER.info('Invalid uuid %s passed', pharmacy_id)
        raise pharmacy_not_found_exception

    pharmacy_id = str(UUID(pharmacy_id))
    if (pharmacy := get_pharmacy(pharmacy_id)) is None:
        LOGGER.info('Pharmacy %s not found', pharmacy_id)
        raise pharmacy_not_found_exception
    return Institution(**pharmacy)


@router.get('',
    response_model=Response[List[Institution]],
    dependencies=[Depends(PermissionsChecker(['pharmacies.list', 'patient.pharmacies.list']))],
)
def get_pharmacy_list():
    """ Get a list of registered pharmacies """
    LOGGER.info('Request for list of pharmacies')
    return {'data': [Institution(**p) for p in get_pharmacies()]}

@router.get('/{pharmacy_id}',
    response_model=Response[Institution],
    dependencies=[Depends(PermissionsChecker(['pharmacies.view']))]
)
def get_pharmacy_details(pharmacy: Institution = Depends(_get_pharmacy)):
    """ Get the details of an individual pharmacy """
    LOGGER.info('Received request to view pharmacy with id %s', pharmacy.institution_id)
    return {'data': pharmacy}


@router.post('',
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionsChecker(['pharmacies.create']))],
    response_model=InstitutionCreateResponse
)
def create_new_pharmacy(pharmacy: BaseInstitution, master_user: BaseUser):
    """ Create a new pharmacy entity and its associated data """
    LOGGER.info('Received request to create new pharmacy')
    try:
        institution_id = create_pharmacy(pharmacy=pharmacy)
        LOGGER.info('Pharmacy created with id %s', institution_id)
    except UniqueViolation as exception:
        LOGGER.info('Duplicate pharmacy found')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Pharmacy already exists with that name'
        ) from exception

    try:
        create_pending_user(user=master_user, institution_id=institution_id)
    except UniqueViolation as exception:
        LOGGER.info('Duplicate master user found')
        delete_pharmacy(institution_id)
        LOGGER.info('Deleted existing pharmacy as duplicate master user exists.')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User already exists'
        ) from exception

    registration_token = next(create_registration_token(
        username=master_user.username,
        token_type=RegistrationType.HEAD_PHARMACIST.value
    ))

    template_object = {'url': f'{FRONT_END_BASE_URL}/signup?token={registration_token["token_id"]}'}
    send_mail(master_user.email, master_user.name, EmailTemplates.PHARMACY_SIGNUP.value, template_object)

    return {'institution_id': institution_id}

@router.post("/register/{entity}",
    status_code=status.HTTP_201_CREATED
)
def register_to_pharmacy(
    user: BaseUser,
    entity: RegistrationType,
    requesting_user: User = Depends(get_current_user)
):
    """ 
    Register a new user to a given pharmacy entity by creating
    a pending user associated with the relevant pharmacy
    institution.
    """
    pharmacy: Institution = _get_pharmacy(pharmacy_id=requesting_user.institution_id)
    LOGGER.info('Request made to add %s to pharmacy %s', entity.value, pharmacy.institution_id)

    entity_required_permissions = {
        RegistrationType.PHARMACY_TECHNICIAN: 'pharmacy.register-pharmacy-technician',
        RegistrationType.PHARMACIST: 'pharmacy.register-pharmacist'
    }

    try:
        required_permissions = entity_required_permissions[entity]
    except KeyError as exc:
        LOGGER.warning('Entity %s has no permissions assigned', entity)
        raise NOT_ALLOWED_EXCEPTION from exc

    check_user_by_permissions(permissions=[required_permissions], user=requesting_user)

    _handle_create_pending_user(user, institution_id=pharmacy.institution_id)

    registration_token = next(
        create_registration_token(username=user.username, token_type=entity.value)
    )

    template_object = _generate_email_template_signup_url(token=registration_token['token_id'])

    templates = {
        RegistrationType.PHARMACY_TECHNICIAN: EmailTemplates.PHARMACY_TECHNICIAN_SIGNUP.value,
        RegistrationType.PHARMACIST: EmailTemplates.PHARMACIST_SIGNUP.value
    }

    send_mail(user.email, user.name, templates[entity], template_object)

    return {'username': user.username}

@router.patch("/{pharmacy_id}/prefer",
    status_code=status.HTTP_200_OK
)
def set_preferred_pharmacy(
    pharmacy: Institution = Depends(_get_pharmacy),
    user: User = Depends(PermissionsChecker(['patient.pharmacy.own']))
):
    """ Set the current authenticated users' preferred pharmacy """
    LOGGER.info('Updating pharmacy assignment for %s in %s', user.username, pharmacy.institution_id)
    set_users_pharmacy(pharmacy_id=pharmacy.institution_id, username=user.username)

    return {'pharmacy_id': pharmacy.institution_id}
