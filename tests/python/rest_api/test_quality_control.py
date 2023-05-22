# Copyright (C) 2023 CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

import json
from copy import deepcopy
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Tuple

import pytest
from cvat_sdk.api_client import models
from cvat_sdk.api_client.api_client import ApiClient, Endpoint
from cvat_sdk.core.helpers import get_paginated_collection
from deepdiff import DeepDiff

from shared.utils.config import make_api_client

from .utils import CollectionSimpleFilterTestBase


class _PermissionTestBase:
    def create_quality_report(self, user: str, task_id: int):
        with make_api_client(user) as api_client:
            (_, response) = api_client.quality_api.create_report(
                quality_report_create_request=models.QualityReportCreateRequest(task_id=task_id),
                _parse_response=False,
            )
            assert response.status == HTTPStatus.ACCEPTED
            rq_id = response.data.decode()

            while True:
                (_, response) = api_client.quality_api.create_report(
                    rq_id=rq_id, _parse_response=False
                )
                assert response.status in [HTTPStatus.CREATED, HTTPStatus.ACCEPTED]

                if response.status == HTTPStatus.CREATED:
                    break

            return json.loads(response.data)

    def create_gt_job(self, user, task_id):
        with make_api_client(user) as api_client:
            (meta, _) = api_client.tasks_api.retrieve_data_meta(task_id)
            start_frame = meta.start_frame

            (job, _) = api_client.jobs_api.create(
                models.JobWriteRequest(
                    type="ground_truth",
                    task_id=task_id,
                    frame_selection_method="manual",
                    frames=[start_frame],
                )
            )

            (labels, _) = api_client.labels_api.list(task_id=task_id)
            api_client.jobs_api.update_annotations(
                job.id,
                job_annotations_update_request=dict(
                    shapes=[
                        dict(
                            frame=start_frame,
                            label_id=labels.results[0].id,
                            type="rectangle",
                            points=[1, 1, 2, 2],
                        ),
                    ],
                ),
            )

        return job


@pytest.mark.usefixtures("restore_db_per_class")
class TestListQualityReports(_PermissionTestBase):
    def _test_list_reports_200(self, user, task_id, *, expected_data=None, **kwargs):
        with make_api_client(user) as api_client:
            results = get_paginated_collection(
                api_client.quality_api.list_reports_endpoint,
                return_json=True,
                task_id=task_id,
                **kwargs,
            )

            if expected_data is not None:
                assert DeepDiff(expected_data, results) == {}

    def _test_list_reports_403(self, user, task_id, **kwargs):
        with make_api_client(user) as api_client:
            (_, response) = api_client.quality_api.list_reports(
                task_id=task_id, **kwargs, _parse_response=False, _check_status=False
            )

            assert response.status == HTTPStatus.FORBIDDEN

    def test_can_list_quality_reports(self, admin_user, quality_reports):
        parent_report = next(r for r in quality_reports if r["task_id"])
        task_id = parent_report["task_id"]
        reports = [parent_report] + [
            r for r in quality_reports if r["parent_id"] == parent_report["id"]
        ]

        self._test_list_reports_200(admin_user, task_id, expected_data=reports)

    @pytest.mark.usefixtures("restore_db_per_function")
    @pytest.mark.parametrize("is_staff, allow", [(True, True), (False, False)])
    def test_user_list_reports_in_sandbox_task(
        self, tasks, jobs, users, is_task_staff, is_staff, allow, admin_user
    ):
        task = next(
            t
            for t in tasks
            if t["organization"] is None
            and not users[t["owner"]["id"]]["is_superuser"]
            and not any(j for j in jobs if j["task_id"] == t["id"] and j["type"] == "ground_truth")
        )

        if is_staff:
            user = task["owner"]["username"]
        else:
            user = next(u for u in users if not is_task_staff(u["id"], task["id"]))["username"]

        self.create_gt_job(admin_user, task["id"])
        report = self.create_quality_report(admin_user, task["id"])

        if allow:
            self._test_list_reports_200(user, task["id"], expected_data=[report], target="task")
        else:
            self._test_list_reports_403(user, task["id"])

    @pytest.mark.usefixtures("restore_db_per_function")
    @pytest.mark.parametrize(
        "org_role, is_staff, allow",
        [
            ("owner", True, True),
            ("owner", False, True),
            ("maintainer", True, True),
            ("maintainer", False, True),
            ("supervisor", True, True),
            ("supervisor", False, False),
            ("worker", True, True),
            ("worker", False, False),
        ],
    )
    def test_user_list_reports_in_org_task(
        self,
        tasks,
        jobs,
        users,
        is_org_member,
        is_task_staff,
        org_role,
        is_staff,
        allow,
        admin_user,
    ):
        for user in users:
            task = next(
                (
                    t
                    for t in tasks
                    if t["organization"] is not None
                    and is_task_staff(user["id"], t["id"]) == is_staff
                    and is_org_member(user["id"], t["organization"], role=org_role)
                    and not any(
                        j for j in jobs if j["task_id"] == t["id"] and j["type"] == "ground_truth"
                    )
                ),
                None,
            )
            if task is not None:
                break

        assert task

        org_id = task["organization"]
        extra_kwargs = {"org_id": org_id}

        self.create_gt_job(admin_user, task["id"])
        report = self.create_quality_report(admin_user, task["id"])

        if allow:
            self._test_list_reports_200(
                user["username"], task["id"], expected_data=[report], **extra_kwargs, target="task"
            )
        else:
            self._test_list_reports_403(user["username"], task["id"], **extra_kwargs)


