""" Module containing API endpoints pertaining to bloodwork requests """
import logging 
from typing import List

from fastapi import APIRouter, status, HTTPException, Depends

from database.queries.bloodwork_queries import (
    mark_bloodwork_request_complete,
    get_request_by_id,
    get_requests_by_practice,
    get_request_by_id_in_practice
)
from helpers import UUIDPathChecker
from models.base import Response
from models.bloodwork import BloodworkRequest, BloodworkListing
from models.auth import User
from permissions import PermissionsChecker

router = APIRouter()

LOGGER = logging.getLogger(__name__)

UUID_VALIDATOR_FIELDS = ['request_id']

REQUEST_NOT_FOUND_EXCEPTION = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail='Bloodwork request not found.'
)

@router.get('',
    response_model=Response[List[BloodworkListing]]
)
def get_bloodwork_requests_by_practice(
    completed: bool = False,
    user: User = Depends(PermissionsChecker(['bloodwork-request.list']))
):
    """ Get the bloodwork requests by the requesting users' practice id.

        By default, all pending requests will be returned unless
        the completed query parameter is specified.
     """
    LOGGER.info('Request made to get bloodwork requests by medical practice %s', user.institution_id)
    return {'data':[BloodworkListing(**br)
                    for br in get_requests_by_practice(practice_id=user.institution_id, completed=completed)]}

@router.get('/{request_id}',
    response_model=BloodworkListing,
    dependencies=[Depends(UUIDPathChecker(UUID_VALIDATOR_FIELDS))]
)
def get_bloodwork_request(
    request_id: str,
    user: User = Depends(PermissionsChecker(['bloodwork-request.get']))
):
    """ Get an individual bloodwork request found in the practice of the requesting user. """
    if (request := get_request_by_id_in_practice(request_id=request_id, practice_id=user.institution_id)) is None:
        raise REQUEST_NOT_FOUND_EXCEPTION
    return BloodworkListing(**request)

@router.patch('/{request_id}/complete',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(UUIDPathChecker(UUID_VALIDATOR_FIELDS))
    ],
)
def mark_request_complete(
    request_id: str,
    user: User = Depends(PermissionsChecker(['bloodwork-request.complete'])),
):
    """ Mark an existing bloodwork request as complete """
    LOGGER.info('Request made to complete bloodwork request with ID %s', request_id)
    if (request := get_request_by_id(request_id=request_id)) is None:
        LOGGER.info('Bloodwork request %s not found', request_id)
        raise REQUEST_NOT_FOUND_EXCEPTION
    bloodwork_request: BloodworkRequest = BloodworkRequest(**request)

    if user.institution_id != bloodwork_request.practice_id:
        LOGGER.info('User %s cannot mark bloodwork request %s as complete.', user.username, bloodwork_request.request_id)
        raise REQUEST_NOT_FOUND_EXCEPTION

    if bloodwork_request.completed_at is not None:
        LOGGER.info('Bloodwork request %s already completed', request_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Bloodwork request already completed.'
        )

    mark_bloodwork_request_complete(request_id=bloodwork_request.request_id)
    LOGGER.debug('Bloodwork request %s marked as completed', request_id)

    return {}
