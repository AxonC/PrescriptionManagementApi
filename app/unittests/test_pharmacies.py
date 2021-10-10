import unittest
from unittest.mock import patch

from fastapi import status, HTTPException
from fastapi.testclient import TestClient

from main import app
from auth import OAUTH_2_SCHEME, get_current_user
from models.base import BaseInstitution, RegistrationType, Institution,InstitutionTypes
from psycopg2.errors import UniqueViolation

from routers.pharmacies import _get_pharmacy


from unittests.common_test_utils import MOCK_USER, MOCK_BASE_USER

client = TestClient(app)

# Disable permission and authentication checking.
@patch('permissions.check_user_by_permissions', return_value=MOCK_USER)
@patch('permissions.get_current_user', return_value=MOCK_USER)
class TestPharmacies(unittest.TestCase):

    def setUp(self):
        app.dependency_overrides[OAUTH_2_SCHEME] = lambda: 'token'
        self.mock_entity = BaseInstitution(
            name='Test Pharmacy',
            address_line_1='31 Spooner Street',
            address_line_2='Quahog',
            address_line_3='Newport County',
            address_line_4='Tiverton',
            city='Quahog',
            state='Rhode Island',
            postcode='000093'
        )
        self.mock_pharmacy_id = 'a5e8a393-a5f9-45f9-a12d-401c9a117554'
        self.endpoint = '/pharmacies'
        self.mock_pharmacy_id = 'a5e8a393-a5f9-45f9-a12d-401c9a117554'
        self.mock_stored_pharmacy = Institution(**self.mock_entity.dict(),
            institution_id=self.mock_pharmacy_id,
            institution_type=InstitutionTypes.PHARMACY
        )          

    @patch('routers.pharmacies.create_pending_user', side_effect=UniqueViolation)
    @patch('routers.pharmacies.delete_pharmacy')
    @patch('routers.pharmacies.create_pharmacy')
    def test_error_thrown_when_duplicate_master_user_found(self, *_):
        res = client.post(self.endpoint, json={
            'pharmacy': self.mock_entity.dict(),
            'master_user': MOCK_BASE_USER.dict()
        })

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['detail'], 'User already exists')

    @patch('routers.pharmacies.create_pending_user', side_effect=UniqueViolation)
    @patch('routers.pharmacies.create_pharmacy')
    @patch('routers.pharmacies.delete_pharmacy')
    def test_pharmacy_rolled_back_when_duplicate_master_user_found(self, mock_delete_pharmacy, mock_create_pharmacy, *_):
        mock_create_pharmacy.return_value = self.mock_pharmacy_id
        client.post(self.endpoint, json={
            'pharmacy': self.mock_entity.dict(),
            'master_user': MOCK_BASE_USER.dict()
        })

        mock_delete_pharmacy.assert_called_once_with(self.mock_pharmacy_id)

    @patch('routers.pharmacies.create_pending_user')
    @patch('routers.pharmacies.send_mail')
    @patch('routers.pharmacies.create_registration_token')
    @patch('routers.pharmacies.create_pharmacy')
    def test_pharmacy_can_be_created(self, mock_create_pharmacy, mock_create_registration_token, mock_send_mail, *_):
        mock_create_pharmacy.return_value = self.mock_pharmacy_id
        res = client.post(self.endpoint, json={
            'pharmacy': self.mock_entity.dict(),
            'master_user': MOCK_BASE_USER.dict()
        })

        mock_create_pharmacy.assert_called_with(pharmacy=self.mock_entity)
        mock_create_registration_token.assert_called_with(username=MOCK_BASE_USER.username, token_type=RegistrationType.HEAD_PHARMACIST.value)
        mock_send_mail.assert_called_once()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.json()['institution_id'], self.mock_pharmacy_id)

    @patch('routers.pharmacies.create_pending_user')
    @patch('routers.pharmacies.create_pharmacy', side_effect=UniqueViolation)
    def test_throws_400_when_duplicate_name_found(self, *_):
        res = client.post(self.endpoint, json={
            'pharmacy': self.mock_entity.dict(),
            'master_user': MOCK_BASE_USER.dict()
        })

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['detail'], 'Pharmacy already exists with that name')

    # GET Pharmacies
    @patch('routers.pharmacies.get_pharmacy')
    def test_throws_404_when_not_found(self, mock_get_pharmacy, *_):
        mock_get_pharmacy.return_value = None
        app.dependency_overrides[_get_pharmacy] = _get_pharmacy

        res = client.get(f'{self.endpoint}/a5e8a393-a5f9-45f9-a12d-401c9a117554')

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.json()['detail'], 'Pharmacy not found.')

    # REGISTER PHARMACY TECHNICANS
    @patch('routers.pharmacies._handle_create_pending_user')
    @patch('routers.pharmacies.get_pharmacy')
    @patch('routers.pharmacies.send_mail')
    @patch('routers.pharmacies.check_user_by_permissions')
    @patch('routers.pharmacies.create_registration_token')
    def test_user_can_be_registered_pharmacy_technician(
        self,
        mock_create_token,
        mock_check_user, 
        mock_send_mail,
        mock_get_pharmacy,
        *_
    ):
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
        mock_get_pharmacy.return_value = Institution(**self.mock_entity.dict(),
            institution_id=self.mock_pharmacy_id,
            institution_type=InstitutionTypes.PHARMACY
        ).dict()

        res = client.post(f'{self.endpoint}/register/{RegistrationType.PHARMACY_TECHNICIAN.value}',
            json={
                **MOCK_BASE_USER.dict(),
            }
        )
        mock_create_token.assert_called_once()
        mock_check_user.assert_called_once()
        mock_send_mail.assert_called_once()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.json()['username'], MOCK_BASE_USER.username)

    @patch('routers.pharmacies.get_pharmacy')
    @patch('routers.pharmacies.check_valid_uuid')
    def test_throws_404_when_uuid_check_fails_pharmacy_technician(self, mock_check_valid_uuid, mock_get_pharmacy, *_):
        mock_check_valid_uuid.return_value = False
        mock_get_pharmacy.return_value = self.mock_stored_pharmacy.dict()

        response = client.post(f'{self.endpoint}/register/{RegistrationType.PHARMACY_TECHNICIAN.value}', json={
            'username': 'pmcclop',
            'name': 'Poop Mc Plop Peake',
            'email': 'test@test.com'
        })

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], 'Pharmacy not found.')

    # REGISTER PHARMACISTS
    @patch('routers.pharmacies._handle_create_pending_user')
    @patch('routers.pharmacies.get_pharmacy')
    @patch('routers.pharmacies.send_mail')
    @patch('routers.pharmacies.check_user_by_permissions')
    @patch('routers.pharmacies.create_registration_token')
    def test_user_can_be_registered_pharmacist(
        self,
        mock_create_token,
        mock_check_user,
        mock_send_mail,
        mock_get_pharmacy,
        *_
    ):
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
        mock_get_pharmacy.return_value = Institution(**self.mock_entity.dict(), 
            institution_id=self.mock_pharmacy_id,
            institution_type=InstitutionTypes.PHARMACY
        ).dict()

        res = client.post(f'{self.endpoint}/register/{RegistrationType.PHARMACIST.value}',
            json={
                **MOCK_BASE_USER.dict(),
            }
        )
        mock_create_token.assert_called_once()
        mock_check_user.assert_called_once()
        mock_send_mail.assert_called_once()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.json()['username'], MOCK_BASE_USER.username)

    @patch('routers.pharmacies.get_pharmacy')
    @patch('routers.pharmacies.check_valid_uuid')
    def test_throws_404_when_uuid_check_fails_pharmacist(self, mock_check_valid_uuid, mock_get_pharmacy, *_):
        mock_check_valid_uuid.return_value = False
        mock_get_pharmacy.return_value = self.mock_stored_pharmacy.dict()

        response = client.post(f'{self.endpoint}/register/{RegistrationType.PHARMACIST.value}', json={
            'username': 'pmcclop',
            'name': 'Poop Mc Plop Peake',
            'email': 'test@test.com'
        })

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], 'Pharmacy not found.')

    @patch('routers.pharmacies.set_users_pharmacy')
    def test_calls_database_query_method_when_setting_user(self, mock_set_users_pharmacy, *_):
        app.dependency_overrides[_get_pharmacy] = lambda: self.mock_stored_pharmacy
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER

        response = client.patch(f'{self.endpoint}/{self.mock_pharmacy_id}/prefer')

        mock_set_users_pharmacy.assert_called_once_with(
            pharmacy_id=self.mock_stored_pharmacy.institution_id, 
            username=MOCK_USER.username
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['pharmacy_id'], self.mock_pharmacy_id)