@pytest.mark.usefixtures("restore_db_per_class")
class TestGetQualityReports(_PermissionTestBase):
    def _test_get_report_200(
        self, user: str, obj_id: int, *, expected_data: Optional[Dict[str, Any]] = None, **kwargs
    ):
        with make_api_client(user) as api_client:
            (_, response) = api_client.quality_api.retrieve_report(obj_id, **kwargs)
            assert response.status == HTTPStatus.OK

        if expected_data is not None:
            assert DeepDiff(expected_data, json.loads(response.data), ignore_order=True) == {}

        return response

    def _test_get_report_403(self, user: str, obj_id: int, **kwargs):
        with make_api_client(user) as api_client:
            (_, response) = api_client.quality_api.retrieve_report(
                obj_id, **kwargs, _parse_response=False, _check_status=False
            )
            assert response.status == HTTPStatus.FORBIDDEN

        return response

    @pytest.mark.parametrize("target", ["task", "job"])
    def test_can_get_full_report_data(self, admin_user, target, quality_reports):
        report = next(r for r in quality_reports if (r["job_id"] is not None) == (target == "job"))
        report_id = report["id"]

        with make_api_client(admin_user) as api_client:
            (report_data, response) = api_client.quality_api.retrieve_report_data(report_id)
            assert response.status == HTTPStatus.OK

        # Just check several keys exist
        for key in ["parameters", "comparison_summary", "frame_results"]:
            assert key in report_data.keys(), key

    @pytest.mark.usefixtures("restore_db_per_function")
    @pytest.mark.parametrize("is_staff, allow", [(True, True), (False, False)])
    def test_user_get_report_in_sandbox_task(
        self, tasks, jobs, users, is_task_staff, is_staff, allow, admin_user
    ):
        task = next(
            t
            for t in tasks
            if t["organization"] is None
            and not users[t["owner"]["id"]]["is_superuser"]
            and not any(j for j in jobs if j["task_id"] == t["id"] and j["type"] == "ground_truth")
        )

        if is_staff:
            user = task["owner"]["username"]
        else:
            user = next(u for u in users if not is_task_staff(u["id"], task["id"]))["username"]

        self.create_gt_job(admin_user, task["id"])
        report = self.create_quality_report(admin_user, task["id"])

        if allow:
            self._test_get_report_200(user, report["id"], expected_data=report)
        else:
            self._test_get_report_403(user, report["id"])

    @pytest.mark.usefixtures("restore_db_per_function")
    @pytest.mark.parametrize(
        "org_role, is_staff, allow",
        [
            ("owner", True, True),
            ("owner", False, True),
            ("maintainer", True, True),
            ("maintainer", False, True),
            ("supervisor", True, True),
            ("supervisor", False, False),
            ("worker", True, True),
            ("worker", False, False),
        ],
    )
    def test_user_get_report_in_org_task(
        self,
        tasks,
        jobs,
        users,
        is_org_member,
        is_task_staff,
        org_role,
        is_staff,
        allow,
        admin_user,
    ):
        for user in users:
            task = next(
                (
                    t
                    for t in tasks
                    if t["organization"] is not None
                    and is_task_staff(user["id"], t["id"]) == is_staff
                    and is_org_member(user["id"], t["organization"], role=org_role)
                    and not any(
                        j for j in jobs if j["task_id"] == t["id"] and j["type"] == "ground_truth"
                    )
                ),
                None,
            )
            if task is not None:
                break

        assert task

        org_id = task["organization"]
        extra_kwargs = {"org_id": org_id}

        self.create_gt_job(admin_user, task["id"])
        report = self.create_quality_report(admin_user, task["id"])

        if allow:
            self._test_get_report_200(
                user["username"], report["id"], expected_data=report, **extra_kwargs
            )
        else:
            self._test_get_report_403(user["username"], report["id"], **extra_kwargs)


