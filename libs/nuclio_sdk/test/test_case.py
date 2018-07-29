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

import unittest
import os
import copy

import libs.common.psycopg2_functions
import libs.nuclio_sdk.test


class TestCase(unittest.TestCase):

    def setUp(self):

        self._platform = libs.nuclio_sdk.test.Platform()
        self._environ_copy = copy.copy(os.environ)

        os.environ['PGINFO'] = 'postgres:pass@172.17.0.1:5432'
        setattr(self._platform.context.user_data, 'conn', libs.common.psycopg2_functions.get_psycopg2_connection())

    def tearDown(self):
        os.environ = self._environ_copy
