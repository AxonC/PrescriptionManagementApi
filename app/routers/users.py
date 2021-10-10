""" Router to handle user management """
from typing import List
import logging

from uuid import UUID
from fastapi import APIRouter, Depends, Body, HTTPException, status


from auth import get_current_user
from database.queries.roles_queries import get_roles, add_role_to_user,\
    remove_existing_roles_for_user

LOGGER = logging.getLogger(__name__)

router = APIRouter()

def _check_roles_exist(roles: List[UUID] = Body(..., embed=True)) -> List[UUID]:
    """ Perform check that all roles in a list exists
        and return the list of UUIDs
    """
    valid_roles = [r['role_id'] for r in get_roles()]
    roles_invalid = any(r for r in roles if str(r) not in valid_roles)
    if roles_invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more roles not found."
        )
    return roles

@router.put("/{username}/roles",
    dependencies=[Depends(get_current_user)],
    status_code=status.HTTP_204_NO_CONTENT
)
async def assign_roles(username: str, roles: List[UUID] = Depends(_check_roles_exist)):
    """ Assign a list of roles to a user. Will replace existing roles. """
    LOGGER.info("Removing existing roles for user: %s", username)
    remove_existing_roles_for_user(username=username)

    for role in roles:
        LOGGER.info("Adding role %s to user: %s", role, username)
        add_role_to_user(username=username, role_id=role)
    return {}
