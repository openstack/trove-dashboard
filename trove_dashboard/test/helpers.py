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

from openstack_dashboard.test import helpers

from trove_dashboard.test.test_data import utils


# Shortcuts to avoid importing openstack_dashboard.test.helpers.
# TODO(zhaochao): as Akihiro Motoki pointed out the helper functions
# inside openstack_dashboard.test is not intended to be used by the
# horizon plugins, we should migrate to horizon.test.helpers instead.
# However some helper functions like 'create_mocks' below are still
# not migrated to horizon.test.helpers yet, we'll come back for this
# when everything is ready.
create_mocks = helpers.create_mocks
IsA = helpers.IsA
IsHttpRequest = helpers.IsHttpRequest


def create_stubs(stubs_to_create={}):
    return helpers.create_stubs(stubs_to_create)


class TroveTestsMixin(object):
    def _setup_test_data(self):
        super(TroveTestsMixin, self)._setup_test_data()
        utils.load_test_data(self)


class TestCase(TroveTestsMixin, helpers.TestCase):
    pass


class BaseAdminViewTests(TroveTestsMixin, helpers.TestCase):
    pass
