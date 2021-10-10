import unittest
from unittest.mock import patch

from fastapi import HTTPException, status
from jose import JWTError
from passlib.exc import UnknownHashError

from auth import authenticate_user, get_current_user, verify_password,\
    check_user_by_permissions

from models.auth import User, BaseUser

class AuthUnittests(unittest.TestCase):
    def setUp(self):
        self.mock_user_model = User(username='username', name='User Name', password='test-password', email='test@test.com')

    @patch('auth.get_user_by_username')
    def test_returns_none_if_username_not_found(self, mock_get_user_by_username):
        mock_get_user_by_username.return_value = iter(())

        result = authenticate_user(username='username', password='password')
        self.assertEqual(result, None)

    @patch('auth.get_user_by_username')
    @patch('auth.verify_password')
    def test_returns_a_base_user_when_user_found_and_password_verified(self, mock_verify_password, mock_get_user_by_username):
        mock_get_user_by_username.return_value.__next__.return_value=self.mock_user_model.dict()
        mock_verify_password.return_value = True

        result = authenticate_user(username='username', password=self.mock_user_model.password)

        mock_verify_password.assert_called_with(plain_password='test-password', hashed_password='test-password')
        self.assertEqual(result, BaseUser(username=self.mock_user_model.username, name=self.mock_user_model.name, email=self.mock_user_model.email))

    @patch('auth.get_user_by_username')
    @patch('auth.verify_password')
    def test_returns_none_when_user_found_but_password_incorrect(self, mock_verify_password, mock_get_user_by_username):
        mock_get_user_by_username.return_value.__next__.return_value=self.mock_user_model.dict()
        mock_verify_password.return_value = False

        result = authenticate_user(username=self.mock_user_model.username, password=self.mock_user_model.password)

        self.assertEqual(result, None)

    def test_raises_exception_when_no_token_is_provided(self):
        with self.assertRaises(HTTPException) as exc:
            get_current_user(None)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, exc.exception.status_code)

    @patch('auth.jwt.decode', side_effect=JWTError)
    def test_raises_exception_when_jwt_cannot_be_decoded(self, _):
        with self.assertRaises(HTTPException) as exc:
            get_current_user('token')
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, exc.exception.status_code)
    
    @patch('auth.jwt.decode')
    def test_raises_exception_when_uid_is_none(self, mock_jwt_decode):
        mock_jwt_decode.return_value = {}

        with self.assertRaises(HTTPException) as exc:
            get_current_user('token')
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, exc.exception.status_code)

    @patch('auth.get_user_by_username')
    @patch('auth.jwt.decode')
    def test_returns_user_model_when_valid(self, mock_jwt_decode, mock_get_user_by_username):
        mock_jwt_decode.return_value = {'uid': self.mock_user_model.username}

        mock_get_user_by_username.return_value.__next__.return_value=self.mock_user_model.dict()

        result = get_current_user('token')
        self.assertEqual(result, self.mock_user_model)

    # verify_password
    @patch('auth.PWD_CONTEXT.verify', side_effect=UnknownHashError)
    def test_returns_false_gracefully_if_hash_fails(self, _):
        result = verify_password('test', 'addb')
        self.assertFalse(result)

    @patch('auth.PWD_CONTEXT.verify')
    def test_returns_true_when_password_hashed_correctly(self, mock_pwd_verify):
        mock_pwd_verify.return_value = True

        result = verify_password('test', 'test')
        self.assertTrue(result)

    # check_user_by_permissions
    @patch('auth.get_user_permissions')
    def test_detects_when_user_has_permission(self, mock_get_user_permissions):
        mock_user_permissions = ['test.test1']
        mock_user_permission_objects = [
            {
                'name': 'test.test1',
                'permission_id': '0bca6be6-eb43-40df-a087-b91dc89edcc9'
            }
        ]
        mock_get_user_permissions.return_value = mock_user_permission_objects
        result = check_user_by_permissions(mock_user_permissions, self.mock_user_model)

        self.assertEqual(result, self.mock_user_model)

    @patch('auth.get_user_permissions')
    def test_raises_http_exception_when_not_has_permission(self, mock_get_user_permissions):
        mock_user_permissions = ['test.test2']
        mock_user_permission_objects = [
            {
                'name': 'test.test1',
                'permission_id': '0bca6be6-eb43-40df-a087-b91dc89edcc9'
            }
        ]

        mock_get_user_permissions.return_value = mock_user_permission_objects

        with self.assertRaises(HTTPException) as exc:
            check_user_by_permissions(mock_user_permissions, self.mock_user_model)

        self.assertEqual(exc.exception.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(exc.exception.detail, "Unauthorized.")
