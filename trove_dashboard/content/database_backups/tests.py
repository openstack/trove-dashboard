# Copyright 2013 Mirantis Inc.
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
from django.utils.translation import ugettext_lazy as _
import mock
import six

from openstack_auth import policy
from openstack_dashboard import api as dash_api

from troveclient import common

from trove_dashboard import api
from trove_dashboard.content.databases.workflows import create_instance
from trove_dashboard.test import helpers as test
from trove_dashboard.utils import common as common_utils

INDEX_URL = reverse('horizon:project:database_backups:index')
BACKUP_URL = reverse('horizon:project:database_backups:create')
DETAILS_URL = reverse('horizon:project:database_backups:detail', args=['id'])
RESTORE_URL = reverse('horizon:project:databases:launch')


class DatabasesBackupsTests(test.TestCase):
    @test.create_mocks({api.trove: ('backup_list', 'instance_get')})
    def test_index(self):
        self.mock_backup_list.return_value = self.database_backups.list()
        self.mock_instance_get.return_value = self.databases.first()

        res = self.client.get(INDEX_URL)

        self.mock_backup_list.assert_called_once_with(test.IsHttpRequest())
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_instance_get, 3,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.assertTemplateUsed(res, 'project/database_backups/index.html')

    @test.create_mocks({api.trove: ('backup_list',)})
    def test_index_exception(self):
        self.mock_backup_list.side_effect = self.exceptions.trove

        res = self.client.get(INDEX_URL)

        self.mock_backup_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(
            res, 'project/database_backups/index.html')
        self.assertEqual(res.status_code, 200)
        self.assertMessageCount(res, error=1)

    @test.create_mocks({
        api.trove: ('instance_list', 'backup_list', 'backup_create'),
        policy: ('check',),
    })
    def test_launch_backup(self):
        self.mock_check.return_value = True
        self.mock_instance_list.return_value = self.databases.list()
        self.mock_backup_list.return_value = self.database_backups.list()

        database = self.databases.first()
        backupName = "NewBackup"
        backupDesc = "Backup Description"

        post = {
            'name': backupName,
            'instance': database.id,
            'description': backupDesc,
            'parent': ""
        }
        res = self.client.post(BACKUP_URL, post)

        self.mock_check.assert_called_once_with((), test.IsHttpRequest())
        self.mock_instance_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_backup_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_backup_create.assert_called_once_with(
            test.IsHttpRequest(),
            backupName,
            database.id,
            backupDesc,
            "")
        self.assertNoFormErrors(res)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({
        api.trove: ('instance_list', 'backup_list'),
        policy: ('check',),
    })
    def test_launch_backup_exception(self):
        self.mock_check.return_value = True
        self.mock_instance_list.side_effect = self.exceptions.trove
        self.mock_backup_list.return_value = self.database_backups.list()

        res = self.client.get(BACKUP_URL)
        self.mock_check.assert_called_once_with((), test.IsHttpRequest())
        self.mock_instance_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_backup_list.assert_called_once_with(test.IsHttpRequest())
        self.assertMessageCount(res, error=1)
        self.assertTemplateUsed(res,
                                'project/database_backups/backup.html')

    @test.create_mocks({
        api.trove: ('instance_list', 'backup_list', 'backup_create'),
        policy: ('check',),
    })
    def test_launch_backup_incr(self):
        self.mock_check.return_value = True
        self.mock_instance_list.return_value = self.databases.list()
        self.mock_backup_list.return_value = self.database_backups.list()

        database = self.databases.first()
        backupName = "NewBackup"
        backupDesc = "Backup Description"
        backupParent = self.database_backups.first()

        post = {
            'name': backupName,
            'instance': database.id,
            'description': backupDesc,
            'parent': backupParent.id,
        }
        res = self.client.post(BACKUP_URL, post)

        self.mock_check.assert_called_once_with((), test.IsHttpRequest())
        self.mock_instance_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_backup_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_backup_create.assert_called_once_with(
            test.IsHttpRequest(),
            backupName,
            database.id,
            backupDesc,
            backupParent.id)
        self.assertNoFormErrors(res)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({api.trove: ('backup_get', 'instance_get')})
    def test_detail_backup(self):
        self.mock_backup_get.return_value = self.database_backups.first()
        self.mock_instance_get.return_value = self.databases.first()
        res = self.client.get(DETAILS_URL)

        self.mock_backup_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(six.text_type))
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.assertTemplateUsed(res,
                                'project/database_backups/details.html')

    @test.create_mocks({api.trove: ('backup_get',)})
    def test_detail_backup_notfound(self):
        self.mock_backup_get.side_effect = self.exceptions.trove
        res = self.client.get(DETAILS_URL)

        self.mock_backup_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(six.text_type))
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({api.trove: ('backup_get', 'instance_get')})
    def test_detail_backup_incr(self):
        incr_backup = self.database_backups.list()[2]
        parent_backup = self.database_backups.list()[1]

        self.mock_backup_get.side_effect = [incr_backup, parent_backup]
        self.mock_instance_get.return_value = self.databases.list()[1]

        url = reverse('horizon:project:database_backups:detail',
                      args=[incr_backup.id])
        res = self.client.get(url)
        self.assertEqual(
            [mock.call(test.IsHttpRequest(), test.IsA(six.text_type)),
             mock.call(test.IsHttpRequest(), incr_backup.parent_id)],
            self.mock_backup_get.call_args_list)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.assertTemplateUsed(res, 'project/database_backups/details.html')

    @test.create_mocks({
        api.trove: ('backup_get', 'backup_list', 'configuration_list',
                    'datastore_flavors', 'datastore_list',
                    'datastore_version_list', 'instance_list'),
        dash_api.cinder: ('volume_type_list',),
        dash_api.neutron: ('network_list',),
        dash_api.nova: ('availability_zone_list',),
        policy: ('check',),
    })
    def test_restore_backup(self):
        backup = self.database_backups.first()
        self.mock_check.return_value = True
        self.mock_backup_get.return_value = self.database_backups.first()
        self.mock_backup_list.return_value = self.database_backups.list()
        self.mock_configuration_list.return_value = (
            self.database_configurations.list())
        self.mock_datastore_flavors.return_value = self.flavors.list()
        self.mock_datastore_list.return_value = self.datastores.list()
        self.mock_datastore_version_list.return_value = (
            self.datastore_versions.list())
        self.mock_instance_list.return_value = (
            common.Paginated(self.databases.list()))
        self.mock_volume_type_list.return_vlue = []
        self.mock_network_list.return_value = self.networks.list()[:1]
        self.mock_availability_zone_list.return_value = (
            self.availability_zones.list())

        url = RESTORE_URL + '?backup=%s' % self.database_backups.first().id
        res = self.client.get(url)
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_check, 4, mock.call((), test.IsHttpRequest()))
        self.mock_backup_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(six.text_type))
        self.mock_backup_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_configuration_list.assert_called_once_with(
            test.IsHttpRequest())
        self.mock_datastore_flavors.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(six.string_types),
            test.IsA(six.string_types))
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_datastore_version_list.assert_called_once_with(
            test.IsHttpRequest(), backup.datastore['type'])
        self.mock_instance_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_volume_type_list.assert_called_once_with(
            test.IsHttpRequest())
        self.mock_network_list.assert_any_call(
            test.IsHttpRequest(), tenant_id=self.tenant.id, shared=False)
        self.mock_availability_zone_list.assert_called_once_with(
            test.IsHttpRequest())
        self.assertTemplateUsed(res, 'project/databases/launch.html')

        set_instance_detail_step = \
            [step for step in res.context_data['workflow'].steps
             if isinstance(step, create_instance.SetInstanceDetails)][0]
        fields = set_instance_detail_step.action.fields
        self.assertTrue(len(fields['datastore'].choices), 1)
        text = 'mysql - 5.6'
        choice = fields['datastore'].choices[0]
        self.assertTrue(choice[0], common_utils.hexlify(text))
        self.assertTrue(choice[1], text)

        advanced_step = [step for step in res.context_data['workflow'].steps
                         if isinstance(step, create_instance.Advanced)][0]
        fields = advanced_step.action.fields
        self.assertTrue(len(fields['initial_state'].choices), 1)
        choice = fields['initial_state'].choices[0]
        self.assertTrue(choice[0], 'backup')
        self.assertTrue(choice[1], _('Restore from Backup'))
