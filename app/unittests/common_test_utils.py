""" Module for common test utils to avoid duplication """
from models.auth import User, BaseUser, BaseUserWithPermissions

MOCK_USER = User(username='tmctestface', name='Testy McTestFace', password='test-pwd', email='test@test.com', institution_id='0fa0a79b-7500-47ea-b9d6-3bce39b0f13e')
MOCK_USER_WITH_PERMISSIONS = BaseUserWithPermissions(username='tmctestface', name='Testy McTestFace', password='test-pwd', email='test@test.com', permissions=[])
MOCK_BASE_USER = BaseUser(username='tmctestface', name='Testy McTestFace', email='test@test.com')