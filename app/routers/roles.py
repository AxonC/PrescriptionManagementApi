""" Module to handle roles related endpoints """
from typing import List
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Body
from uuid import UUID

from auth import get_current_user
from models.base import Response
from models.permissions_roles import BaseRole, Role, RoleWithPermissions, \
    PermissionsForRoleRequest

from database.queries.roles_queries import get_roles, get_role_with_permissions, \
    create_role, get_role_by_id, add_permission_to_role, remove_existing_permissions_for_role
from database.queries.permissions_queries import get_all_permissions

LOGGER = logging.getLogger(__name__)

router = APIRouter()

@router.get("",
    dependencies=[Depends(get_current_user)],
    response_model=Response[List[Role]]
)
async def get_all_roles():
    """ Get all roles registered in the application """
    LOGGER.info("Received request to get roles.")
    return {"data": [Role(**r) for r in get_roles()]}

@router.get("/{role_id}",
    dependencies=[Depends(get_current_user)],
    response_model=Response[RoleWithPermissions]
)
async def get_role(role_id: UUID):
    """ Get the details of a role including the associated permissions """
    LOGGER.info("Request to get role: %s", role_id)
    if (role_information := next(get_role_with_permissions(role_id=role_id))) is None:
        LOGGER.info("Role %s not found", role_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return {"data": role_information}

@router.post("",
    dependencies=[Depends(get_current_user)],
    status_code=status.HTTP_201_CREATED,
    response_model=Response[str]
)
async def create_new_role(role: BaseRole):
    """ Create a new role """
    LOGGER.info("Creating new role with request %s", role)
    role_id = next(create_role(name=role.name, description=role.description))
    return {"data": role_id}

def _check_role_exists(role_id: UUID):
    """ Check role exists given its UUID """
    if (next(get_role_by_id(role_id=role_id))) is None:
        LOGGER.info("Role %s not found.", role_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role not found.")
    LOGGER.debug("Role check successful for %s", role_id)
    return role_id

def _check_permissions_exists(permissions: List[UUID] = Body(..., embed=True)):
    valid_permissions = [p['permission_id'] for p in get_all_permissions()]
    permissions_invalid = any(p for p in permissions if str(p) not in valid_permissions)
    if permissions_invalid:
        LOGGER.info("Permissions given not all valid. %s", permissions)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more permissions not valid."
        )
    LOGGER.debug("Permission checks successful for %s", permissions)
    return permissions

@router.put("/{role_id}/permissions",
    dependencies=[Depends(get_current_user)],
    status_code=status.HTTP_204_NO_CONTENT
)
async def add_permissions_to_role(
    role_id: UUID = Depends(_check_role_exists),
    permissions: List[UUID] = Depends(_check_permissions_exists)
):
    """ Add a list of permission UUIDs to a role.
        Permissions in this request will replace all previous permissions as
        defined in the behaviour of a PUT request.

        Passing an empty list of permissions will remove all permissions for a role.
    """
    LOGGER.info("Removing permissions for role %s", role_id)
    remove_existing_permissions_for_role(role_id=role_id)

    for permission in permissions:
        LOGGER.debug("Adding permission %s to role %s", permission, role_id)
        add_permission_to_role(role_id=role_id, permission_id=permission)
    return {}
