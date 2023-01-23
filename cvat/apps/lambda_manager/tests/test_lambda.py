
# Copyright (C) 2021-2022 Intel Corporation
#
# SPDX-License-Identifier: MIT

import json
from collections import OrderedDict
from io import BytesIO
from typing import Dict, Optional
from unittest import mock, skip
import os

import requests
from django.contrib.auth.models import Group, User
from django.http import HttpResponseNotFound, HttpResponseServerError
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from cvat.apps.engine.tests.utils import get_paginated_collection

LAMBDA_ROOT_PATH = '/api/lambda'
LAMBDA_FUNCTIONS_PATH = f'{LAMBDA_ROOT_PATH}/functions'
LAMBDA_REQUESTS_PATH = f'{LAMBDA_ROOT_PATH}/requests'

id_function_detector = "test-openvino-omz-public-yolo-v3-tf"
id_function_reid_response_data = "test-openvino-omz-intel-person-reidentification-retail-0300"
id_function_reid_response_no_data = "test-openvino-omz-intel-person-reidentification-retail-1234"
id_function_interactor = "test-openvino-dextr"
id_function_tracker = "test-pth-foolwood-siammask"
id_function_non_type = "test-model-has-non-type"
id_function_wrong_type = "test-model-has-wrong-type"
id_function_unknown_type = "test-model-has-unknown-type"
id_function_non_unique_labels = "test-model-has-non-unique-labels"
id_function_state_building = "test-model-has-state-building"
id_function_state_error = "test-model-has-state-error"

expected_keys_in_response_all_functions = ["id", "kind", "labels", "description", "framework", "name"]
expected_keys_in_response_function_interactor = expected_keys_in_response_all_functions + ["min_pos_points", "startswith_box"]
expected_keys_in_response_function_tracker = expected_keys_in_response_all_functions + ["state"]
expected_keys_in_response_requests = ["id", "function", "status", "progress", "enqueued", "started", "ended", "exc_info"]

path = os.path.join(os.path.dirname(__file__), 'assets', 'tasks.json')
with open(path) as f:
    tasks = json.load(f)

# removed unnecessary data
path = os.path.join(os.path.dirname(__file__), 'assets', 'functions.json')
with open(path) as f:
    functions = json.load(f)


def generate_image_file(filename, size=(100, 100)):
    f = BytesIO()
    image = Image.new('RGB', size=size)
    image.save(f, 'jpeg')
    f.name = filename
    f.seek(0)
    return f


class ForceLogin:
    def __init__(self, user, client):
        self.user = user
        self.client = client

    def __enter__(self):
        if self.user:
            self.client.force_login(self.user, backend='django.contrib.auth.backends.ModelBackend')

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if self.user:
            self.client.logout()

