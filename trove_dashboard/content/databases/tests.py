# Copyright 2013 Mirantis Inc.
# Copyright 2013 Rackspace Hosting.
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

import logging
import unittest
from unittest import mock

import django
from django import http
from django.urls import reverse
from horizon import exceptions
from openstack_auth import policy
from openstack_dashboard import api as dash_api
from troveclient import common

from trove_dashboard import api
from trove_dashboard.content.databases import forms
from trove_dashboard.content.databases import tables
from trove_dashboard.content.databases import views
from trove_dashboard.content.databases.workflows import create_instance
from trove_dashboard.test import helpers as test
from trove_dashboard.utils import common as common_utils

INDEX_URL = reverse('horizon:project:databases:index')
LAUNCH_URL = reverse('horizon:project:databases:launch')
DETAILS_URL = reverse('horizon:project:databases:detail', args=['id'])


class DatabaseTests(test.TestCase):
    @test.create_mocks(
        {api.trove: ('instance_get', 'instance_list', 'flavor_list')})
    def test_index(self):
        # Mock database instances
        databases = common.Paginated(self.databases.list())
        self.mock_instance_list.return_value = databases
        # Mock flavors
        self.mock_flavor_list.return_value = self.flavors.list()

        res = self.client.get(INDEX_URL)
        self.mock_instance_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        replica_id = databases[-1].replicas[0]['id']
        self.mock_instance_get.assert_called_once_with(test.IsHttpRequest(),
                                                       replica_id)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, 'project/databases/index.html')
        # Check the Host column displaying ip or hostname
        self.assertContains(res, '10.0.0.3')
        self.assertContains(res, 'trove.instance-2.com')

    @test.create_mocks(
        {api.trove: ('instance_get', 'instance_list', 'flavor_list')})
    def test_index_flavor_exception(self):
        # Mock database instances
        databases = common.Paginated(self.databases.list())
        self.mock_instance_list.return_value = databases
        # Mock flavors
        self.mock_flavor_list.side_effect = self.exceptions.trove

        res = self.client.get(INDEX_URL)
        self.mock_instance_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        replica_id = databases[-1].replicas[0]['id']
        self.mock_instance_get.assert_called_once_with(test.IsHttpRequest(),
                                                       replica_id)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, 'project/databases/index.html')
        self.assertMessageCount(res, error=1)

    @test.create_mocks(
        {api.trove: ('instance_get', 'instance_list',)})
    def test_index_list_exception(self):
        # Mock database instances
        self.mock_instance_list.side_effect = self.exceptions.trove

        res = self.client.get(INDEX_URL)
        self.mock_instance_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        self.assertTemplateUsed(res, 'project/databases/index.html')
        self.assertMessageCount(res, error=1)

    @test.create_mocks(
        {api.trove: ('instance_get', 'instance_list', 'flavor_list')})
    def test_index_pagination(self):
        # Mock database instances
        databases = self.databases.list()
        last_record = databases[-1]
        databases = common.Paginated(databases, next_marker="foo")
        self.mock_instance_list.return_value = databases
        # Mock flavors
        self.mock_flavor_list.return_value = self.flavors.list()

        res = self.client.get(INDEX_URL)
        self.mock_instance_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        replica_id = databases[-1].replicas[0]['id']
        self.mock_instance_get.assert_called_once_with(test.IsHttpRequest(),
                                                       replica_id)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, 'project/databases/index.html')
        self.assertContains(
            res, 'marker=' + last_record.id)

    @test.create_mocks(
        {api.trove: ('instance_get', 'instance_list', 'flavor_list')})
    def test_index_flavor_list_exception(self):
        # Mocking instances.
        databases = common.Paginated(self.databases.list())
        self.mock_instance_list.return_value = databases
        # Mocking flavor list with raising an exception.
        self.mock_flavor_list.side_effect = self.exceptions.trove

        res = self.client.get(INDEX_URL)
        self.mock_instance_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        replica_id = databases[-1].replicas[0]['id']
        self.mock_instance_get.assert_called_once_with(test.IsHttpRequest(),
                                                       replica_id)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, 'project/databases/index.html')
        self.assertMessageCount(res, error=1)

    @test.create_mocks({
        api.trove: ('backup_list', 'configuration_list', 'datastore_flavors',
                    'datastore_list', 'datastore_version_list', 'flavor_list',
                    'instance_list'),
        dash_api.cinder: ('volume_type_list',),
        dash_api.neutron: ('network_list',),
        dash_api.nova: ('availability_zone_list',),
        policy: ('check',),
    })
    def test_launch_instance(self):
        self.mock_check.return_value = True
        self.mock_datastore_flavors.return_value = self.flavors.list()
        self.mock_backup_list.return_value = self.database_backups.list()
        self.mock_configuration_list.return_value = []
        self.mock_instance_list.return_value = self.databases.list()
        # Mock datastores
        self.mock_datastore_list.return_value = self.datastores.list()
        # Mock datastore versions
        self.mock_datastore_version_list.return_value = (
            self.datastore_versions.list())

        self.mock_volume_type_list.return_value = []

        self.mock_network_list.side_effect = [self.networks.list()[:1],
                                              self.networks.list()[1:]]

        self.mock_availability_zone_list.return_value = (
            self.availability_zones.list())

        res = self.client.get(LAUNCH_URL)
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_check, 5, mock.call((), test.IsHttpRequest()))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_datastore_flavors, 20,
            mock.call(test.IsHttpRequest(),
                      test.IsA(str),
                      test.IsA(str)))
        self.mock_backup_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_configuration_list.assert_called_once_with(
            test.IsHttpRequest())
        self.mock_instance_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_datastore_version_list, 4,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.mock_volume_type_list.assert_called_once_with(
            test.IsHttpRequest())
        self.mock_network_list.assert_has_calls([
            mock.call(test.IsHttpRequest(),
                      tenant_id=self.tenant.id,
                      shared=False),
            mock.call(test.IsHttpRequest(), shared=True)])
        self.mock_availability_zone_list.assert_called_once_with(
            test.IsHttpRequest())
        self.assertTemplateUsed(res, 'project/databases/launch.html')

    # django 1.7 and later does not handle the thrown Http302
    # exception well enough.
    # TODO(mrunge): re-check when django-1.8 is stable
    @unittest.skipIf(django.VERSION >= (1, 7, 0),
                     'Currently skipped with Django >= 1.7')
    @test.create_mocks({api.trove: ('flavor_list',)})
    def test_launch_instance_exception_on_flavors(self):
        trove_exception = self.exceptions.nova
        self.mock_flavor_list.side_effect = trove_exception

        toSuppress = ["trove_dashboard.content.databases."
                      "workflows.create_instance",
                      "horizon.workflows.base"]

        # Suppress expected log messages in the test output
        loggers = []
        for cls in toSuppress:
            logger = logging.getLogger(cls)
            loggers.append((logger, logger.getEffectiveLevel()))
            logger.setLevel(logging.CRITICAL)

        try:
            with self.assertRaises(exceptions.Http302):
                self.client.get(LAUNCH_URL)
                self.mock_datastore_flavors.assert_called_once_with(
                    test.IsHttpRequest(), mock.ANY, mock.ANY)

        finally:
            # Restore the previous log levels
            for (log, level) in loggers:
                log.setLevel(level)

    @test.create_mocks({
        api.trove: ('backup_list', 'configuration_list', 'datastore_flavors',
                    'datastore_list', 'datastore_version_list', 'flavor_list',
                    'instance_create', 'instance_list'),
        dash_api.cinder: ('volume_type_list',),
        dash_api.neutron: ('network_list',),
        dash_api.nova: ('availability_zone_list',),
        policy: ('check',),
    })
    def test_create_simple_instance(self):
        self.mock_check.return_value = True
        self.mock_datastore_flavors.return_value = self.flavors.list()
        self.mock_backup_list.return_value = self.database_backups.list()
        self.mock_instance_list.return_value = self.databases.list()
        # Mock datastores
        self.mock_datastore_list.return_value = self.datastores.list()
        # Mock datastore versions
        self.mock_datastore_version_list.return_value = (
            self.datastore_versions.list())

        self.mock_volume_type_list.return_value = []

        self.mock_network_list.side_effect = [self.networks.list()[:1],
                                              self.networks.list()[1:]]

        nics = [{"net-id": self.networks.first().id}]

        datastore = 'mysql'
        datastore_version = '5.5'
        field_name = self._build_flavor_widget_name(datastore,
                                                    datastore_version)
        self.mock_availability_zone_list.return_value = (
            self.availability_zones.list())

        # Mock create database call
        self.mock_instance_create.return_value = self.databases.first()

        post = {
            'name': "MyDB",
            'volume': '1',
            'flavor': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'datastore': field_name,
            field_name: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'network': self.networks.first().id,
            'volume_type': 'no_type'
        }

        res = self.client.post(LAUNCH_URL, post)
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_check, 5, mock.call((), test.IsHttpRequest()))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_datastore_flavors, 20,
            mock.call(test.IsHttpRequest(),
                      test.IsA(str),
                      test.IsA(str)))
        self.mock_backup_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_instance_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_datastore_version_list, 4,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.mock_volume_type_list.assert_called_once_with(
            test.IsHttpRequest())
        self.mock_network_list.assert_has_calls([
            mock.call(test.IsHttpRequest(),
                      tenant_id=self.tenant.id,
                      shared=False),
            mock.call(test.IsHttpRequest(), shared=True)])
        self.mock_availability_zone_list.assert_called_once_with(
            test.IsHttpRequest())
        self.mock_instance_create.assert_called_once_with(
            test.IsHttpRequest(),
            test.IsA(str),
            test.IsA(int),
            test.IsA(str),
            databases=None,
            datastore=datastore,
            datastore_version=datastore_version,
            restore_point=None,
            replica_of=None,
            configuration=None,
            users=None,
            nics=nics,
            replica_count=None,
            volume_type=None,
            locality=None,
            availability_zone=test.IsA(str),
            access=None)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({
        api.trove: ('backup_list', 'configuration_list', 'datastore_flavors',
                    'datastore_list', 'datastore_version_list', 'flavor_list',
                    'instance_create', 'instance_list'),
        dash_api.cinder: ('volume_type_list',),
        dash_api.neutron: ('network_list',),
        dash_api.nova: ('availability_zone_list',),
        policy: ('check',),
    })
    def test_create_simple_instance_exception(self):
        self.mock_check.return_value = True
        trove_exception = self.exceptions.nova
        self.mock_datastore_flavors.return_value = self.flavors.list()
        self.mock_backup_list.return_value = self.database_backups.list()
        self.mock_instance_list.return_value = self.databases.list()
        # Mock datastores
        self.mock_datastore_list.return_value = self.datastores.list()
        # Mock datastore versions
        self.mock_datastore_version_list.return_value = (
            self.datastore_versions.list())

        self.mock_volume_type_list.return_value = []

        self.mock_network_list.side_effect = [self.networks.list()[:1],
                                              self.networks.list()[1:]]

        nics = [{"net-id": self.networks.first().id}]

        datastore = 'mysql'
        datastore_version = '5.5'
        field_name = self._build_flavor_widget_name(datastore,
                                                    datastore_version)
        self.mock_availability_zone_list.return_value = (
            self.availability_zones.list())

        # Mock create database call
        self.mock_instance_create.side_effect = trove_exception

        post = {
            'name': "MyDB",
            'volume': '1',
            'flavor': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'datastore': field_name,
            field_name: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'network': self.networks.first().id,
            'volume_type': 'no_type'
        }

        res = self.client.post(LAUNCH_URL, post)
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_check, 5, mock.call((), test.IsHttpRequest()))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_datastore_flavors, 20,
            mock.call(test.IsHttpRequest(),
                      test.IsA(str),
                      test.IsA(str)))
        self.mock_backup_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_instance_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_datastore_version_list, 4,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.mock_volume_type_list.assert_called_once_with(
            test.IsHttpRequest())
        self.mock_network_list.assert_has_calls([
            mock.call(test.IsHttpRequest(),
                      tenant_id=self.tenant.id,
                      shared=False),
            mock.call(test.IsHttpRequest(), shared=True)])
        self.mock_availability_zone_list.assert_called_once_with(
            test.IsHttpRequest())
        self.mock_instance_create.assert_called_once_with(
            test.IsHttpRequest(),
            test.IsA(str),
            test.IsA(int),
            test.IsA(str),
            databases=None,
            datastore=datastore,
            datastore_version=datastore_version,
            restore_point=None,
            replica_of=None,
            configuration=None,
            users=None,
            nics=nics,
            replica_count=None,
            volume_type=None,
            locality=None,
            availability_zone=test.IsA(str),
            access=None)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({
        api.trove: ('instance_get', 'flavor_get', 'root_show')
    })
    def _test_details(self, database, test_text, assert_contains=True):
        self.mock_instance_get.return_value = database
        self.mock_flavor_get.return_value = self.flavors.first()
        self.mock_root_show.return_value = self.database_user_roots.first()

        # Suppress expected log messages in the test output
        loggers = []
        toSuppress = ["trove_dashboard.content.databases.tabs",
                      "horizon.tables"]
        for cls in toSuppress:
            logger = logging.getLogger(cls)
            loggers.append((logger, logger.getEffectiveLevel()))
            logger.setLevel(logging.CRITICAL)
        try:
            res = self.client.get(DETAILS_URL)
            self.mock_instance_get.assert_called_once_with(
                test.IsHttpRequest(), test.IsA(str))
            self.mock_flavor_get.assert_called_once_with(
                test.IsHttpRequest(), test.IsA(str))
            self.mock_root_show.assert_called_once_with(
                test.IsHttpRequest(), test.IsA(str))
            self.assertTemplateUsed(res, 'project/databases/'
                                         '_detail_overview.html')
            if assert_contains:
                self.assertContains(res, test_text)
            else:
                self.assertNotContains(res, test_text)
        finally:
            # Restore the previous log levels
            for (log, level) in loggers:
                log.setLevel(level)

    def test_details_with_ip(self):
        database = self.databases.first()
        self._test_details(database, database.ip[0])

    def test_details_with_hostname(self):
        database = self.databases.list()[1]
        self._test_details(database, database.hostname)

    def test_details_without_locality(self):
        database = self.databases.list()[1]
        self._test_details(database, "Locality", assert_contains=False)

    def test_details_with_locality(self):
        database = self.databases.first()
        self._test_details(database, "Locality")

    def test_create_database(self):
        database = self.databases.first()

        url = reverse('horizon:project:databases:create_database',
                      args=[database.id])
        res = self.client.get(url)
        self.assertTemplateUsed(res, 'project/databases/create_database.html')

    @test.create_mocks({api.trove: ('database_create',)})
    def test_create_new_database(self):
        new_database = {
            "status": "ACTIVE",
            "updated": "2013-08-12T22:00:09",
            "name": "NewDB",
            "links": [],
            "created": "2013-08-12T22:00:03",
            "ip": [
                "10.0.0.3",
            ],
            "volume": {
                "used": 0.13,
                "size": 1,
            },
            "flavor": {
                "id": "1",
                "links": [],
            },
            "datastore": {
                "type": "mysql",
                "version": "5.5"
            },
            "id": "12345678-73db-4e23-b52e-368937d72719",
        }

        self.mock_database_create.return_value = new_database

        url = reverse('horizon:project:databases:create_database',
                      args=['id'])
        post = {
            'method': 'CreateDatabaseForm',
            'instance_id': 'id',
            'name': 'NewDB'}

        res = self.client.post(url, post)
        self.mock_database_create.assert_called_once_with(
            test.IsHttpRequest(), u'id', u'NewDB', character_set=u'',
            collation=u'')
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)

    @test.create_mocks({api.trove: ('database_create',)})
    def test_create_new_database_exception(self):
        self.mock_database_create.side_effect = self.exceptions.trove

        url = reverse('horizon:project:databases:create_database',
                      args=['id'])
        post = {
            'method': 'CreateDatabaseForm',
            'instance_id': 'id',
            'name': 'NewDB'}

        res = self.client.post(url, post)
        self.mock_database_create.assert_called_once_with(
            test.IsHttpRequest(), u'id', u'NewDB', character_set=u'',
            collation=u'')
        self.assertEqual(res.status_code, 302)

    @test.create_mocks({api.trove: ('instance_get', 'root_show')})
    def test_show_root(self):
        database = self.databases.first()
        database.id = u'id'
        user = self.database_user_roots.first()

        self.mock_instance_get.return_value = database
        self.mock_root_show.return_value = user

        url = reverse('horizon:project:databases:manage_root',
                      args=['id'])
        res = self.client.get(url)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_root_show, 2,
            mock.call(test.IsHttpRequest(), database.id))
        self.assertTemplateUsed(
            res, 'project/databases/manage_root.html')

    @test.create_mocks({api.trove: ('instance_get', 'root_show')})
    def test_show_root_exception(self):
        database = self.databases.first()

        self.mock_instance_get.return_value = database
        self.mock_root_show.side_effect = self.exceptions.trove

        url = reverse('horizon:project:databases:manage_root',
                      args=['id'])
        res = self.client.get(url)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_root_show.assert_called_once_with(
            test.IsHttpRequest(), u'id')
        self.assertRedirectsNoFollow(res, DETAILS_URL)

    @test.create_mocks({api.trove: ('root_enable',)})
    def test_enable_root(self):
        self.mock_root_enable.return_value = ("root", "password")

        url = reverse('horizon:project:databases:manage_root',
                      args=['id'])
        form_data = {"action": "manage_root__enable_root_action__%s" % 'id'}
        req = self.factory.post(url, form_data)

        kwargs = {'instance_id': 'id'}

        enable_root_info_list = []
        enable_root_info = views.EnableRootInfo('id', 'inst1', False, '')
        enable_root_info_list.append(enable_root_info)

        table = tables.ManageRootTable(req, enable_root_info_list, **kwargs)
        table.maybe_handle()

        self.mock_root_enable.assert_called_once_with(
            test.IsHttpRequest(), [u'id'])
        self.assertEqual(table.data[0].enabled, True)
        self.assertEqual(table.data[0].password, "password")

    @test.create_mocks({api.trove: ('root_enable',)})
    def test_enable_root_exception(self):
        self.mock_root_enable.side_effect = self.exceptions.trove

        url = reverse('horizon:project:databases:manage_root',
                      args=['id'])
        form_data = {"action": "manage_root__enable_root_action__%s" % 'id'}
        req = self.factory.post(url, form_data)

        kwargs = {'instance_id': 'id'}

        enable_root_info_list = []
        enable_root_info = views.EnableRootInfo('id', 'inst1', False, '')
        enable_root_info_list.append(enable_root_info)

        table = tables.ManageRootTable(req, enable_root_info_list, **kwargs)
        table.maybe_handle()

        self.mock_root_enable.assert_called_once_with(
            test.IsHttpRequest(), [u'id'])
        self.assertNotEqual(table.data[0].enabled, True)
        self.assertNotEqual(table.data[0].password, "password")

    @test.create_mocks({api.trove: ('root_disable',)})
    def test_disable_root(self):
        url = reverse('horizon:project:databases:manage_root',
                      args=['id'])
        form_data = {"action": "manage_root__disable_root_action__%s" % 'id'}
        req = self.factory.post(url, form_data)

        kwargs = {'instance_id': 'id'}

        enable_root_info_list = []
        enable_root_info = views.EnableRootInfo(
            'id', 'inst1', True, 'password')
        enable_root_info_list.append(enable_root_info)

        table = tables.ManageRootTable(req, enable_root_info_list, **kwargs)
        table.maybe_handle()

        self.mock_root_disable.assert_called_once_with(
            test.IsHttpRequest(), u'id')
        self.assertEqual(table.data[0].enabled, True)
        self.assertIsNone(table.data[0].password)

    @test.create_mocks({api.trove: ('root_disable',)})
    def test_disable_root_exception(self):
        self.mock_root_disable.side_effect = self.exceptions.trove

        url = reverse('horizon:project:databases:manage_root',
                      args=['id'])
        form_data = {"action": "manage_root__disable_root_action__%s" % 'id'}
        req = self.factory.post(url, form_data)

        kwargs = {'instance_id': 'id'}

        enable_root_info_list = []
        enable_root_info = views.EnableRootInfo(
            'id', 'inst1', True, 'password')
        enable_root_info_list.append(enable_root_info)

        table = tables.ManageRootTable(req, enable_root_info_list, **kwargs)
        table.maybe_handle()

        self.mock_root_disable.assert_called_once_with(
            test.IsHttpRequest(), u'id')
        self.assertEqual(table.data[0].enabled, True)
        self.assertEqual(table.data[0].password, "password")

    @test.create_mocks({
        api.trove: ('instance_get', 'flavor_get', 'user_delete', 'users_list',
                    'user_list_access')
    })
    def test_user_delete(self):
        database = self.databases.first()
        user = self.database_users.first()
        user_db = self.database_user_dbs.first()

        database_id = database.id
        # Instead of using the user's ID, the api uses the user's name. BOOO!
        user_id = user.name + "@" + user.host

        # views.py: DetailView.get_data
        self.mock_instance_get.return_value = database
        self.mock_flavor_get.return_value = self.flavors.first()

        # tabs.py: UserTab.get_user_data
        self.mock_users_list.return_value = [user]
        self.mock_user_list_access.return_value = [user_db]

        # tables.py: DeleteUser.delete
        self.mock_user_delete.return_value = None

        details_url = reverse('horizon:project:databases:detail',
                              args=[database_id])
        url = details_url + '?tab=instance_details__users_tab'
        action_string = u"users__delete__%s" % user_id
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_flavor_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_users_list.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_user_list_access.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str), test.IsA(str),
            host=test.IsA(str))
        self.mock_user_delete.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str),
            test.IsA(str), host=test.IsA(str))
        self.assertRedirectsNoFollow(res, url)

    def test_create_user(self):
        user = self.users.first()

        url = reverse('horizon:project:databases:create_user',
                      args=[user.id])
        res = self.client.get(url)
        self.assertTemplateUsed(res, 'project/databases/create_user.html')

    @test.create_mocks({api.trove: ('user_create',)})
    def test_create_new_user(self):
        database = self.databases.first()
        user = self.users.first()

        new_user = {
            "name": "Test_User2",
            "host": "%",
            "databases": ["TestDB"],
        }

        self.mock_user_create.return_value = new_user

        url = reverse('horizon:project:databases:create_user',
                      args=[database.id])
        post = {
            'method': 'CreateUserForm',
            'instance_id': database.id,
            'name': user.name,
            'password': 'password'}

        res = self.client.post(url, post)
        self.mock_user_create.assert_called_once_with(
            test.IsHttpRequest(), database.id, user.name, u'password',
            host=u'', databases=[])
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)

    @test.create_mocks({api.trove: ('user_create',)})
    def test_create_new_user_exception(self):
        self.mock_user_create.side_effect = self.exceptions.trove

        url = reverse('horizon:project:databases:create_user',
                      args=['id'])
        post = {
            'method': 'CreateUserForm',
            'instance_id': 'id',
            'name': 'name',
            'password': 'password'}

        res = self.client.post(url, post)
        self.mock_user_create.assert_called_once_with(
            test.IsHttpRequest(), u'id', u'name', u'password',
            host=u'', databases=[])
        self.assertEqual(res.status_code, 302)

    @test.create_mocks({api.trove: ('user_update_attributes',)})
    def test_edit_user(self):
        database = self.databases.first()
        user = self.users.first()

        url = reverse('horizon:project:databases:edit_user',
                      args=[database.id, user.name, '%'])
        post = {
            'method': 'EditUserForm',
            'instance_id': database.id,
            'user_name': user.name,
            'user_host': '%',
            'new_name': 'new_name',
            'new_password': 'new_password',
            'new_host': '127.0.0.1'}

        res = self.client.post(url, post)
        self.mock_user_update_attributes.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str),
            test.IsA(str), host=test.IsA(str),
            new_name=test.IsA(str),
            new_password=test.IsA(str),
            new_host=test.IsA(str))
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)

    @test.create_mocks({api.trove: ('user_update_attributes',)})
    def test_edit_user_exception(self):
        database = self.databases.first()
        user = self.users.first()

        url = reverse('horizon:project:databases:edit_user',
                      args=[database.id, user.name, '%'])
        post = {
            'method': 'EditUserForm',
            'instance_id': database.id,
            'user_name': user.name,
            'new_name': 'new_name',
            'user_host': '%',
            'new_password': 'new_password',
            'new_host': '127.0.0.1'}

        res = self.client.post(url, post)
        self.mock_user_update_attributes.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str),
            test.IsA(str), host=test.IsA(str),
            new_name=test.IsA(str),
            new_password=test.IsA(str),
            new_host=test.IsA(str))
        self.assertEqual(res.status_code, 302)

    def test_edit_user_no_values(self):
        database = self.databases.first()
        user = self.users.first()

        url = reverse('horizon:project:databases:edit_user',
                      args=[database.id, user.name, '%'])
        post = {
            'method': 'EditUserForm',
            'instance_id': database.id,
            'user_name': user.name,
            'user_host': '%'}
        res = self.client.post(url, post)

        msg = forms.EditUserForm.validation_error_message
        self.assertFormError(res, "form", None, [msg])

    @test.create_mocks({api.trove: ('database_list', 'user_show_access')})
    def test_access_detail_get(self):
        self.mock_database_list.return_value = self.databases.list()
        self.mock_user_show_access.return_value = self.databases.list()

        url = reverse('horizon:project:databases:access_detail',
                      args=['id', 'name', 'host'])
        res = self.client.get(url)
        self.mock_database_list.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_user_show_access.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str),
            test.IsA(str), host=test.IsA(str))
        self.assertTemplateUsed(
            res, 'project/databases/access_detail.html')

    @test.create_mocks({api.trove: ('database_list', 'user_show_access')})
    def test_access_detail_get_exception(self):
        self.mock_database_list.return_value = self.databases.list()
        self.mock_user_show_access.side_effect = self.exceptions.trove

        url = reverse('horizon:project:databases:access_detail',
                      args=['id', 'name', 'host'])
        res = self.client.get(url)
        self.mock_database_list.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_user_show_access.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str),
            test.IsA(str), host=test.IsA(str))
        self.assertRedirectsNoFollow(res, DETAILS_URL)

    @test.create_mocks({api.trove: ('user_grant_access',)})
    def test_detail_grant_access(self):
        url = reverse('horizon:project:databases:access_detail',
                      args=['id', 'name', 'host'])
        form_data = {"action": "access__grant_access__%s" % 'db1'}
        req = self.factory.post(url, form_data)

        kwargs = {'instance_id': 'id', 'user_name': 'name', 'user_host': '%'}

        db_access_list = []
        db_access = views.DBAccess('db1', False)
        db_access_list.append(db_access)

        table = tables.AccessTable(req, db_access_list, **kwargs)
        handled = table.maybe_handle()

        self.mock_user_grant_access.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str), test.IsA(str),
            [test.IsA(str)], host=test.IsA(str))
        handled_url = handled['location']
        self.assertEqual(handled_url, url)

    @test.create_mocks({api.trove: ('user_grant_access',)})
    def test_detail_grant_access_exception(self):
        self.mock_user_grant_access.side_effect = self.exceptions.trove

        url = reverse('horizon:project:databases:access_detail',
                      args=['id', 'name', 'host'])
        form_data = {"action": "access__grant_access__%s" % 'db1'}
        req = self.factory.post(url, form_data)

        kwargs = {'instance_id': 'id', 'user_name': 'name', 'user_host': '%'}

        db_access_list = []
        db_access = views.DBAccess('db1', False)
        db_access_list.append(db_access)

        table = tables.AccessTable(req, db_access_list, **kwargs)
        handled = table.maybe_handle()

        self.mock_user_grant_access.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str), test.IsA(str),
            [test.IsA(str)], host=test.IsA(str))
        handled_url = handled['location']
        self.assertEqual(handled_url, url)

    @test.create_mocks({api.trove: ('user_revoke_access',)})
    def test_detail_revoke_access(self):
        url = reverse('horizon:project:databases:access_detail',
                      args=['id', 'name', 'host'])
        form_data = {"action": "access__revoke_access__%s" % 'db1'}
        req = self.factory.post(url, form_data)

        kwargs = {'instance_id': 'id', 'user_name': 'name', 'user_host': '%'}

        db_access_list = []
        db_access = views.DBAccess('db1', True)
        db_access_list.append(db_access)

        table = tables.AccessTable(req, db_access_list, **kwargs)
        handled = table.maybe_handle()

        self.mock_user_revoke_access.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str), test.IsA(str),
            test.IsA(str), host=test.IsA(str))
        handled_url = handled['location']
        self.assertEqual(handled_url, url)

    @test.create_mocks({api.trove: ('user_revoke_access',)})
    def test_detail_revoke_access_exception(self):
        self.mock_user_revoke_access.side_effect = self.exceptions.trove

        url = reverse('horizon:project:databases:access_detail',
                      args=['id', 'name', 'host'])
        form_data = {"action": "access__revoke_access__%s" % 'db1'}
        req = self.factory.post(url, form_data)

        kwargs = {'instance_id': 'id', 'user_name': 'name', 'user_host': '%'}

        db_access_list = []
        db_access = views.DBAccess('db1', True)
        db_access_list.append(db_access)

        table = tables.AccessTable(req, db_access_list, **kwargs)
        handled = table.maybe_handle()

        self.mock_user_revoke_access.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str), test.IsA(str),
            test.IsA(str), host=test.IsA(str))
        handled_url = handled['location']
        self.assertEqual(handled_url, url)

    @test.create_mocks({
        api.trove: ('instance_get', 'instance_resize_volume')})
    def test_resize_volume(self):
        database = self.databases.first()
        database_id = database.id
        database_size = database.volume.get('size')

        # views.py: DetailView.get_data
        self.mock_instance_get.return_value = database

        # forms.py: ResizeVolumeForm.handle
        self.mock_instance_resize_volume.return_value = None

        url = reverse('horizon:project:databases:resize_volume',
                      args=[database_id])
        post = {
            'instance_id': database_id,
            'orig_size': database_size,
            'new_size': database_size + 1,
        }
        res = self.client.post(url, post)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_instance_resize_volume.assert_called_once_with(
            test.IsHttpRequest(), database_id, test.IsA(int))
        self.assertNoFormErrors(res)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({api.trove: ('instance_get', )})
    def test_resize_volume_bad_value(self):
        database = self.databases.first()
        database_id = database.id
        database_size = database.volume.get('size')

        # views.py: DetailView.get_data
        self.mock_instance_get.return_value = database

        url = reverse('horizon:project:databases:resize_volume',
                      args=[database_id])
        post = {
            'instance_id': database_id,
            'orig_size': database_size,
            'new_size': database_size,
        }
        res = self.client.post(url, post)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.assertContains(
            res, "New size for volume must be greater than current size.")

    @test.create_mocks(
        {api.trove: ('instance_get',
                     'flavor_list')})
    def test_resize_instance_get(self):
        database = self.databases.first()

        # views.py: DetailView.get_data
        self.mock_instance_get.return_value = database
        self.mock_flavor_list.return_value = self.database_flavors.list()

        url = reverse('horizon:project:databases:resize_instance',
                      args=[database.id])

        res = self.client.get(url)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), database.id)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, 'project/databases/resize_instance.html')
        option = '<option value="%s">%s</option>'
        for flavor in self.database_flavors.list():
            if flavor.id == database.flavor['id']:
                self.assertNotContains(res, option % (flavor.id, flavor.name))
            else:
                self.assertContains(res, option % (flavor.id, flavor.name))

    @test.create_mocks(
        {api.trove: ('instance_get',
                     'flavor_list',
                     'instance_resize')})
    def test_resize_instance(self):
        database = self.databases.first()

        # views.py: DetailView.get_data
        self.mock_instance_get.return_value = database
        self.mock_flavor_list.return_value = self.database_flavors.list()

        old_flavor = self.database_flavors.list()[0]
        new_flavor = self.database_flavors.list()[1]

        self.mock_instance_resize.return_value = None

        url = reverse('horizon:project:databases:resize_instance',
                      args=[database.id])
        post = {
            'instance_id': database.id,
            'old_flavor_name': old_flavor.name,
            'old_flavor_id': old_flavor.id,
            'new_flavor': new_flavor.id
        }
        res = self.client.post(url, post)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), database.id)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_instance_resize.assert_called_once_with(
            test.IsHttpRequest(), database.id, new_flavor.id)
        self.assertNoFormErrors(res)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({
        api.trove: ('backup_list', 'configuration_list', 'datastore_flavors',
                    'datastore_list', 'datastore_version_list', 'flavor_list',
                    'instance_create', 'instance_get', 'instance_list_all'),
        dash_api.cinder: ('volume_type_list',),
        dash_api.neutron: ('network_list',),
        dash_api.nova: ('availability_zone_list',),
        policy: ('check',),
    })
    def test_create_replica_instance(self):
        self.mock_check.return_value = True
        self.mock_datastore_flavors.return_value = self.flavors.list()
        self.mock_backup_list.return_value = self.database_backups.list()
        self.mock_instance_list_all.return_value = self.databases.list()
        self.mock_datastore_list.return_value = self.datastores.list()
        self.mock_datastore_version_list.return_value = (
            self.datastore_versions.list())

        self.mock_volume_type_list.return_value = []

        self.mock_network_list.side_effect = [self.networks.list()[:1],
                                              self.networks.list()[1:]]

        nics = [{"net-id": self.networks.first().id}]

        self.mock_availability_zone_list.return_value = (
            self.availability_zones.list())

        self.mock_instance_get.return_value = self.databases.first()

        datastore = 'mysql'
        datastore_version = '5.5'
        field_name = self._build_flavor_widget_name(datastore,
                                                    datastore_version)
        # Mock create database call
        self.mock_instance_create.return_value = self.databases.first()

        post = {
            'name': "MyDB",
            'volume': '1',
            'flavor': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'datastore': field_name,
            field_name: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'network': self.networks.first().id,
            'initial_state': 'master',
            'master': self.databases.first().id,
            'replica_count': 2,
            'volume_type': 'no_type'
        }

        res = self.client.post(LAUNCH_URL, post)
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_check, 5, mock.call((), test.IsHttpRequest()))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_datastore_flavors, 20,
            mock.call(test.IsHttpRequest(),
                      test.IsA(str),
                      test.IsA(str)))
        self.mock_backup_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_instance_list_all.assert_called_once_with(
            test.IsHttpRequest())
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_datastore_version_list, 4,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.mock_volume_type_list.assert_called_once_with(
            test.IsHttpRequest())
        self.mock_network_list.assert_has_calls([
            mock.call(test.IsHttpRequest(),
                      tenant_id=self.tenant.id,
                      shared=False),
            mock.call(test.IsHttpRequest(), shared=True)])
        self.mock_availability_zone_list.assert_called_once_with(
            test.IsHttpRequest())
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_instance_create.assert_called_once_with(
            test.IsHttpRequest(),
            test.IsA(str),
            test.IsA(int),
            test.IsA(str),
            databases=None,
            datastore=datastore,
            datastore_version=datastore_version,
            restore_point=None,
            replica_of=self.databases.first().id,
            configuration=None,
            users=None,
            nics=nics,
            replica_count=2,
            volume_type=None,
            locality=None,
            availability_zone=test.IsA(str),
            access=None)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({
        api.trove: ('promote_to_replica_source',),
        views.PromoteToReplicaSourceView: ('get_initial',)})
    def test_promote_replica_instance(self):
        replica_source = self.databases.first()
        replica = self.databases.list()[1]

        initial = {'instance_id': replica_source.id,
                   'replica': replica,
                   'replica_source': replica_source}
        self.mock_get_initial.return_value = initial

        url = reverse('horizon:project:databases:promote_to_replica_source',
                      args=[replica_source.id])
        form = {
            'instance_id': replica_source.id
        }
        res = self.client.post(url, form)
        self.mock_get_initial.assert_called_once()
        self.mock_promote_to_replica_source.assert_called_once_with(
            test.IsHttpRequest(), replica_source.id)
        self.assertNoFormErrors(res)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({
        api.trove: ('promote_to_replica_source',),
        views.PromoteToReplicaSourceView: ('get_initial',)})
    def test_promote_replica_instance_exception(self):
        replica_source = self.databases.first()
        replica = self.databases.list()[1]

        initial = {'instance_id': replica_source.id,
                   'replica': replica,
                   'replica_source': replica_source}
        self.mock_get_initial.return_value = initial

        self.mock_promote_to_replica_source.side_effect = (
            self.exceptions.trove)

        url = reverse('horizon:project:databases:promote_to_replica_source',
                      args=[replica_source.id])
        form = {
            'instance_id': replica_source.id
        }
        res = self.client.post(url, form)
        self.mock_get_initial.assert_called_once()
        self.mock_promote_to_replica_source.assert_called_once_with(
            test.IsHttpRequest(), replica_source.id)
        self.assertEqual(res.status_code, 302)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({
        api.trove: ('flavor_list', 'instance_list',
                    'eject_replica_source',),
    })
    def test_eject_replica_source(self):
        databases = common.Paginated(self.databases.list())
        database = databases[2]

        databases = common.Paginated(self.databases.list())
        self.mock_instance_list.return_value = databases
        self.mock_flavor_list.return_value = self.flavors.list()

        res = self.client.post(
            INDEX_URL,
            {'action': 'databases__eject_replica_source__%s' % database.id})

        self.mock_eject_replica_source.assert_called_once_with(
            test.IsHttpRequest(), database.id)
        self.mock_instance_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({
        api.trove: ('flavor_list', 'instance_list',
                    'eject_replica_source',),
    })
    def test_eject_replica_source_exception(self):
        databases = common.Paginated(self.databases.list())
        database = databases[2]

        self.mock_eject_replica_source.side_effect = self.exceptions.trove

        databases = common.Paginated(self.databases.list())
        self.mock_instance_list.return_value = databases
        self.mock_flavor_list.return_value = self.flavors.list()

        res = self.client.post(
            INDEX_URL,
            {'action': 'databases__eject_replica_source__%s' % database.id})

        self.mock_eject_replica_source.assert_called_once_with(
            test.IsHttpRequest(), database.id)
        self.mock_instance_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({
        api.trove: ('instance_list',)
    })
    def test_master_list_pagination(self):
        request = http.HttpRequest()

        first_part = common.Paginated(items=self.databases.list()[:1],
                                      next_marker='marker')
        second_part = common.Paginated(items=self.databases.list()[1:])

        self.mock_instance_list.side_effect = [
            first_part, second_part, first_part]

        advanced_page = create_instance.AdvancedAction(request, None)
        choices = advanced_page.populate_master_choices(request, None)
        expected_calls = [
            mock.call(request),
            mock.call(request, marker='marker'),
            mock.call(request)]
        self.assertEqual(expected_calls,
                         self.mock_instance_list.call_args_list)
        self.assertEqual(len(choices), len(self.databases.list()) + 1)

    def _build_datastore_display_text(self, datastore, datastore_version):
        return datastore + ' - ' + datastore_version

    def _build_flavor_widget_name(self, datastore, datastore_version):
        return common_utils.hexlify(self._build_datastore_display_text(
            datastore, datastore_version))

    @test.create_mocks({
        api.trove: ('instance_get',
                    'configuration_list',
                    'instance_attach_configuration'),
    })
    def test_attach_configuration(self):
        database = self.databases.first()
        configuration = self.database_configurations.first()

        self.mock_instance_get.return_value = database
        self.mock_configuration_list.return_value = (
            self.database_configurations.list())
        self.mock_instance_attach_configuration.return_value = None

        url = reverse('horizon:project:databases:attach_config',
                      args=[database.id])
        form = {
            'instance_id': database.id,
            'configuration': configuration.id,
        }
        res = self.client.post(url, form)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_configuration_list.assert_called_once_with(
            test.IsHttpRequest())
        self.mock_instance_attach_configuration.assert_called_once_with(
            test.IsHttpRequest(), database.id, configuration.id)
        self.assertNoFormErrors(res)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({
        api.trove: ('instance_get',
                    'configuration_list',
                    'instance_attach_configuration'),
    })
    def test_attach_configuration_exception(self):
        database = self.databases.first()
        configuration = self.database_configurations.first()

        self.mock_instance_get.return_value = database
        self.mock_configuration_list.return_value = (
            self.database_configurations.list())
        self.mock_instance_attach_configuration.side_effect = (
            self.exceptions.trove)

        url = reverse('horizon:project:databases:attach_config',
                      args=[database.id])
        form = {
            'instance_id': database.id,
            'configuration': configuration.id,
        }
        res = self.client.post(url, form)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_configuration_list.assert_called_once_with(
            test.IsHttpRequest())
        self.mock_instance_attach_configuration.assert_called_once_with(
            test.IsHttpRequest(), database.id, configuration.id)
        self.assertEqual(res.status_code, 302)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({
        api.trove: ('instance_list',
                    'flavor_list',
                    'instance_detach_configuration',),
    })
    def test_detach_configuration(self):
        databases = common.Paginated(self.databases.list())
        database = databases[2]

        self.mock_instance_list.return_value = databases
        self.mock_flavor_list.return_value = self.flavors.list()
        self.mock_instance_detach_configuration.return_value = None

        res = self.client.post(
            INDEX_URL,
            {'action': 'databases__detach_configuration__%s' % database.id})

        self.mock_instance_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_instance_detach_configuration.assert_called_once_with(
            test.IsHttpRequest(), database.id)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({
        api.trove: ('instance_list',
                    'flavor_list',
                    'instance_detach_configuration',),
    })
    def test_detach_configuration_exception(self):
        databases = common.Paginated(self.databases.list())
        database = databases[2]

        self.mock_instance_list.return_value = databases
        self.mock_flavor_list.return_value = self.flavors.list()
        self.mock_instance_detach_configuration.side_effect = (
            self.exceptions.trove)

        res = self.client.post(
            INDEX_URL,
            {'action': 'databases__detach_configuration__%s' % database.id})

        self.mock_instance_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_instance_detach_configuration.assert_called_once_with(
            test.IsHttpRequest(), database.id)
        self.assertRedirectsNoFollow(res, INDEX_URL)
