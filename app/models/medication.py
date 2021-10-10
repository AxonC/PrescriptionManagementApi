from enum import IntEnum
from pydantic import BaseModel, Field

class MedicationBloodworkTypes(IntEnum):
    FULL_BLOOD_COUNT = 1
    BLOOD_PRESSURE = 2
    UREA_ELECTROLYTES = 3
class Medication(BaseModel):
    medication_id: str
    medication_name: str
    bloodwork_requirement: MedicationBloodworkTypes = Field(None)