class _LambdaTestCaseBase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        http_patcher = mock.patch('cvat.apps.lambda_manager.views.LambdaGateway._http', side_effect = self.__get_data_from_lambda_manager_http)
        self.addCleanup(http_patcher.stop)
        http_patcher.start()

        invoke_patcher = mock.patch('cvat.apps.lambda_manager.views.LambdaGateway.invoke', side_effect = self.__invoke_function)
        self.addCleanup(invoke_patcher.stop)
        invoke_patcher.start()

    def __get_data_from_lambda_manager_http(self, **kwargs):
        url = kwargs["url"]
        if url == "/api/functions":
            return functions["positive"]
        else:
            func_id = url.split("/")[-1]
            if func_id in functions["positive"]:
                if func_id in [id_function_state_building, id_function_state_error]:
                    r = requests.RequestException()
                    r.response = HttpResponseServerError()
                    raise r # raise 500 Internal_Server error

                return functions["positive"][func_id]
            else:
                r = requests.HTTPError()
                r.response = HttpResponseNotFound()
                raise r # raise 404 Not Found error

    def __invoke_function(self, func, payload):
        data = []
        func_id = func.id
        type_function = functions["positive"][func_id]["metadata"]["annotations"]["type"]
        if type_function == "reid":
            if func_id == id_function_reid_response_data:
                data = [0, 1]
            else:
                data = []
        elif type_function == "tracker":
            data = {
                "shape": [12.34, 34.0, 35.01, 41.99],
                "state": {"key": "value"},
            }
        elif type_function == "interactor":
            data = [
                [8, 12],
                [34, 56],
                [77, 77],
            ]
        elif type_function == "detector":
            data = [
                {'confidence': '0.9959098', 'label': 'car', 'points': [3, 3, 15, 15], 'type': 'rectangle'},
                {'confidence': '0.89535173', 'label': 'car', 'points': [20, 25, 30, 35], 'type': 'rectangle'},
                {'confidence': '0.59464583', 'label': 'car', 'points': [12.17, 45.0, 69.80, 18.99], 'type': 'polygon'},
            ]

        return data

    @classmethod
    def _create_db_users(cls):
        (group_admin, _) = Group.objects.get_or_create(name="admin")
        (group_user, _) = Group.objects.get_or_create(name="business")

        user_admin = User.objects.create_superuser(username="admin", email="",
            password="admin")
        user_admin.groups.add(group_admin)
        user_dummy = User.objects.create_user(username="user", password="user",
            email="user@example.com")
        user_dummy.groups.add(group_user)

        cls.admin = user_admin
        cls.user = user_dummy


    def _create_task(self, data, image_data, *, owner=None, org_id=None):
        with ForceLogin(owner or self.admin, self.client):
            response = self.client.post('/api/tasks', data=data, format="json",
                QUERY_STRING=f'org_id={org_id}' if org_id is not None else None)
            assert response.status_code == status.HTTP_201_CREATED, response.status_code
            tid = response.data["id"]

            response = self.client.post("/api/tasks/%s/data" % tid,
                data=image_data,
                QUERY_STRING=f'org_id={org_id}' if org_id is not None else None)
            assert response.status_code == status.HTTP_202_ACCEPTED, response.status_code

            response = self.client.get("/api/tasks/%s" % tid,
                QUERY_STRING=f'org_id={org_id}' if org_id is not None else None)
            task = response.data

        return task


    def _generate_task_images(self, count): # pylint: disable=no-self-use
        images = {
            "client_files[%d]" % i: generate_image_file("image_%d.jpg" % i)
            for i in range(count)
        }
        images["image_quality"] = 75
        return images


    @classmethod
    def setUpTestData(cls):
        cls._create_db_users()


    def _get_request(self, path, user, *, org_id=None):
        with ForceLogin(user, self.client):
            response = self.client.get(path,
                QUERY_STRING=f'org_id={org_id}' if org_id is not None else '')
        return response


    def _delete_request(self, path, user, *, org_id=None):
        with ForceLogin(user, self.client):
            response = self.client.delete(path,
                QUERY_STRING=f'org_id={org_id}' if org_id is not None else '')
        return response


    def _post_request(self, path, user, data, *, org_id=None):
        data = json.dumps(data)
        with ForceLogin(user, self.client):
            response = self.client.post(path, data=data, content_type='application/json',
                QUERY_STRING=f'org_id={org_id}' if org_id is not None else '')
        return response


    def _patch_request(self, path, user, data, *, org_id=None):
        data = json.dumps(data)
        with ForceLogin(user, self.client):
            response = self.client.patch(path, data=data, content_type='application/json',
                QUERY_STRING=f'org_id={org_id}' if org_id is not None else '')
        return response


    def _check_expected_keys_in_response_function(self, data):
        kind = data["kind"]
        if kind == "interactor":
            for key in expected_keys_in_response_function_interactor:
                self.assertIn(key, data)
        elif kind == "tracker":
            for key in expected_keys_in_response_function_tracker:
                self.assertIn(key, data)
        else:
            for key in expected_keys_in_response_all_functions:
                self.assertIn(key, data)