@pytest.mark.usefixtures("restore_db_per_function")
class TestPostQualityReports(_PermissionTestBase):
    def test_can_create_report(self, admin_user, jobs):
        gt_job = next(j for j in jobs if j["type"] == "ground_truth")
        task_id = gt_job["task_id"]

        report = self.create_quality_report(admin_user, task_id)
        assert models.QualityReport._from_openapi_data(**report)


class TestSimpleQualityReportsFilters(CollectionSimpleFilterTestBase):
    @pytest.fixture(autouse=True)
    def setup(self, restore_db_per_class, admin_user, quality_reports, jobs):
        self.user = admin_user
        self.samples = quality_reports
        self.job_samples = jobs

    def _get_endpoint(self, api_client: ApiClient) -> Endpoint:
        return api_client.quality_api.list_reports_endpoint

    def _get_field_samples(self, field: str) -> Tuple[Any, List[Dict[str, Any]]]:
        if field == "task_id":
            # This filter includes both the task and nested job reports
            task_id, task_reports = super()._get_field_samples(field)
            task_job_ids = set(j["id"] for j in self.job_samples if j["task_id"] == task_id)
            task_reports = list(task_reports) + [
                r
                for r in self.samples
                if self._get_field(r, self._map_field("job_id")) in task_job_ids
            ]
            return task_id, task_reports
        else:
            return super()._get_field_samples(field)

    @pytest.mark.parametrize(
        "field",
        ("task_id", "job_id", "parent_id", "target"),
    )
    def test_can_use_simple_filter_for_object_list(self, field):
        return super().test_can_use_simple_filter_for_object_list(field)


