""" Core models for the application """
from typing import TypeVar, Optional, Generic

from pydantic import Field
from pydantic.generics import GenericModel, BaseModel
from enum import IntEnum, Enum

DataT = TypeVar('DataT')

class Response(GenericModel, Generic[DataT]):
    data: Optional[DataT]

class InstitutionTypes(IntEnum):
    """ Enum listing the types of an institution stored in the database. """
    MEDICAL_PRACTICE = 1
    PHARMACY = 2


class RegistrationType(Enum):
    GP = 'GP'
    HEAD_PHARMACIST = 'HEAD_PHARMACIST'
    PATIENT = 'PATIENT'
    MEDICAL_PRACTICE_ADMINISTRATOR = "MEDICAL_PRACTICE_ADMINISTRATOR"
    PHARMACY_TECHNICIAN = 'PHARMACY_TECHNICIAN'
    PHARMACIST = 'PHARMACIST'

class BaseInstitution(BaseModel):
    """ Model used to depict common fields across entities """
    name: str
    address_line_1: str
    address_line_2: str
    address_line_3: str = Field(None)
    address_line_4: str = Field(None)
    city: str
    state: str
    postcode: str

class Institution(BaseInstitution):
    institution_id: str
    institution_type: InstitutionTypes

class InstitutionCreateResponse(BaseModel):
    institution_id: str

class PharmacyPreference(BaseModel):
    username: str
    institution_id: str
