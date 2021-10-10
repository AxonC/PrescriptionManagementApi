import logging  
import uuid
from fastapi import APIRouter, Body, HTTPException, status, \
    Depends
from psycopg2.errors import ForeignKeyViolation

from models.base import Response, InstitutionTypes, RegistrationType
from models.auth import User
from models.registration_tokens import RegistrationToken
from auth import create_token
from database.queries.token_queries import get_active_token
from database.queries.user_queries import get_pending_user_by_username,\
    delete_pending_user
from database.queries.medical_practice_queries import assign_gp_to_practice
from database.queries.roles_queries import add_role_to_user
from models.permissions_roles import CoreRoles
from helpers import check_valid_uuid

from auth import create_new_user

router = APIRouter()

LOGGER = logging.getLogger(__name__)

def _check_registration_token(
    registration_token: str = Body(..., embed=True, title='Token of registration')
) -> RegistrationToken:
    """ Check that a registration token exists. Return the token ID if valid. """
    unauthorized_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Registration token invalid'
    )

    if not check_valid_uuid(registration_token):
        raise unauthorized_exception

    if (token := next(get_active_token(token_id=registration_token), None)) is None:
        LOGGER.info('Registration token invalid')
        raise unauthorized_exception
    return RegistrationToken(**token)

@router.post("/convert", status_code=status.HTTP_201_CREATED)
def convert_pending_user(
    password: str = Body(..., embed=True),
    registration_token: RegistrationToken = Depends(_check_registration_token)
):
    """ Convert a pending user into a full user account

        If successful, returns a valid JWT access token for the
        newly created user. Deletes the pending user after successful
        creation.
    """
    LOGGER.info('Received request to convert %s to a full user', registration_token.username)
    if (user := next(get_pending_user_by_username(username=registration_token.username), None)) is None:
        LOGGER.error('Pending user not found')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User does not exist')

    new_user = User(
        name=user['name'],
        email=user['email'],
        username=user['username'],
        password=password,
    )
    if not create_new_user(new_user, institution_id=user['institution_id']):
        LOGGER.error('User cannot be converted.')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Error creating user')

    role_assignments = {
        RegistrationType.MEDICAL_PRACTICE_ADMINISTRATOR: CoreRoles.MEDICAL_PRACTICE_ADMINISTRATOR.value,
        RegistrationType.GP: CoreRoles.GP.value,
        RegistrationType.PATIENT: CoreRoles.PATIENT.value,
        RegistrationType.HEAD_PHARMACIST: CoreRoles.HEAD_PHARMACIST.value,
        RegistrationType.PHARMACIST: CoreRoles.PHARMACIST.value,
        RegistrationType.PHARMACY_TECHNICIAN: CoreRoles.PHARMACY_TECHNICIAN.value
    }

    try:
        LOGGER.info('Assigning roles for %s', new_user.username)
        add_role_to_user(username=new_user.username, role_id=role_assignments[registration_token.token_type])
    except KeyError:
        LOGGER.error('Role assignment not handled for %s', registration_token.token_type)
        raise
    except ForeignKeyViolation:
        LOGGER.error('Role %s does not exist in database to assign', role_assignments[registration_token.token_type])
        raise

    # registration token deleted on delete of pending user row.
    delete_pending_user(username=registration_token.username)

    access_token = create_token(username=user['username'])
    LOGGER.info("Token generated for user %s", user['username'])
    return {"access_token": access_token, "token_type": "bearer"}