@pytest.mark.usefixtures("restore_db_per_class")
class TestListQualityConflicts(_PermissionTestBase):
    def _test_list_conflicts_200(self, user, report_id, *, expected_data=None, **kwargs):
        with make_api_client(user) as api_client:
            results = get_paginated_collection(
                api_client.quality_api.list_conflicts_endpoint,
                return_json=True,
                report_id=report_id,
                **kwargs,
            )

            if expected_data is not None:
                assert DeepDiff(expected_data, results) == {}

        return results

    def _test_list_conflicts_403(self, user, report_id, **kwargs):
        with make_api_client(user) as api_client:
            (_, response) = api_client.quality_api.list_conflicts(
                report_id=report_id, **kwargs, _parse_response=False, _check_status=False
            )

            assert response.status == HTTPStatus.FORBIDDEN

    def test_can_list_job_report_conflicts(self, admin_user, quality_reports, quality_conflicts):
        report = next(r for r in quality_reports if r["job_id"])
        conflicts = [c for c in quality_conflicts if c["report_id"] == report["id"]]

        self._test_list_conflicts_200(admin_user, report["id"], expected_data=conflicts)

    @pytest.mark.usefixtures("restore_db_per_function")
    @pytest.mark.parametrize("is_staff, allow", [(True, True), (False, False)])
    def test_user_list_conflicts_in_sandbox_task(
        self, tasks, jobs, users, is_task_staff, is_staff, allow, admin_user
    ):
        task = next(
            t
            for t in tasks
            if t["organization"] is None
            and not users[t["owner"]["id"]]["is_superuser"]
            and not any(j for j in jobs if j["task_id"] == t["id"] and j["type"] == "ground_truth")
        )

        if is_staff:
            user = task["owner"]["username"]
        else:
            user = next(u for u in users if not is_task_staff(u["id"], task["id"]))["username"]

        self.create_gt_job(admin_user, task["id"])
        report = self.create_quality_report(admin_user, task["id"])
        conflicts = self._test_list_conflicts_200(admin_user, report_id=report["id"])
        assert conflicts

        if allow:
            self._test_list_conflicts_200(user, report["id"], expected_data=conflicts)
        else:
            self._test_list_conflicts_200(user, report["id"], expected_data=[])

    @pytest.mark.usefixtures("restore_db_per_function")
    @pytest.mark.parametrize(
        "org_role, is_staff, allow",
        [
            ("owner", True, True),
            ("owner", False, True),
            ("maintainer", True, True),
            ("maintainer", False, True),
            ("supervisor", True, True),
            ("supervisor", False, False),
            ("worker", True, True),
            ("worker", False, False),
        ],
    )
    def test_user_list_conflicts_in_org_task(
        self,
        tasks,
        jobs,
        users,
        is_org_member,
        is_task_staff,
        org_role,
        is_staff,
        allow,
        admin_user,
    ):
        for user in users:
            task = next(
                (
                    t
                    for t in tasks
                    if t["organization"] is not None
                    and is_task_staff(user["id"], t["id"]) == is_staff
                    and is_org_member(user["id"], t["organization"], role=org_role)
                    and not any(
                        j for j in jobs if j["task_id"] == t["id"] and j["type"] == "ground_truth"
                    )
                ),
                None,
            )
            if task is not None:
                break

        assert task
        user = user["username"]

        org_id = task["organization"]
        extra_kwargs = {"org_id": org_id}

        self.create_gt_job(admin_user, task["id"])
        report = self.create_quality_report(admin_user, task["id"])
        conflicts = self._test_list_conflicts_200(
            admin_user, report_id=report["id"], **extra_kwargs
        )
        assert conflicts

        if allow:
            self._test_list_conflicts_200(
                user, report["id"], expected_data=conflicts, **extra_kwargs
            )
        else:
            self._test_list_conflicts_200(user, report["id"], expected_data=[], **extra_kwargs)


