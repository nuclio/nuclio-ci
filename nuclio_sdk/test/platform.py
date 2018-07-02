# Copyright 2017 The Nuclio Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import logging
import unittest.mock
import json

import nuclio_sdk
import nuclio_sdk.platform

# different HTTP client libraries for Python 2/3
if sys.version_info[:2] < (3, 0):
    from httplib import HTTPConnection
else:
    from http.client import HTTPConnection


class Platform(object):

    def __init__(self):
        self._logger = nuclio_sdk.Logger(logging.DEBUG)
        self._logger.set_handler('default', sys.stdout, nuclio_sdk.logger.HumanReadableFormatter())

        self._handler_contexts = {}
        self._call_function_mock = unittest.mock.MagicMock()
        self._kind = 'test'
        self.namespace = 'default'

        self._connection_provider = HTTPConnection
        self.caller_platform = nuclio_sdk.Context(self._logger)
        # for tests that need a context
        self._context = nuclio_sdk.Context(self._logger, self)

    def call_handler(self, handler, event):
        return handler(self._get_handler_context(handler), event)

    def call_function(self, function_indicator, event, node=None, wait_for_response=True):
        # return self._call_function_mock(name, event)


        # get connection from provider

        connection = self._connection_provider(self._get_function_url(function_indicator))

        # if the user passes a dict as a body, assume json serialization. otherwise take content type from
        # body or use plain text
        if isinstance(event.body, dict):
            body = json.dumps(event.body)
            content_type = 'application/json'
        else:
            body = event.body
            content_type = event.content_type or 'text/plain'

        connection.request(event.method,
                           event.path,
                           body=body,
                           headers={'Content-Type': content_type})

        if wait_for_response:
            # get response from connection
            connection_response = connection.getresponse()

            # header dict
            response_headers = {}

            # get response headers as lowercase
            for (name, value) in connection_response.getheaders():
                response_headers[name.lower()] = value

            # if content type exists, use it
            response_content_type = response_headers.get('content-type', 'text/plain')

            # read the body
            response_body = connection_response.read()

            # if content type is json, go ahead and do parsing here. if it explodes, don't blow up
            if response_content_type == 'application/json':
                response_body = json.loads(response_body)

            response = nuclio_sdk.Response(headers=response_headers,
                                           body=response_body,
                                           content_type=response_content_type,
                                           status_code=connection_response.status)

            return response

        return

    def get_call_function_call_args(self, index):
        return self._call_function_mock.call_args_list[index][0]

    def _get_function_url(self, function_indeicator):

        # local envs prefix namespace
        if self.kind == 'local':
            return '{0}-{1}:8080'.format(self.namespace, function_indeicator)
        elif self.kind == 'test':
            return '0.0.0.0:{}'.format(function_indeicator)
        else:
            return '{0}:8080'.format(function_indeicator)


    @property
    def context(self):
        return self._context

    @property
    def kind(self):
        return self._kind

    @property
    def call_function_mock(self):
        return self._call_function_mock

    def _get_handler_context(self, handler):
        try:
            return self._handler_contexts[handler]
        except KeyError:

            # first time we're calling this handler
            context = nuclio_sdk.Context(self._logger, self)

            # get handler module
            handler_module = sys.modules[handler.__module__]

            self._logger.info_with('Calling handler init context', handler=str(handler))

            # call init context
            if hasattr(handler_module, 'init_context'):
                getattr(handler_module, 'init_context')(context)

            # save context and return it
            self._handler_contexts[handler] = context

            return context
