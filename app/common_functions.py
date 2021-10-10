""" Module to store functions which are used across the application """
import logging

from fastapi import HTTPException, status
from psycopg2.errors import UniqueViolation

from config import FRONT_END_BASE_URL
from database.queries.user_queries import create_pending_user
from models.auth import BaseUser

LOGGER = logging.getLogger(__name__)

def _handle_create_pending_user(user: BaseUser, institution_id: str) -> None:
    """ Function to encapsulate the logic to create a pending user with
        error handling.

        Designed to be consumed from an API endpoint function.
    """
    try:
        LOGGER.debug('Creating pending user %s for institution %s', user.username, institution_id)
        create_pending_user(user, institution_id=institution_id)
    except UniqueViolation as exception:
        LOGGER.warning('User already exists with username %s', user.username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User already exists'
        ) from exception

def _generate_email_template_signup_url(token: str) -> dict:
    """ Generate a URL to be used in the email templates for signup of users"""
    return {'url': f'{FRONT_END_BASE_URL}/signup?token={token}'}
