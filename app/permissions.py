from typing import List

from fastapi import Depends

from auth import OAUTH_2_SCHEME, get_current_user, check_user_by_permissions

class PermissionsChecker:
    """ Object used by Depends in fast API to:
            a) check the user is authenticated via their JWT token
            b) check that they hold the desired permissions passed into the constructor

        Permissions is a list of the permission names.
    """
    def __init__(self, permissions: List[str]):
        self.permissions = permissions

    def __call__(self, token: str = Depends(OAUTH_2_SCHEME)):
        user = get_current_user(token)
        if len(self.permissions) < 1:
            return user
        return check_user_by_permissions(permissions=self.permissions, user=user)
