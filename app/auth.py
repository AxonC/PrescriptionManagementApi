""" Module handling authentication methods """
import logging
from typing import List
from datetime import timedelta, datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from psycopg2.errors import UniqueViolation

from config import AUTHENTICATION_SECRET_KEY
from database.queries.user_queries import get_user_by_username, create_user, get_user_permissions
from models.auth import User, BaseUser

ALGORITHM = "HS256"
OAUTH_2_SCHEME = OAuth2PasswordBearer(tokenUrl="token")
PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
LOGGER = logging.getLogger(__name__)

NOT_ALLOWED_EXCEPTION = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized.")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """ Verify a plan password against a hashed password """
    try:
        pwd = PWD_CONTEXT.verify(plain_password, hashed_password)
    except UnknownHashError:
        LOGGER.critical("User with un-hashed password.")
        return False
    return pwd

def authenticate_user(username: str, password: str) -> BaseUser:
    """ Authenticate a user given a username and password from form_data """
    LOGGER.debug("Authenticating %s", username)
    if (user := next(get_user_by_username(username), None)) is None:
        LOGGER.debug("Username not found for %s", username)
        return None

    password_valid = verify_password(plain_password=password, hashed_password=user['password'])
    return BaseUser(**user) if password_valid else None

def create_new_user(user: User, institution_id: str = None) -> bool:
    """ Create a new user. User object should contain a plain password.

        Returns the BaseUser model of the created user. Password excluded from
        model so safe to return via API.
    """
    user.password = PWD_CONTEXT.hash(user.password)
    try:
        username = next(create_user(user=user, institution_id=institution_id), None)
    except UniqueViolation:
        LOGGER.exception("Failed to create new user")
        return None
    return username


def create_token(username: str, token_expiry_minutes: int = 180) -> str:
    """ Function to create a JWT token for a given username with a specified expiry.

        User should be verified before using this function. This does NOT verify
        their credentials.
    """
    expiry = datetime.now() + timedelta(minutes=token_expiry_minutes)
    claims = {"exp": expiry, "uid": username}
    return jwt.encode(claims, AUTHENTICATION_SECRET_KEY, ALGORITHM)

def get_current_user(token: str = Depends(OAUTH_2_SCHEME)) -> User:
    """ Verify the given JWT token and get the relevant user if valid """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    try:
        # attempt to decode the JWT token against the secret key
        payload = jwt.decode(token, AUTHENTICATION_SECRET_KEY, algorithms=[ALGORITHM])
        # if valid, grab the username from the JWT token.
        if (username := payload.get("uid", None)) is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc
    return User(**next(get_user_by_username(username=username)))

def check_user_by_permissions(permissions: List[str], user: User) -> User:
    """ Check the user has any of the permissions

        Designed to be called from another API function as it
        raises HTTPException.

        Permissions parameter should be a list of permission names
        rather than a list of UUIDs.
    """
    user_permissions = [p['name'] for p in get_user_permissions(username=user.username)]
    LOGGER.info('%s permissions found for user %s', len(user_permissions), user.username)

    if '*' in user_permissions:
        LOGGER.debug('User %s has wildcard permission, bypassing', user.username)
        return user

    has_permission = any(p for p in user_permissions if p in permissions)

    if not has_permission:
        LOGGER.debug('User %s does not have permissions %s', user.username, permissions)
        raise NOT_ALLOWED_EXCEPTION
    return user