class LambdaTestCases(_LambdaTestCaseBase):
    def setUp(self):
        super().setUp()

        images_main_task = self._generate_task_images(3)
        images_assigneed_to_user_task = self._generate_task_images(3)
        self.main_task = self._create_task(tasks["main"], images_main_task)
        self.assigneed_to_user_task = self._create_task(
            tasks["assigneed_to_user"], images_assigneed_to_user_task
        )

    def test_api_v2_lambda_functions_list(self):
        response = self._get_request(LAMBDA_FUNCTIONS_PATH, self.admin)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for data in response.data:
            self._check_expected_keys_in_response_function(data)

        response = self._get_request(LAMBDA_FUNCTIONS_PATH, self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for data in response.data:
            self._check_expected_keys_in_response_function(data)

        response = self._get_request(LAMBDA_FUNCTIONS_PATH, None)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    @mock.patch('cvat.apps.lambda_manager.views.LambdaGateway._http', return_value = {})
    def test_api_v2_lambda_functions_list_empty(self, mock_http):
        response = self._get_request(LAMBDA_FUNCTIONS_PATH, self.admin)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        response = self._get_request(LAMBDA_FUNCTIONS_PATH, self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        response = self._get_request(LAMBDA_FUNCTIONS_PATH, None)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    @mock.patch('cvat.apps.lambda_manager.views.LambdaGateway._http', return_value = functions["negative"])
    def test_api_v2_lambda_functions_list_wrong(self, mock_http):
        response = self._get_request(LAMBDA_FUNCTIONS_PATH, self.admin)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_api_v2_lambda_functions_read(self):
        ids_functions = [id_function_detector, id_function_interactor,\
                         id_function_tracker, id_function_reid_response_data, \
                         id_function_non_type, id_function_wrong_type, id_function_unknown_type]

        for id_func in ids_functions:
            path = f'{LAMBDA_FUNCTIONS_PATH}/{id_func}'

            response = self._get_request(path, self.admin)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self._check_expected_keys_in_response_function(response.data)

            response = self._get_request(path, self.user)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self._check_expected_keys_in_response_function(response.data)

            response = self._get_request(path, None)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_api_v2_lambda_functions_read_wrong_id(self):
        id_wrong_function = "test-functions-wrong-id"
        response = self._get_request(f'{LAMBDA_FUNCTIONS_PATH}/{id_wrong_function}', self.admin)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self._get_request(f'{LAMBDA_FUNCTIONS_PATH}/{id_wrong_function}', self.user)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self._get_request(f'{LAMBDA_FUNCTIONS_PATH}/{id_wrong_function}', None)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    @mock.patch('cvat.apps.lambda_manager.views.LambdaGateway._http', return_value = functions["negative"][id_function_non_unique_labels])
    def test_api_v2_lambda_functions_read_non_unique_labels(self, mock_http):
        response = self._get_request(f'{LAMBDA_FUNCTIONS_PATH}/{id_function_non_unique_labels}', self.admin)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    @skip("Fail: add mock")
    def test_api_v2_lambda_requests_list(self):
        response = self._get_request(LAMBDA_REQUESTS_PATH, self.admin)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in expected_keys_in_response_requests:
            self.assertIn(key, response.data[0])

        response = self._get_request(LAMBDA_REQUESTS_PATH, self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in expected_keys_in_response_requests:
            self.assertIn(key, response.data[0])

        response = self._get_request(LAMBDA_REQUESTS_PATH, None)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_api_v2_lambda_requests_list_empty(self):
        response = self._get_request(LAMBDA_REQUESTS_PATH, self.admin)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        response = self._get_request(LAMBDA_REQUESTS_PATH, self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        response = self._get_request(LAMBDA_REQUESTS_PATH, None)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_api_v2_lambda_requests_read(self):
        # create request
        data_main_task = {
            "function": id_function_detector,
            "task": self.main_task["id"],
            "cleanup": True,
            "threshold": 55,
            "quality": "original",
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(LAMBDA_REQUESTS_PATH, self.admin, data_main_task)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        id_request = response.data["id"]

        response = self._get_request(f'{LAMBDA_REQUESTS_PATH}/{id_request}', self.admin)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in expected_keys_in_response_requests:
            self.assertIn(key, response.data)

        response = self._get_request(f'{LAMBDA_REQUESTS_PATH}/{id_request}', self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in expected_keys_in_response_requests:
            self.assertIn(key, response.data)

        response = self._get_request(f'{LAMBDA_REQUESTS_PATH}/{id_request}', None)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_api_v2_lambda_requests_read_wrong_id(self):
        id_request = "cf343b95-afeb-475e-ab53-8d7e64991d30-wrong-id"

        response = self._get_request(f'{LAMBDA_REQUESTS_PATH}/{id_request}', self.admin)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self._get_request(f'{LAMBDA_REQUESTS_PATH}/{id_request}', self.user)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self._get_request(f'{LAMBDA_REQUESTS_PATH}/{id_request}', None)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_api_v2_lambda_requests_delete_finished_request(self):
        data = {
            "function": id_function_detector,
            "task": self.main_task["id"],
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(f'{LAMBDA_REQUESTS_PATH}', self.admin, data)
        id_request = response.data["id"]

        response = self._delete_request(f'{LAMBDA_REQUESTS_PATH}/{id_request}', None)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self._delete_request(f'{LAMBDA_REQUESTS_PATH}/{id_request}', self.admin)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self._get_request(f'{LAMBDA_REQUESTS_PATH}/{id_request}', self.admin)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self._post_request(f'{LAMBDA_REQUESTS_PATH}', self.admin, data)
        id_request = response.data["id"]
        response = self._delete_request(f'{LAMBDA_REQUESTS_PATH}/{id_request}', self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self._get_request(f'{LAMBDA_REQUESTS_PATH}/{id_request}', self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    @skip("Fail: add mock")
    def test_api_v2_lambda_requests_delete_not_finished_request(self):
        pass


    def test_api_v2_lambda_requests_create(self):
        ids_functions = [id_function_detector, id_function_interactor, id_function_tracker, \
                         id_function_reid_response_data, id_function_detector, id_function_reid_response_no_data, \
                         id_function_non_type, id_function_wrong_type, id_function_unknown_type]

        for id_func in ids_functions:
            data_main_task = {
                "function": id_func,
                "task": self.main_task["id"],
                "cleanup": True,
                "threshold": 55,
                "quality": "original",
                "mapping": {
                    "car": { "name": "car" },
                },
            }
            data_assigneed_to_user_task = {
                "function": id_func,
                "task": self.assigneed_to_user_task["id"],
                "cleanup": False,
                "quality": "compressed",
                "max_distance": 70,
                "mapping": {
                    "car": { "name": "car" },
                },
            }

            response = self._post_request(LAMBDA_REQUESTS_PATH, self.admin, data_main_task)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            for key in expected_keys_in_response_requests:
                self.assertIn(key, response.data)

            response = self._post_request(LAMBDA_REQUESTS_PATH, self.user, data_assigneed_to_user_task)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            for key in expected_keys_in_response_requests:
                self.assertIn(key, response.data)

            response = self._post_request(LAMBDA_REQUESTS_PATH, self.user, data_main_task)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            response = self._post_request(LAMBDA_REQUESTS_PATH, None, data_main_task)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    @mock.patch('cvat.apps.lambda_manager.views.LambdaGateway._http', return_value = functions["negative"]["test-model-has-non-unique-labels"])
    def test_api_v2_lambda_requests_create_non_unique_labels(self, mock_http):
        data = {
            "function": id_function_non_unique_labels,
            "task": self.main_task["id"],
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }

        response = self._post_request(LAMBDA_REQUESTS_PATH, self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_api_v2_lambda_requests_create_empty_data(self):
        data = {}
        response = self._post_request(LAMBDA_REQUESTS_PATH, self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_api_v2_lambda_requests_create_without_function(self):
        data = {
            "task": self.main_task["id"],
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(LAMBDA_REQUESTS_PATH, self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_api_v2_lambda_requests_create_wrong_id_function(self):
        data = {
            "function": "test-requests-wrong-id",
            "task": self.main_task["id"],
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(LAMBDA_REQUESTS_PATH, self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    @skip("Fail: add mock")
    def test_api_v2_lambda_requests_create_two_requests(self):
        data = {
            "function": id_function_detector,
            "task": self.main_task["id"],
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        self._post_request(LAMBDA_REQUESTS_PATH, self.admin, data)
        response = self._post_request(LAMBDA_REQUESTS_PATH, self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


    def test_api_v2_lambda_requests_create_empty_mapping(self):
        data = {
            "function": id_function_detector,
            "task": self.main_task["id"],
            "cleanup": True,
            "mapping": {},
        }
        response = self._post_request(LAMBDA_REQUESTS_PATH, self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in expected_keys_in_response_requests:
            self.assertIn(key, response.data)


    def test_api_v2_lambda_requests_create_without_cleanup(self):
        data = {
            "function": id_function_detector,
            "task": self.main_task["id"],
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(LAMBDA_REQUESTS_PATH, self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in expected_keys_in_response_requests:
            self.assertIn(key, response.data)


    def test_api_v2_lambda_requests_create_without_mapping(self):
        data = {
            "function": id_function_detector,
            "task": self.main_task["id"],
            "cleanup": True,
        }
        response = self._post_request(LAMBDA_REQUESTS_PATH, self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in expected_keys_in_response_requests:
            self.assertIn(key, response.data)


    def test_api_v2_lambda_requests_create_without_task(self):
        data = {
            "function": id_function_detector,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(LAMBDA_REQUESTS_PATH, self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_api_v2_lambda_requests_create_wrong_id_task(self):
        data = {
            "function": id_function_detector,
            "task": 12345,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(LAMBDA_REQUESTS_PATH, self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_api_v2_lambda_requests_create_is_not_ready(self):
        ids_functions = [id_function_state_building, id_function_state_error]

        for id_func in ids_functions:
            data = {
                "function": id_func,
                "task": self.main_task["id"],
                "cleanup": True,
                "mapping": {
                    "car": { "name": "car" },
                },
            }

            response = self._post_request(LAMBDA_REQUESTS_PATH, self.admin, data)
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


    def test_api_v2_lambda_functions_create_detector(self):
        data_main_task = {
            "task": self.main_task["id"],
            "frame": 0,
            "cleanup": True,
            "threshold": 0.55,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        data_assigneed_to_user_task = {
            "task": self.assigneed_to_user_task["id"],
            "frame": 0,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.admin, data_main_task)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.user, data_assigneed_to_user_task)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", None, data_main_task)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @skip("Fail: expected result != actual result") # TODO move test to test_api_v2_lambda_functions_create
    def test_api_v2_lambda_functions_create_user_assigned_to_no_user(self):
        data = {
            "task": self.main_task["id"],
            "frame": 0,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.user, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_api_v2_lambda_functions_create_interactor(self):
        data_main_task = {
            "task": self.main_task["id"],
            "frame": 0,
            "pos_points": [
				[3.45, 6.78],
				[12.1, 12.1],
                [34.1, 41.0],
				[43.01, 43.99],
            ],
            "neg_points": [
				[3.25, 6.58],
				[11.1, 11.0],
				[35.5, 44.44],
				[45.01, 45.99],
			],
        }
        data_assigneed_to_user_task = {
            "task": self.assigneed_to_user_task["id"],
            "frame": 0,
            "threshold": 0.1,
            "pos_points": [
				[3.45, 6.78],
				[12.1, 12.1],
                [34.1, 41.0],
				[43.01, 43.99],
            ],
            "neg_points": [
				[3.25, 6.58],
				[11.1, 11.0],
				[35.5, 44.44],
				[45.01, 45.99],
			],
        }

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_interactor}", self.admin, data_main_task)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_interactor}", self.user, data_assigneed_to_user_task)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_interactor}", None, data_main_task)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_api_v2_lambda_functions_create_tracker(self):
        data_main_task = {
            "task": self.main_task["id"],
            "frame": 0,
            "shape": [
				12.12,
				34.45,
				54.0,
				76.12,
			],
        }
        data_assigneed_to_user_task = {
            "task": self.assigneed_to_user_task["id"],
            "frame": 0,
            "shape": [
				12.12,
				34.45,
				54.0,
				76.12,
			],
        }

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_tracker}", self.admin, data_main_task)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_tracker}", self.user, data_assigneed_to_user_task)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_tracker}", None, data_main_task)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_api_v2_lambda_functions_create_reid(self):
        data_main_task = {
            "task": self.main_task["id"],
            "frame0": 0,
            "frame1": 1,
            "boxes0": [
                OrderedDict([('attributes', []), ('frame', 0), ('group', None), ('id', 11258), ('label_id', 8), ('occluded', False), ('path_id', 0), ('points', [137.0, 129.0, 457.0, 676.0]), ('source', 'auto'), ('type', 'rectangle'), ('z_order', 0)]),
                OrderedDict([('attributes', []), ('frame', 0), ('group', None), ('id', 11259), ('label_id', 8), ('occluded', False), ('path_id', 1), ('points', [1511.0, 224.0, 1537.0, 437.0]), ('source', 'auto'), ('type', 'rectangle'), ('z_order', 0)]),
            ],
            "boxes1": [
                OrderedDict([('attributes', []), ('frame', 1), ('group', None), ('id', 11260), ('label_id', 8), ('occluded', False), ('points', [1076.0, 199.0, 1218.0, 593.0]), ('source', 'auto'), ('type', 'rectangle'), ('z_order', 0)]),
                OrderedDict([('attributes', []), ('frame', 1), ('group', None), ('id', 11261), ('label_id', 8), ('occluded', False), ('points', [924.0, 177.0, 1090.0, 615.0]), ('source', 'auto'), ('type', 'rectangle'), ('z_order', 0)]),
            ],
            "quality": None,
            "threshold": 0.5,
            "max_distance": 55,
        }
        data_assigneed_to_user_task = {
            "task": self.assigneed_to_user_task["id"],
            "frame0": 0,
            "frame1": 1,
            "boxes0": [
                OrderedDict([('attributes', []), ('frame', 0), ('group', None), ('id', 11258), ('label_id', 8), ('occluded', False), ('path_id', 0), ('points', [137.0, 129.0, 457.0, 676.0]), ('source', 'auto'), ('type', 'rectangle'), ('z_order', 0)]),
                OrderedDict([('attributes', []), ('frame', 0), ('group', None), ('id', 11259), ('label_id', 8), ('occluded', False), ('path_id', 1), ('points', [1511.0, 224.0, 1537.0, 437.0]), ('source', 'auto'), ('type', 'rectangle'), ('z_order', 0)]),
            ],
            "boxes1": [
                OrderedDict([('attributes', []), ('frame', 1), ('group', None), ('id', 11260), ('label_id', 8), ('occluded', False), ('points', [1076.0, 199.0, 1218.0, 593.0]), ('source', 'auto'), ('type', 'rectangle'), ('z_order', 0)]),
                OrderedDict([('attributes', []), ('frame', 1), ('group', 0), ('id', 11398), ('label_id', 8), ('occluded', False), ('points', [184.3935546875, 211.5048828125, 331.64968722073354, 97.27792672028772, 445.87667560321825, 126.17873100983161, 454.13404825737416, 691.8087578194827, 180.26452189455085]), ('source', 'manual'), ('type', 'polygon'), ('z_order', 0)]),
            ],
            "quality": None,
        }

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_reid_response_data}", self.admin, data_main_task)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_reid_response_data}", self.user, data_assigneed_to_user_task)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_reid_response_data}", None, data_main_task)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_reid_response_no_data}", self.admin, data_main_task)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_reid_response_no_data}", self.user, data_assigneed_to_user_task)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_reid_response_no_data}", None, data_main_task)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_api_v2_lambda_functions_create_non_type(self):
        data = {
            "task": self.main_task["id"],
            "frame": 0,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_non_type}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


    def test_api_v2_lambda_functions_create_wrong_type(self):
        data = {
            "task": self.main_task["id"],
            "frame": 0,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_wrong_type}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


    def test_api_v2_lambda_functions_create_unknown_type(self):
        data = {
            "task": self.main_task["id"],
            "frame": 0,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_unknown_type}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


    @mock.patch('cvat.apps.lambda_manager.views.LambdaGateway._http', return_value = functions["negative"]["test-model-has-non-unique-labels"])
    def test_api_v2_lambda_functions_create_non_unique_labels(self, mock_http):
        data = {
            "task": self.main_task["id"],
            "frame": 0,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_non_unique_labels}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_api_v2_lambda_functions_create_quality(self):
        qualities = [None, "original", "compressed"]

        for quality in qualities:
            data = {
                "task": self.main_task["id"],
                "frame": 0,
                "cleanup": True,
                "quality": quality,
                "mapping": {
                    "car": { "name": "car" },
                },
            }

            response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.admin, data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = {
            "task": self.main_task["id"],
            "frame": 0,
            "cleanup": True,
            "quality": "test-error-quality",
            "mapping": {
                "car": { "name": "car" },
            },
        }

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_api_v2_lambda_functions_create_empty_data(self):
        data = {}
        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_api_v2_lambda_functions_create_detector_empty_mapping(self):
        data = {
            "task": self.main_task["id"],
            "frame": 0,
            "cleanup": True,
            "mapping": {},
        }
        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_api_v2_lambda_functions_create_detector_without_cleanup(self):
        data = {
            "task": self.main_task["id"],
            "frame": 0,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_api_v2_lambda_functions_create_detector_without_mapping(self):
        data = {
            "task": self.main_task["id"],
            "frame": 0,
            "cleanup": True,
        }
        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_api_v2_lambda_functions_create_detector_without_task(self):
        data = {
            "frame": 0,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_api_v2_lambda_functions_create_detector_without_id_frame(self):
        data = {
            "task": self.main_task["id"],
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_api_v2_lambda_functions_create_wrong_id_function(self):
        data = {
            "task": self.main_task["id"],
            "frame": 0,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/test-functions-wrong-id", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_api_v2_lambda_functions_create_wrong_id_task(self):
        data = {
            "task": 12345,
            "frame": 0,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    @skip("Fail: expected result != actual result, issue #2770")
    def test_api_v2_lambda_functions_create_detector_wrong_id_frame(self):
        data = {
            "task": self.main_task["id"],
            "frame": 12345,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    @skip("Fail: add mock and expected result != actual result")
    def test_api_v2_lambda_functions_create_two_functions(self):
        data = {
            "task": self.main_task["id"],
            "frame": 0,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.admin, data)
        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


    def test_api_v2_lambda_functions_create_function_is_not_ready(self):
        data = {
            "task": self.main_task["id"],
            "frame": 0,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }
        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_state_building}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        response = self._post_request(f"{LAMBDA_FUNCTIONS_PATH}/{id_function_state_error}", self.admin, data)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class Issue4996_Cases(_LambdaTestCaseBase):
    # Check regressions for https://github.com/opencv/cvat/issues/4996#issuecomment-1266123032
    # We need to check that job assignee can call functions in the assigned jobs
    # This requires to pass the job id in the call request.

    def _create_org(self, *, owner: int, members: Dict[int, str] = None) -> dict:
        org = self._post_request('/api/organizations', user=owner, data={
            "slug": "testorg",
            "name": "test Org",
        })
        assert org.status_code == status.HTTP_201_CREATED
        org = org.json()

        for uid, role in members.items():
            user = self._get_request('/api/users/self', user=uid)
            assert user.status_code == status.HTTP_200_OK
            user = user.json()

            invitation = self._post_request('/api/invitations', user=owner, data={
                'email': user['email'],
                'role': role,
            }, org_id=org['id'])
            assert invitation.status_code == status.HTTP_201_CREATED

        return org

    def _set_task_assignee(self, task: int, assignee: Optional[int], *,
            org_id: Optional[int] = None):
        response = self._patch_request(f'/api/tasks/{task}', user=self.admin, data={
            'assignee_id': assignee,
        }, org_id=org_id)
        assert response.status_code == status.HTTP_200_OK

    def _set_job_assignee(self, job: int, assignee: Optional[int], *,
            org_id: Optional[int] = None):
        response = self._patch_request(f'/api/jobs/{job}', user=self.admin, data={
            'assignee': assignee,
        }, org_id=org_id)
        assert response.status_code == status.HTTP_200_OK

    def setUp(self):
        self.org = self._create_org(owner=self.admin, members={self.user: 'worker'})

        task = self._create_task(data={
                'name': 'test_task',
                'labels': [{'name': 'cat'}],
                'segment_size': 2
            },
            image_data=self._generate_task_images(6),
            owner=self.admin,
            org_id=self.org['id'],
        )
        self.task = task

        jobs = get_paginated_collection(lambda page:
            self._get_request(
                f"/api/jobs?task_id={self.task['id']}&page={page}",
                self.admin, org_id=self.org['id']
            )
        )
        self.job = jobs[1]

        self.common_data = {
            "task": self.task['id'],
            "frame": 0,
            "cleanup": True,
            "mapping": {
                "car": { "name": "car" },
            },
        }

        self.function_name = f"{LAMBDA_FUNCTIONS_PATH}/{id_function_detector}"

        return super().setUp()

    def _get_valid_job_params(self):
        return {
            "job": self.job['id'],
            "frame": 2
        }

    def _get_invalid_job_params(self):
        return {
            "job": self.job['id'],
            "frame": 0
        }

    def test_can_call_function_for_job_worker_in_org__deny_unassigned_worker_with_task_request(self):
        data = self.common_data.copy()
        with self.subTest(job=None, assignee=None):
            response = self._post_request(self.function_name, self.user, data,
                org_id=self.org['id'])
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_can_call_function_for_job_worker_in_org__deny_unassigned_worker_with_job_request(self):
        data = self.common_data.copy()
        data.update(self._get_valid_job_params())
        with self.subTest(job='defined', assignee=None):
            response = self._post_request(self.function_name, self.user, data,
                org_id=self.org['id'])
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_can_call_function_for_job_worker_in_org__allow_task_assigned_worker_with_task_request(self):
        self._set_task_assignee(self.task['id'], self.user.id, org_id=self.org['id'])

        data = self.common_data.copy()
        with self.subTest(job=None, assignee='task'):
            response = self._post_request(self.function_name, self.user, data,
                org_id=self.org['id'])
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_can_call_function_for_job_worker_in_org__deny_job_assigned_worker_with_task_request(self):
        self._set_job_assignee(self.job['id'], self.user.id, org_id=self.org['id'])

        data = self.common_data.copy()
        with self.subTest(job=None, assignee='job'):
            response = self._post_request(self.function_name, self.user, data,
                org_id=self.org['id'])
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_can_call_function_for_job_worker_in_org__allow_job_assigned_worker_with_job_request(self):
        self._set_job_assignee(self.job['id'], self.user.id, org_id=self.org['id'])

        data = self.common_data.copy()
        data.update(self._get_valid_job_params())
        with self.subTest(job='defined', assignee='job'):
            response = self._post_request(self.function_name, self.user, data,
                org_id=self.org['id'])
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_can_check_job_boundaries_in_function_call__fail_for_frame_outside_job(self):
        self._set_job_assignee(self.job['id'], self.user.id, org_id=self.org['id'])

        data = self.common_data.copy()
        data.update(self._get_invalid_job_params())
        with self.subTest(job='defined', frame='outside'):
            response = self._post_request(self.function_name, self.user, data,
                org_id=self.org['id'])
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_can_check_job_boundaries_in_function_call__ok_for_frame_inside_job(self):
        self._set_job_assignee(self.job['id'], self.user.id, org_id=self.org['id'])

        data = self.common_data.copy()
        data.update(self._get_valid_job_params())
        with self.subTest(job='defined', frame='inside'):
            response = self._post_request(self.function_name, self.user, data,
                org_id=self.org['id'])
            self.assertEqual(response.status_code, status.HTTP_200_OK)
