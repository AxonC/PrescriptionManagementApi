import unittest
from unittest.mock import patch

from fastapi import status, HTTPException
from fastapi.testclient import TestClient

from main import app
from models.auth import User
from models.permissions_roles import Role, RoleWithPermissions
from routers.roles import _check_role_exists, _check_permissions_exists
from auth import get_current_user

client = TestClient(app)

class RolesRouterTests(unittest.TestCase):
    def setUp(self):
        self.mock_current_user = User(username='tmctestface', name='Testy McTestFace', password='test-pwd', email='test@test.com')
        self.mock_base_role = {
            'role_id': '0dabea9d-60b3-4d98-8960-312216ec9cf5',
            'name': 'Test Role',
            'description': 'Role for testing'
        }
        app.dependency_overrides[get_current_user] = lambda: self.mock_current_user

    @patch('routers.roles.get_roles')
    def test_gathers_list_of_roles_correctly(self, mock_get_roles):
        mock_roles_list = [
            self.mock_base_role
        ]
        mock_get_roles.return_value.__iter__.return_value = mock_roles_list

        response = client.get("/roles")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data'], mock_roles_list)

    @patch('routers.roles.get_role_with_permissions')
    def test_gets_role_correctly(self, mock_get_role_with_permissions):
        mock_permissions = [
            {
                'permission_id': '9ddfdc47-9663-4aaf-ac0b-ec86e717d420',
                'name': 'test.permission'
            }
        ]
        mock_role = {**self.mock_base_role, 'permissions': mock_permissions}
        mock_get_role_with_permissions.return_value.__next__.return_value = mock_role

        response = client.get(f"/roles/{self.mock_base_role['role_id']}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data'], mock_role)

    @patch('routers.roles.get_role_with_permissions')
    def tests_throws_not_found_exception_when_not_found(self, mock_get_role_with_permissions):
        mock_get_role_with_permissions.return_value.__next__.return_value = None
        response = client.get(f"/roles/{self.mock_base_role['role_id']}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], 'Not found.')

    @patch('routers.roles.create_role')
    def tests_calls_query_with_correct_params_to_create_role(self, mock_create_role):
        mock_create_role.return_value.__next__.return_value = self.mock_base_role['role_id']

        response = client.post("/roles", json={
            'name': self.mock_base_role['name'],
            'description': self.mock_base_role['description']
        })

        mock_create_role.assert_called_with(
            name=self.mock_base_role['name'],
            description=self.mock_base_role['description']
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()['data'], self.mock_base_role['role_id'])

    @patch('routers.roles.add_permission_to_role')
    @patch('routers.roles.remove_existing_permissions_for_role')
    def test_removes_existing_permissions_from_role_when_put(self, mock_remove_existing, _):
        mock_permissions_to_add = ['e1416696-62ef-42d1-a84c-18b36d35d7f9']
        # pass the role check
        app.dependency_overrides[_check_role_exists] = lambda: self.mock_base_role['role_id']
        # pass the permission check
        app.dependency_overrides[_check_permissions_exists] = lambda: mock_permissions_to_add
        
        response = client.put(f"/roles/{self.mock_base_role['role_id']}/permissions", json={
            'permissions': mock_permissions_to_add
        })

        mock_remove_existing.assert_called_with(role_id=self.mock_base_role['role_id'])
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch('routers.roles.add_permission_to_role')
    @patch('routers.roles.remove_existing_permissions_for_role')
    def test_calls_add_permission_to_role_with_permission(self, _, mock_add_permission_to_role):
        mock_permissions_to_add = ['e1416696-62ef-42d1-a84c-18b36d35d7f9']
        # pass the role check
        app.dependency_overrides[_check_role_exists] = lambda: self.mock_base_role['role_id']
        # pass the permission check
        app.dependency_overrides[_check_permissions_exists] = lambda: mock_permissions_to_add

        response = client.put(f"/roles/{self.mock_base_role['role_id']}/permissions", json={
            'permissions': mock_permissions_to_add
        })

        mock_add_permission_to_role.assert_called_with(
            role_id=self.mock_base_role['role_id'],
            permission_id=mock_permissions_to_add[0]
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # HELPER FUNCTION TESTS
    @patch('routers.roles.get_role_by_id')
    def tests_check_role_exists_helper_raises_when_does_not_pass(self, mock_get_role_by_id):
        mock_get_role_by_id.return_value.__next__.return_value = None

        with self.assertRaises(HTTPException) as exc:
            _check_role_exists(role_id=self.mock_base_role['role_id'])
        self.assertEqual(exc.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(exc.exception.detail, 'Role not found.')

    @patch('routers.roles.get_role_by_id')
    def test_returns_role_id_when_role_found(self, mock_get_role_by_id):
        mock_get_role_by_id.return_value = iter([self.mock_base_role])

        result = _check_role_exists(role_id=self.mock_base_role['role_id'])
        self.assertEqual(result, self.mock_base_role['role_id'])

    @patch('routers.roles.get_all_permissions')
    def test_raises_exception_when_permission_not_found(self, mock_get_all_permissions):
        mock_get_all_permissions.return_value = iter([{'permission_id': '3413cc55-6a78-4c09-a176-0387eac4d395'}])

        with self.assertRaises(HTTPException) as exc:
            _check_permissions_exists(permissions=['e1416696-62ef-42d1-a84c-18b36d35d7f9'])
        self.assertEqual(exc.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(exc.exception.detail, "One or more permissions not valid.")    

    @patch('routers.roles.get_all_permissions')
    def test_returns_permissions_when_all_are_valid(self, mock_get_all_permissions):
        mock_permission = {'permission_id': '3413cc55-6a78-4c09-a176-0387eac4d395'}
        mock_get_all_permissions.return_value = iter([mock_permission])

        result = _check_permissions_exists(permissions=[mock_permission['permission_id']])
        self.assertEqual(result, [mock_permission['permission_id']])