class TestSimpleQualityConflictsFilters(CollectionSimpleFilterTestBase):
    @pytest.fixture(autouse=True)
    def setup(self, restore_db_per_class, admin_user, quality_conflicts, quality_reports):
        self.user = admin_user
        self.samples = quality_conflicts
        self.report_samples = quality_reports

    def _get_endpoint(self, api_client: ApiClient) -> Endpoint:
        return api_client.quality_api.list_conflicts_endpoint

    def _get_field_samples(self, field: str) -> Tuple[Any, List[Dict[str, Any]]]:
        if field == "job_id":
            # This field is not included in the response
            job_id = self._find_valid_field_value(self.report_samples, field_path=["job_id"])
            job_reports = set(r["id"] for r in self.report_samples if r["job_id"] == job_id)
            job_conflicts = [
                c
                for c in self.samples
                if self._get_field(c, self._map_field("report_id")) in job_reports
            ]
            return job_id, job_conflicts
        elif field == "task_id":
            # This field is not included in the response
            task_report = next(r for r in self.report_samples if r["task_id"])
            task_reports = {task_report["id"]} | {
                r["id"] for r in self.report_samples if r["parent_id"] == task_report["id"]
            }
            task_conflicts = [
                c
                for c in self.samples
                if self._get_field(c, self._map_field("report_id")) in task_reports
            ]
            return task_report["task_id"], task_conflicts
        else:
            return super()._get_field_samples(field)

    @pytest.mark.parametrize(
        "field",
        ("report_id", "importance", "type", "frame", "job_id", "task_id"),
    )
    def test_can_use_simple_filter_for_object_list(self, field):
        return super().test_can_use_simple_filter_for_object_list(field)


@pytest.mark.usefixtures("restore_db_per_class")
class TestGetSettings(_PermissionTestBase):
    def _test_get_settings_200(
        self, user: str, obj_id: int, *, expected_data: Optional[Dict[str, Any]] = None, **kwargs
    ):
        with make_api_client(user) as api_client:
            (_, response) = api_client.quality_api.retrieve_settings(obj_id, **kwargs)
            assert response.status == HTTPStatus.OK

        if expected_data is not None:
            assert DeepDiff(expected_data, json.loads(response.data), ignore_order=True) == {}

        return response

    def _test_get_settings_403(self, user: str, obj_id: int, **kwargs):
        with make_api_client(user) as api_client:
            (_, response) = api_client.quality_api.retrieve_settings(
                obj_id, **kwargs, _parse_response=False, _check_status=False
            )
            assert response.status == HTTPStatus.FORBIDDEN

        return response

    def test_can_get_settings(self, admin_user, quality_settings):
        settings_id, settings = next(iter(quality_settings.items()))
        self._test_get_settings_200(admin_user, settings_id, expected_data=settings)

    @pytest.mark.parametrize("is_staff, allow", [(True, True), (False, False)])
    def test_user_get_settings_in_sandbox_task(
        self, quality_settings, tasks, users, is_task_staff, is_staff, allow
    ):
        task = next(
            t
            for t in tasks
            if t["organization"] is None and not users[t["owner"]["id"]]["is_superuser"]
        )

        if is_staff:
            user = task["owner"]["username"]
        else:
            user = next(u for u in users if not is_task_staff(u["id"], task["id"]))["username"]

        settings_id = task["quality_settings"]
        settings = quality_settings[settings_id]

        if allow:
            self._test_get_settings_200(user, settings_id, expected_data=settings)
        else:
            self._test_get_settings_403(user, settings_id)

    @pytest.mark.parametrize(
        "org_role, is_staff, allow",
        [
            ("owner", True, True),
            ("owner", False, True),
            ("maintainer", True, True),
            ("maintainer", False, True),
            ("supervisor", True, True),
            ("supervisor", False, False),
            ("worker", True, True),
            ("worker", False, False),
        ],
    )
    def test_user_get_settings_in_org_task(
        self,
        tasks,
        users,
        is_org_member,
        is_task_staff,
        org_role,
        is_staff,
        allow,
        quality_settings,
    ):
        for user in users:
            task = next(
                (
                    t
                    for t in tasks
                    if t["organization"] is not None
                    and is_task_staff(user["id"], t["id"]) == is_staff
                    and is_org_member(user["id"], t["organization"], role=org_role)
                ),
                None,
            )
            if task is not None:
                break

        assert task

        org_id = task["organization"]
        extra_kwargs = {"org_id": org_id}

        settings_id = task["quality_settings"]
        settings = quality_settings[settings_id]

        if allow:
            self._test_get_settings_200(
                user["username"], settings_id, expected_data=settings, **extra_kwargs
            )
        else:
            self._test_get_settings_403(user["username"], settings_id, **extra_kwargs)


