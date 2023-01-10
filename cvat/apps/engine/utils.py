# Copyright (C) 2020-2022 Intel Corporation
#
# SPDX-License-Identifier: MIT

import ast
# from typing import Optional, Type
import cv2 as cv
from collections import namedtuple
import hashlib
import importlib
import sys
import traceback
import subprocess
import os
import urllib.parse

from av import VideoFrame
from PIL import Image

from django.core.exceptions import ValidationError
from django.urls import reverse as _django_reverse
from django.utils.http import urlencode
# from django.db.models.query import QuerySet
# from rest_framework.response import Response
# from rest_framework.viewsets import GenericViewSet

Import = namedtuple("Import", ["module", "name", "alias"])

def parse_imports(source_code: str):
    root = ast.parse(source_code)

    for node in ast.iter_child_nodes(root):
        if isinstance(node, ast.Import):
            module = []
        elif isinstance(node, ast.ImportFrom):
            module = node.module
        else:
            continue

        for n in node.names:
            yield Import(module, n.name, n.asname)

def import_modules(source_code: str):
    results = {}
    imports = parse_imports(source_code)
    for import_ in imports:
        module = import_.module if import_.module else import_.name
        loaded_module = importlib.import_module(module)

        if not import_.name == module:
            loaded_module = getattr(loaded_module, import_.name)

        if import_.alias:
            results[import_.alias] = loaded_module
        else:
            results[import_.name] = loaded_module

    return results

class InterpreterError(Exception):
    pass

def execute_python_code(source_code, global_vars=None, local_vars=None):
    try:
        # pylint: disable=exec-used
        exec(source_code, global_vars, local_vars)
    except SyntaxError as err:
        error_class = err.__class__.__name__
        details = err.args[0]
        line_number = err.lineno
        raise InterpreterError("{} at line {}: {}".format(error_class, line_number, details))
    except AssertionError as err:
        # AssertionError doesn't contain any args and line number
        error_class = err.__class__.__name__
        raise InterpreterError("{}".format(error_class))
    except Exception as err:
        error_class = err.__class__.__name__
        details = err.args[0]
        _, _, tb = sys.exc_info()
        line_number = traceback.extract_tb(tb)[-1][1]
        raise InterpreterError("{} at line {}: {}".format(error_class, line_number, details))

def av_scan_paths(*paths):
    if 'yes' == os.environ.get('CLAM_AV'):
        command = ['clamscan', '--no-summary', '-i', '-o']
        command.extend(paths)
        res = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) # nosec
        if res.returncode:
            raise ValidationError(res.stdout)

def rotate_image(image, angle):
    height, width = image.shape[:2]
    image_center = (width/2, height/2)
    matrix = cv.getRotationMatrix2D(image_center, angle, 1.)
    abs_cos = abs(matrix[0,0])
    abs_sin = abs(matrix[0,1])
    bound_w = int(height * abs_sin + width * abs_cos)
    bound_h = int(height * abs_cos + width * abs_sin)
    matrix[0, 2] += bound_w/2 - image_center[0]
    matrix[1, 2] += bound_h/2 - image_center[1]
    matrix = cv.warpAffine(image, matrix, (bound_w, bound_h))
    return matrix

def md5_hash(frame):
    if isinstance(frame, VideoFrame):
        frame = frame.to_image()
    elif isinstance(frame, str):
        frame = Image.open(frame, 'r')
    return hashlib.md5(frame.tobytes()).hexdigest() # nosec

def parse_specific_attributes(specific_attributes):
    assert isinstance(specific_attributes, str), 'Specific attributes must be a string'
    parsed_specific_attributes = urllib.parse.parse_qsl(specific_attributes)
    return {
        key: value for (key, value) in parsed_specific_attributes
    } if parsed_specific_attributes else dict()


def parse_exception_message(msg):
    parsed_msg = msg
    try:
        if 'ErrorDetail' in msg:
            # msg like: 'rest_framework.exceptions.ValidationError:
            # [ErrorDetail(string="...", code=\'invalid\')]\n'
            parsed_msg = msg.split('string=')[1].split(', code=')[0].strip("\"")
        elif msg.startswith('rest_framework.exceptions.'):
            parsed_msg = msg.split(':')[1].strip()
    except Exception: # nosec
        pass
    return parsed_msg

def process_failed_job(rq_job):
    if rq_job.meta['tmp_file_descriptor']:
        os.close(rq_job.meta['tmp_file_descriptor'])
    if os.path.exists(rq_job.meta['tmp_file']):
        os.remove(rq_job.meta['tmp_file'])
    exc_info = str(rq_job.exc_info or rq_job.dependency.exc_info)
    if rq_job.dependency:
        rq_job.dependency.delete()
    rq_job.delete()

    return parse_exception_message(exc_info)

def configure_dependent_job(queue, rq_id, rq_func, db_storage, filename, key):
    rq_job_id_download_file = rq_id + f'?action=download_{filename}'
    rq_job_download_file = queue.fetch_job(rq_job_id_download_file)
    if not rq_job_download_file:
        # note: boto3 resource isn't pickleable, so we can't use storage
        rq_job_download_file = queue.enqueue_call(
            func=rq_func,
            args=(db_storage, filename, key),
            job_id=rq_job_id_download_file
        )
    return rq_job_download_file

# def make_paginated_response(queryset: QuerySet, *,
#     viewset: GenericViewSet,
#     response_type: Type[Response] = Response,
#     request: Optional[Request] = None,
#     **serializer_params
# ) -> Response:
#     # Adapted from the mixins.ListModelMixin.list()

#     serializer_params.setdefault('many', True)

#     if request is not None:
#         context = serializer_params.setdefault('context', {})
#         context.setdefault('request', request)

#     make_serializer = viewset.get_serializer

#     page = viewset.paginate_queryset(queryset)
#     if page is not None:
#         serializer = make_serializer(page, **serializer_params)
#         return viewset.get_paginated_response(serializer.data)

#     serializer = make_serializer(queryset, **serializer_params)

#     return response_type(serializer.data)

def reverse(viewname, *, args=None, kwargs=None, query_params=None) -> str:
    """
    The same as reverse(), but adds query params support.
    """

    url = _django_reverse(viewname, args=args, kwargs=kwargs)

    if query_params:
        return f'{url}?{urlencode(query_params)}'

    return url
