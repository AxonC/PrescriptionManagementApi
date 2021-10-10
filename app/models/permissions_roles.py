from typing import List
from enum import Enum

from uuid import UUID
from pydantic import BaseModel

class CoreRoles(Enum):
    """ Enum for roles which are builtin to the application. These are
        populated using the database-init project.
    """
    GP = '45423550-fc13-4f96-b8c0-2895dcf2b2e6'
    PATIENT = '0fa0a79b-7500-47ea-b9d6-3bce39b0f13e'
    MEDICAL_PRACTICE_ADMINISTRATOR = 'c84415c1-59d1-480b-8ead-a61dbbdf2f9a'
    PHARMACY_TECHNICIAN = '3716ed7b-78ca-4c69-8def-99f5529ac415'
    PHARMACIST = 'b75e4f48-701f-4bba-b5dd-78ae21fddb5b'
    HEAD_PHARMACIST = '490231de-b6c9-4215-9866-5c84b059e1c6'
class BaseRole(BaseModel):
    """ Base attributes used to create a role """
    name: str
    description: str

class Role(BaseRole):
    """ A role assigned to a user. """
    role_id: UUID

class Permission(BaseModel):
    """ A permission which belongs to a role """ 
    permission_id: UUID
    name: str

class RoleWithPermissions(Role):
    """ A role with its associated permissions """
    permissions: List[Permission]
    
class PermissionsForRoleRequest(BaseModel):
    """ Request to add a permission to a role. """
    permissions: List[UUID]