@pytest.mark.usefixtures("restore_db_per_function")
class TestPatchSettings(_PermissionTestBase):
    def _test_patch_settings_200(
        self,
        user: str,
        obj_id: int,
        data: dict[str, Any],
        *,
        expected_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        with make_api_client(user) as api_client:
            (_, response) = api_client.quality_api.partial_update_settings(
                obj_id, patched_quality_settings_request=data, **kwargs
            )
            assert response.status == HTTPStatus.OK

        if expected_data is not None:
            assert DeepDiff(expected_data, json.loads(response.data), ignore_order=True) == {}

        return response

    def _test_patch_settings_403(self, user: str, obj_id: int, data: dict[str, Any], **kwargs):
        with make_api_client(user) as api_client:
            (_, response) = api_client.quality_api.partial_update_settings(
                obj_id,
                patched_quality_settings_request=data,
                **kwargs,
                _parse_response=False,
                _check_status=False,
            )
            assert response.status == HTTPStatus.FORBIDDEN

        return response

    def _get_request_data(self, data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        patched_data = deepcopy(data)

        for field, value in data.items():
            if isinstance(value, bool):
                patched_data[field] = not value
            elif isinstance(value, float):
                patched_data[field] = 1 - value

        expected_data = deepcopy(patched_data)

        return patched_data, expected_data

    def test_can_patch_settings(self, admin_user, quality_settings):
        settings_id, settings = next(iter(quality_settings.items()))
        data, expected_data = self._get_request_data(settings)
        self._test_patch_settings_200(admin_user, settings_id, data, expected_data=expected_data)

    @pytest.mark.parametrize("is_staff, allow", [(True, True), (False, False)])
    def test_user_patch_settings_in_sandbox_task(
        self, quality_settings, tasks, users, is_task_staff, is_staff, allow
    ):
        task = next(
            t
            for t in tasks
            if t["organization"] is None and not users[t["owner"]["id"]]["is_superuser"]
        )

        if is_staff:
            user = task["owner"]["username"]
        else:
            user = next(u for u in users if not is_task_staff(u["id"], task["id"]))["username"]

        settings_id = task["quality_settings"]
        settings = quality_settings[settings_id]
        data, expected_data = self._get_request_data(settings)

        if allow:
            self._test_patch_settings_200(user, settings_id, data, expected_data=expected_data)
        else:
            self._test_patch_settings_403(user, settings_id, data)

    @pytest.mark.parametrize(
        "org_role, is_staff, allow",
        [
            ("owner", True, True),
            ("owner", False, True),
            ("maintainer", True, True),
            ("maintainer", False, True),
            ("supervisor", True, True),
            ("supervisor", False, False),
            ("worker", True, True),
            ("worker", False, False),
        ],
    )
    def test_user_patch_settings_in_org_task(
        self,
        tasks,
        users,
        is_org_member,
        is_task_staff,
        org_role,
        is_staff,
        allow,
        quality_settings,
    ):
        for user in users:
            task = next(
                (
                    t
                    for t in tasks
                    if t["organization"] is not None
                    and is_task_staff(user["id"], t["id"]) == is_staff
                    and is_org_member(user["id"], t["organization"], role=org_role)
                ),
                None,
            )
            if task is not None:
                break

        assert task

        org_id = task["organization"]
        extra_kwargs = {"org_id": org_id}

        settings_id = task["quality_settings"]
        settings = quality_settings[settings_id]
        data, expected_data = self._get_request_data(settings)

        if allow:
            self._test_patch_settings_200(
                user["username"], settings_id, data, expected_data=expected_data, **extra_kwargs
            )
        else:
            self._test_patch_settings_403(user["username"], settings_id, data, **extra_kwargs)
