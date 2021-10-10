""" Module to store information on email templates """
from enum import Enum

class EmailTemplates(Enum):
    """ Enum of Sendgrid Template IDs """
    PHARMACY_SIGNUP = 'd-ad3e2c18e91246b0bf5eb76fbc7f460f'
    MEDICAL_PRACTICE_SIGNUP = 'd-7b78b7c37d2f4ec7b00a583276b43780'
    GP_SIGNUP = 'd-36d43de369be48029de5aeb129b5d84c'
    PATIENT_SIGNUP = 'd-e9a095ecff374fc996a4acda57712eb7'
    PHARMACY_TECHNICIAN_SIGNUP = 'd-8e5feeda278e42b589eb9c7fb0e38ada'
    PHARMACIST_SIGNUP = 'd-a625d44b764449459f802c49c98567c0'
    PRESCRIPTION_NOTIFICATION = 'd-e48fc50306964087874bb45283c59a73'
