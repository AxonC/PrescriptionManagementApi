from enum import Enum
from uuid import UUID

from pydantic import BaseModel

from models.base import RegistrationType

class RegistrationTokenType(Enum):
    """ Enum to represent types of registration tokens """
    MEDICAL_PRACTICE = 1

class RegistrationToken(BaseModel):
    token_id: UUID
    token_type: RegistrationType
    username: str
