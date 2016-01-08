# Copyright 2016 Tesora Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from openstack_dashboard.test.test_data import exceptions
from openstack_dashboard.test.test_data import utils

from troveclient import exceptions as trove_exceptions


def data(TEST):
    if not TEST.exceptions:
        TEST.exceptions = utils.TestDataContainer()

    trove_exception = trove_exceptions.ClientException
    TEST.exceptions.trove = (exceptions.
                             create_stubbed_exception(trove_exception))

    trove_auth = trove_exceptions.Unauthorized
    TEST.exceptions.trove_unauthorized = (exceptions.
                                          create_stubbed_exception(trove_auth))
