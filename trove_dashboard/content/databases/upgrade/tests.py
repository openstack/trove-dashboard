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

from django.urls import reverse
from unittest.mock import ANY
from unittest.mock import patch

from trove_dashboard import api
from trove_dashboard.test import helpers as test


INDEX_URL = reverse('horizon:project:databases:index')


class UpgradeTests(test.TestCase):

    @patch.object(api.trove, "instance_get")
    @patch.object(api.trove, "datastore_version_list")
    def test_upgrade_instance_get(self, mock_versions, mock_instance_get):
        database = self.databases.first()

        mock_instance_get.return_value = database
        mock_versions.return_value = self.datastore_versions.list()

        url = reverse(
            'horizon:project:databases:upgrade:upgrade_instance',
            args=[database.id]
        )

        res = self.client.get(url)

        self.assertTemplateUsed(
            res,
            'project/databases/upgrade/upgrade_instance.html'
        )

        mock_instance_get.assert_called_once_with(ANY, database.id)
        mock_versions.assert_called_once_with(ANY, database.datastore['type'])

    @patch.object(api.trove, "instance_get")
    @patch.object(api.trove, "datastore_version_list")
    @patch.object(api.trove, "instance_upgrade")
    def test_upgrade_instance(
        self,
        mock_upgrade,
        mock_versions,
        mock_instance_get
    ):

        database = self.databases.first()
        datastore_version = self.datastore_versions.first()

        mock_instance_get.return_value = database
        mock_versions.return_value = self.datastore_versions.list()
        mock_upgrade.return_value = None

        url = reverse(
            'horizon:project:databases:upgrade:upgrade_instance',
            args=[database.id]
        )

        post = {
            'instance_id': database.id,
            'instance_name': database.name,
            'new_datastore_version': datastore_version.id
        }

        res = self.client.post(url, post)

        self.assertNoFormErrors(res)
        self.assertRedirectsNoFollow(res, INDEX_URL)

        mock_instance_get.assert_called_once_with(ANY, database.id)
        mock_versions.assert_called_once_with(ANY, database.datastore['type'])
        mock_upgrade.assert_called_once_with(
            ANY,
            database.id,
            datastore_version.id
        )
