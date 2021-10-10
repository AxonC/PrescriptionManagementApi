from typing import List, Optional

from pydantic import BaseModel, Field
from models.permissions_roles import Permission

class BaseUser(BaseModel):
    username: str
    name: str
    email: str

class BaseUserWithInstitution(BaseUser):
    institution_id: Optional[str] = Field(None)

class User(BaseUser):
    password: str
    institution_id: str = Field(None)

class BaseUserWithPermissions(BaseModel):
    username: str
    name: str
    email: str
    permissions: List[Permission]

class UserWithRoles(BaseUser):
    roles: List[str]
