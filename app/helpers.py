""" Module containing helper functions """
from uuid import UUID
from fastapi import Request, HTTPException, status
from typing import Union, List

def check_valid_uuid(uuid: Union[str, UUID]):
    """ Function to check whether a string or UUID is valid.
        Performs check by trying to construct UUID and catching
        documented exceptions for the UUID constructor.
    """
    try:
        val = UUID(str(uuid), version=4)
    except (AttributeError, ValueError, TypeError) :
        return False
    return str(val) == uuid


class UUIDPathChecker:
    """ Class to check a list of parameters passed in the path of
        a request contains a valid uuid.

        Constructor should have a list of the path parameter keys.

        Uses the underlying request object from FastAPI/Starlette
        to access the path parameters outside the usual method.

        Class is designed to be used as a dependency to an API method.

        Example usage:
            Depends(UUIDPathChecker(['prescription_id']))

        Raises:
            HTTPException with 422.

        Returns:
            None
    """
    def __init__(self, fields: List[str]):
        self.fields = fields

    def __call__(self, request: Request) -> None:
        """ Check that every field defined in the constructor meets the test for
            a uuid by accessing the underlying request path parameters
        """
        uuid_fields_valid =  all(check_valid_uuid(request.path_params[f]) for f in self.fields)
        if not uuid_fields_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='Malformed UUID detected.'
            )
