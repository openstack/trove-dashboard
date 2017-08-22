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

import binascii
import logging

import django
from django.core.urlresolvers import reverse
from django import http
import unittest

from mox3.mox import IsA  # noqa
import six

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

INDEX_URL = reverse('horizon:project:databases:index')
LAUNCH_URL = reverse('horizon:project:databases:launch')
DETAILS_URL = reverse('horizon:project:databases:detail', args=['id'])


class DatabaseTests(test.TestCase):
    @test.create_stubs(
        {api.trove: ('instance_list', 'flavor_list')})
    def test_index(self):
        # Mock database instances
        databases = common.Paginated(self.databases.list())
        api.trove.instance_list(IsA(http.HttpRequest), marker=None)\
            .AndReturn(databases)
        # Mock flavors
        api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndReturn(self.flavors.list())

        self.mox.ReplayAll()
        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, 'project/databases/index.html')
        # Check the Host column displaying ip or hostname
        self.assertContains(res, '10.0.0.3')
        self.assertContains(res, 'trove.instance-2.com')

    @test.create_stubs(
        {api.trove: ('instance_list', 'flavor_list')})
    def test_index_flavor_exception(self):
        # Mock database instances
        databases = common.Paginated(self.databases.list())
        api.trove.instance_list(IsA(http.HttpRequest), marker=None)\
            .AndReturn(databases)
        # Mock flavors
        api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()
        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, 'project/databases/index.html')
        self.assertMessageCount(res, error=1)

    @test.create_stubs(
        {api.trove: ('instance_list',)})
    def test_index_list_exception(self):
        # Mock database instances
        api.trove.instance_list(IsA(http.HttpRequest), marker=None)\
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()
        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, 'project/databases/index.html')
        self.assertMessageCount(res, error=1)

    @test.create_stubs(
        {api.trove: ('instance_list', 'flavor_list')})
    def test_index_pagination(self):
        # Mock database instances
        databases = self.databases.list()
        last_record = databases[-1]
        databases = common.Paginated(databases, next_marker="foo")
        api.trove.instance_list(IsA(http.HttpRequest), marker=None)\
            .AndReturn(databases)
        # Mock flavors
        api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndReturn(self.flavors.list())

        self.mox.ReplayAll()
        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, 'project/databases/index.html')
        self.assertContains(
            res, 'marker=' + last_record.id)

    @test.create_stubs(
        {api.trove: ('instance_list', 'flavor_list')})
    def test_index_flavor_list_exception(self):
        # Mocking instances.
        databases = common.Paginated(self.databases.list())
        api.trove.instance_list(
            IsA(http.HttpRequest),
            marker=None,
        ).AndReturn(databases)
        # Mocking flavor list with raising an exception.
        api.trove.flavor_list(
            IsA(http.HttpRequest),
        ).AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()

        res = self.client.get(INDEX_URL)

        self.assertTemplateUsed(res, 'project/databases/index.html')
        self.assertMessageCount(res, error=1)

    @test.create_stubs({
        api.trove: ('backup_list', 'configuration_list', 'datastore_flavors',
                    'datastore_list', 'datastore_version_list', 'flavor_list',
                    'instance_list'),
        dash_api.cinder: ('volume_type_list',),
        dash_api.neutron: ('network_list',),
        dash_api.nova: ('availability_zone_list',),
        policy: ('check',),
    })
    def test_launch_instance(self):
        policy.check((), IsA(http.HttpRequest)).MultipleTimes().AndReturn(True)
        api.trove.datastore_flavors(IsA(http.HttpRequest),
                                    IsA(six.string_types),
                                    IsA(six.string_types)).\
            MultipleTimes().AndReturn(self.flavors.list())
        api.trove.backup_list(IsA(http.HttpRequest)).AndReturn(
            self.database_backups.list())
        api.trove.configuration_list(IsA(http.HttpRequest)).AndReturn([])
        api.trove.instance_list(IsA(http.HttpRequest)).AndReturn(
            self.databases.list())
        # Mock datastores
        api.trove.datastore_list(IsA(http.HttpRequest)).AndReturn(
            self.datastores.list())
        # Mock datastore versions
        api.trove.datastore_version_list(IsA(http.HttpRequest), IsA(str)).\
            MultipleTimes().AndReturn(self.datastore_versions.list())

        dash_api.cinder.volume_type_list(IsA(http.HttpRequest)).AndReturn([])

        dash_api.neutron.network_list(IsA(http.HttpRequest),
                                      tenant_id=self.tenant.id,
                                      shared=False).AndReturn(
                                          self.networks.list()[:1])

        dash_api.neutron.network_list(IsA(http.HttpRequest),
                                      shared=True).AndReturn(
                                          self.networks.list()[1:])

        dash_api.nova.availability_zone_list(IsA(http.HttpRequest)) \
            .AndReturn(self.availability_zones.list())

        self.mox.ReplayAll()
        res = self.client.get(LAUNCH_URL)
        self.assertTemplateUsed(res, 'project/databases/launch.html')

    # django 1.7 and later does not handle the thrown Http302
    # exception well enough.
    # TODO(mrunge): re-check when django-1.8 is stable
    @unittest.skipIf(django.VERSION >= (1, 7, 0),
                     'Currently skipped with Django >= 1.7')
    @test.create_stubs({api.trove: ('flavor_list',)})
    def test_launch_instance_exception_on_flavors(self):
        trove_exception = self.exceptions.nova
        api.trove.flavor_list(IsA(http.HttpRequest)).AndRaise(trove_exception)
        self.mox.ReplayAll()

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

        finally:
            # Restore the previous log levels
            for (log, level) in loggers:
                log.setLevel(level)

    @test.create_stubs({
        api.trove: ('backup_list', 'configuration_list', 'datastore_flavors',
                    'datastore_list', 'datastore_version_list', 'flavor_list',
                    'instance_create', 'instance_list'),
        dash_api.cinder: ('volume_type_list',),
        dash_api.neutron: ('network_list',),
        dash_api.nova: ('availability_zone_list',),
        policy: ('check',),
    })
    def test_create_simple_instance(self):
        policy.check((), IsA(http.HttpRequest)).MultipleTimes().AndReturn(True)
        api.trove.datastore_flavors(IsA(http.HttpRequest),
                                    IsA(six.string_types),
                                    IsA(six.string_types)).\
            MultipleTimes().AndReturn(self.flavors.list())

        api.trove.backup_list(IsA(http.HttpRequest)).AndReturn(
            self.database_backups.list())

        api.trove.instance_list(IsA(http.HttpRequest)).AndReturn(
            self.databases.list())

        # Mock datastores
        api.trove.datastore_list(IsA(http.HttpRequest))\
            .AndReturn(self.datastores.list())

        # Mock datastore versions
        api.trove.datastore_version_list(IsA(http.HttpRequest), IsA(str))\
            .MultipleTimes().AndReturn(self.datastore_versions.list())

        dash_api.cinder.volume_type_list(IsA(http.HttpRequest)).AndReturn([])

        dash_api.neutron.network_list(IsA(http.HttpRequest),
                                      tenant_id=self.tenant.id,
                                      shared=False).AndReturn(
                                          self.networks.list()[:1])

        dash_api.neutron.network_list(IsA(http.HttpRequest),
                                      shared=True).AndReturn(
                                          self.networks.list()[1:])

        nics = [{"net-id": self.networks.first().id, "v4-fixed-ip": ''}]

        datastore = 'mysql'
        datastore_version = '5.5'
        field_name = self._build_flavor_widget_name(datastore,
                                                    datastore_version)
        dash_api.nova.availability_zone_list(IsA(http.HttpRequest)) \
            .AndReturn(self.availability_zones.list())

        # Actual create database call
        api.trove.instance_create(
            IsA(http.HttpRequest),
            IsA(six.text_type),
            IsA(int),
            IsA(six.text_type),
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
            availability_zone=IsA(six.text_type)
        ).AndReturn(self.databases.first())

        self.mox.ReplayAll()
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
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({
        api.trove: ('backup_list', 'configuration_list', 'datastore_flavors',
                    'datastore_list', 'datastore_version_list', 'flavor_list',
                    'instance_create', 'instance_list'),
        dash_api.cinder: ('volume_type_list',),
        dash_api.neutron: ('network_list',),
        dash_api.nova: ('availability_zone_list',),
        policy: ('check',),
    })
    def test_create_simple_instance_exception(self):
        policy.check((), IsA(http.HttpRequest)).MultipleTimes().AndReturn(True)
        trove_exception = self.exceptions.nova
        api.trove.datastore_flavors(IsA(http.HttpRequest),
                                    IsA(six.string_types),
                                    IsA(six.string_types)).\
            MultipleTimes().AndReturn(self.flavors.list())

        api.trove.backup_list(IsA(http.HttpRequest)).AndReturn(
            self.database_backups.list())

        api.trove.instance_list(IsA(http.HttpRequest)).AndReturn(
            self.databases.list())

        # Mock datastores
        api.trove.datastore_list(IsA(http.HttpRequest))\
            .AndReturn(self.datastores.list())

        # Mock datastore versions
        api.trove.datastore_version_list(IsA(http.HttpRequest), IsA(str))\
            .MultipleTimes().AndReturn(self.datastore_versions.list())

        dash_api.cinder.volume_type_list(IsA(http.HttpRequest)).AndReturn([])

        dash_api.neutron.network_list(IsA(http.HttpRequest),
                                      tenant_id=self.tenant.id,
                                      shared=False).AndReturn(
                                          self.networks.list()[:1])

        dash_api.neutron.network_list(IsA(http.HttpRequest),
                                      shared=True).AndReturn(
                                          self.networks.list()[1:])

        nics = [{"net-id": self.networks.first().id, "v4-fixed-ip": ''}]

        datastore = 'mysql'
        datastore_version = '5.5'
        field_name = self._build_flavor_widget_name(datastore,
                                                    datastore_version)
        dash_api.nova.availability_zone_list(IsA(http.HttpRequest)) \
            .AndReturn(self.availability_zones.list())

        # Actual create database call
        api.trove.instance_create(
            IsA(http.HttpRequest),
            IsA(six.text_type),
            IsA(int),
            IsA(six.text_type),
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
            availability_zone=IsA(six.text_type)
        ).AndRaise(trove_exception)

        self.mox.ReplayAll()
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
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({
        api.trove: ('instance_get', 'flavor_get', 'root_show')
    })
    def _test_details(self, database, test_text, assert_contains=True):
        api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))\
            .AndReturn(database)
        api.trove.flavor_get(IsA(http.HttpRequest), IsA(str))\
            .AndReturn(self.flavors.first())
        api.trove.root_show(IsA(http.HttpRequest), IsA(str)) \
            .AndReturn(self.database_user_roots.first())

        self.mox.ReplayAll()

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

    @test.create_stubs({api.trove: ('database_create',)})
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

        api.trove.database_create(
            IsA(http.HttpRequest), u'id', u'NewDB', character_set=u'',
            collation=u'').AndReturn(new_database)
        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:create_database',
                      args=['id'])
        post = {
            'method': 'CreateDatabaseForm',
            'instance_id': 'id',
            'name': 'NewDB'}

        res = self.client.post(url, post)
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)

    @test.create_stubs({api.trove: ('database_create',)})
    def test_create_new_database_exception(self):
        api.trove.database_create(
            IsA(http.HttpRequest), u'id', u'NewDB', character_set=u'',
            collation=u'').AndRaise(self.exceptions.trove)
        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:create_database',
                      args=['id'])
        post = {
            'method': 'CreateDatabaseForm',
            'instance_id': 'id',
            'name': 'NewDB'}

        res = self.client.post(url, post)
        self.assertEqual(res.status_code, 302)

    @test.create_stubs({api.trove: ('instance_get', 'root_show')})
    def test_show_root(self):
        database = self.databases.first()
        database.id = u'id'
        user = self.database_user_roots.first()

        api.trove.instance_get(IsA(http.HttpRequest), IsA(unicode))\
            .AndReturn(database)

        api.trove.root_show(IsA(http.HttpRequest), database.id) \
            .MultipleTimes().AndReturn(user)

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:manage_root',
                      args=['id'])
        res = self.client.get(url)
        self.assertTemplateUsed(
            res, 'project/databases/manage_root.html')

    @test.create_stubs({api.trove: ('instance_get', 'root_show')})
    def test_show_root_exception(self):
        database = self.databases.first()

        api.trove.instance_get(IsA(http.HttpRequest), IsA(unicode))\
            .AndReturn(database)

        api.trove.root_show(IsA(http.HttpRequest), u'id') \
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:manage_root',
                      args=['id'])
        res = self.client.get(url)
        self.assertRedirectsNoFollow(res, DETAILS_URL)

    @test.create_stubs({api.trove: ('root_enable',)})
    def test_enable_root(self):
        api.trove.root_enable(IsA(http.HttpRequest), [u'id']) \
            .AndReturn(("root", "password"))

        self.mox.ReplayAll()

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

        self.assertEqual(table.data[0].enabled, True)
        self.assertEqual(table.data[0].password, "password")

    @test.create_stubs({api.trove: ('root_enable',)})
    def test_enable_root_exception(self):
        api.trove.root_enable(IsA(http.HttpRequest), [u'id']) \
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()

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

        self.assertNotEqual(table.data[0].enabled, True)
        self.assertNotEqual(table.data[0].password, "password")

    @test.create_stubs({api.trove: ('root_disable',)})
    def test_disable_root(self):
        api.trove.root_disable(IsA(http.HttpRequest), u'id')

        self.mox.ReplayAll()

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

        self.assertEqual(table.data[0].enabled, True)
        self.assertIsNone(table.data[0].password)

    @test.create_stubs({api.trove: ('root_disable',)})
    def test_disable_root_exception(self):
        api.trove.root_disable(IsA(http.HttpRequest), u'id') \
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()

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

        self.assertEqual(table.data[0].enabled, True)
        self.assertEqual(table.data[0].password, "password")

    @test.create_stubs({
        api.trove: ('instance_get', 'flavor_get', 'user_delete', 'users_list',
                    'user_list_access')
    })
    def test_user_delete(self):
        database = self.databases.first()
        user = self.database_users.first()
        user_db = self.database_user_dbs.first()

        database_id = database.id
        # Instead of using the user's ID, the api uses the user's name. BOOO!
        user_id = user.name

        # views.py: DetailView.get_data
        api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))\
            .AndReturn(database)
        api.trove.flavor_get(IsA(http.HttpRequest), IsA(str))\
            .AndReturn(self.flavors.first())

        # tabs.py: UserTab.get_user_data
        api.trove.users_list(IsA(http.HttpRequest),
                             IsA(str)).AndReturn([user])
        api.trove.user_list_access(IsA(http.HttpRequest),
                                   IsA(str),
                                   IsA(str),
                                   host=IsA(str)).AndReturn([user_db])

        # tables.py: DeleteUser.delete
        api.trove.user_delete(IsA(http.HttpRequest),
                              IsA(six.text_type),
                              IsA(six.text_type)).AndReturn(None)

        self.mox.ReplayAll()

        details_url = reverse('horizon:project:databases:detail',
                              args=[database_id])
        url = details_url + '?tab=instance_details__users_tab'
        action_string = u"users__delete__%s" % user_id
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.assertRedirectsNoFollow(res, url)

    def test_create_user(self):
        user = self.users.first()

        url = reverse('horizon:project:databases:create_user',
                      args=[user.id])
        res = self.client.get(url)
        self.assertTemplateUsed(res, 'project/databases/create_user.html')

    @test.create_stubs({api.trove: ('user_create',)})
    def test_create_new_user(self):
        database = self.databases.first()
        user = self.users.first()

        new_user = {
            "name": "Test_User2",
            "host": "%",
            "databases": ["TestDB"],
        }

        api.trove.user_create(
            IsA(http.HttpRequest), database.id, user.name, u'password',
            host=u'', databases=[]).AndReturn(new_user)

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:create_user',
                      args=[database.id])
        post = {
            'method': 'CreateUserForm',
            'instance_id': database.id,
            'name': user.name,
            'password': 'password'}

        res = self.client.post(url, post)
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)

    @test.create_stubs({api.trove: ('user_create',)})
    def test_create_new_user_exception(self):
        api.trove.user_create(
            IsA(http.HttpRequest), u'id', u'name', u'password',
            host=u'', databases=[]).AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:create_user',
                      args=['id'])
        post = {
            'method': 'CreateUserForm',
            'instance_id': 'id',
            'name': 'name',
            'password': 'password'}

        res = self.client.post(url, post)
        self.assertEqual(res.status_code, 302)

    @test.create_stubs({api.trove: ('user_update_attributes',)})
    def test_edit_user(self):
        database = self.databases.first()
        user = self.users.first()

        api.trove.user_update_attributes(
            IsA(http.HttpRequest), IsA(six.text_type), IsA(six.text_type),
            host=IsA(six.text_type), new_name=IsA(six.text_type),
            new_password=IsA(six.text_type), new_host=IsA(six.text_type))

        self.mox.ReplayAll()

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
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)

    @test.create_stubs({api.trove: ('user_update_attributes',)})
    def test_edit_user_exception(self):
        database = self.databases.first()
        user = self.users.first()

        api.trove.user_update_attributes(
            IsA(http.HttpRequest), IsA(six.text_type), IsA(six.text_type),
            host=IsA(six.text_type), new_name=IsA(six.text_type),
            new_password=IsA(six.text_type), new_host=IsA(six.text_type))

        self.mox.ReplayAll()

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

    @test.create_stubs({api.trove: ('database_list', 'user_show_access')})
    def test_access_detail_get(self):
        api.trove.database_list(IsA(http.HttpRequest), IsA(six.text_type)) \
            .AndReturn(self.databases.list())

        api.trove.user_show_access(IsA(http.HttpRequest), IsA(six.text_type),
                                   IsA(six.text_type),
                                   host=IsA(six.text_type)) \
            .AndReturn(self.databases.list())

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:access_detail',
                      args=['id', 'name', 'host'])
        res = self.client.get(url)
        self.assertTemplateUsed(
            res, 'project/databases/access_detail.html')

    @test.create_stubs({api.trove: ('database_list', 'user_show_access')})
    def test_access_detail_get_exception(self):
        api.trove.database_list(IsA(http.HttpRequest), IsA(six.text_type)) \
            .AndReturn(self.databases.list())

        api.trove.user_show_access(IsA(http.HttpRequest), IsA(six.text_type),
                                   IsA(six.text_type),
                                   host=IsA(six.text_type)) \
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:access_detail',
                      args=['id', 'name', 'host'])
        res = self.client.get(url)
        self.assertRedirectsNoFollow(res, DETAILS_URL)

    @test.create_stubs({api.trove: ('user_grant_access',)})
    def test_detail_grant_access(self):
        api.trove.user_grant_access(
            IsA(http.HttpRequest), IsA(six.text_type), IsA(six.text_type),
            [IsA(six.text_type)], host=IsA(six.text_type))

        self.mox.ReplayAll()

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

        handled_url = handled['location']
        self.assertEqual(handled_url, url)

    @test.create_stubs({api.trove: ('user_grant_access',)})
    def test_detail_grant_access_exception(self):
        api.trove.user_grant_access(
            IsA(http.HttpRequest), IsA(six.text_type), IsA(six.text_type),
            [IsA(six.text_type)], host=IsA(six.text_type)) \
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()

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

        handled_url = handled['location']
        self.assertEqual(handled_url, url)

    @test.create_stubs({api.trove: ('user_revoke_access',)})
    def test_detail_revoke_access(self):

        api.trove.user_revoke_access(
            IsA(http.HttpRequest), IsA(six.text_type), IsA(six.text_type),
            [IsA(six.text_type)], host=IsA(six.text_type))

        self.mox.ReplayAll()

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

        handled_url = handled['location']
        self.assertEqual(handled_url, url)

    @test.create_stubs({api.trove: ('user_revoke_access',)})
    def test_detail_revoke_access_exception(self):

        api.trove.user_revoke_access(
            IsA(http.HttpRequest), IsA(six.text_type), IsA(six.text_type),
            [IsA(six.text_type)], host=IsA(six.text_type)) \
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()

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

        handled_url = handled['location']
        self.assertEqual(handled_url, url)

    @test.create_stubs({
        api.trove: ('instance_get', 'instance_resize_volume')})
    def test_resize_volume(self):
        database = self.databases.first()
        database_id = database.id
        database_size = database.volume.get('size')

        # views.py: DetailView.get_data
        api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))\
            .AndReturn(database)

        # forms.py: ResizeVolumeForm.handle
        api.trove.instance_resize_volume(IsA(http.HttpRequest),
                                         database_id,
                                         IsA(int)).AndReturn(None)

        self.mox.ReplayAll()
        url = reverse('horizon:project:databases:resize_volume',
                      args=[database_id])
        post = {
            'instance_id': database_id,
            'orig_size': database_size,
            'new_size': database_size + 1,
        }
        res = self.client.post(url, post)
        self.assertNoFormErrors(res)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({api.trove: ('instance_get', )})
    def test_resize_volume_bad_value(self):
        database = self.databases.first()
        database_id = database.id
        database_size = database.volume.get('size')

        # views.py: DetailView.get_data
        api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))\
            .AndReturn(database)

        self.mox.ReplayAll()
        url = reverse('horizon:project:databases:resize_volume',
                      args=[database_id])
        post = {
            'instance_id': database_id,
            'orig_size': database_size,
            'new_size': database_size,
        }
        res = self.client.post(url, post)
        self.assertContains(
            res, "New size for volume must be greater than current size.")

    @test.create_stubs(
        {api.trove: ('instance_get',
                     'flavor_list')})
    def test_resize_instance_get(self):
        database = self.databases.first()

        # views.py: DetailView.get_data
        api.trove.instance_get(IsA(http.HttpRequest), database.id)\
            .AndReturn(database)
        api.trove.flavor_list(IsA(http.HttpRequest)).\
            AndReturn(self.database_flavors.list())

        self.mox.ReplayAll()
        url = reverse('horizon:project:databases:resize_instance',
                      args=[database.id])

        res = self.client.get(url)
        self.assertTemplateUsed(res, 'project/databases/resize_instance.html')
        option = '<option value="%s">%s</option>'
        for flavor in self.database_flavors.list():
            if flavor.id == database.flavor['id']:
                self.assertNotContains(res, option % (flavor.id, flavor.name))
            else:
                self.assertContains(res, option % (flavor.id, flavor.name))

    @test.create_stubs(
        {api.trove: ('instance_get',
                     'flavor_list',
                     'instance_resize')})
    def test_resize_instance(self):
        database = self.databases.first()

        # views.py: DetailView.get_data
        api.trove.instance_get(IsA(http.HttpRequest), database.id)\
            .AndReturn(database)
        api.trove.flavor_list(IsA(http.HttpRequest)).\
            AndReturn(self.database_flavors.list())

        old_flavor = self.database_flavors.list()[0]
        new_flavor = self.database_flavors.list()[1]

        api.trove.instance_resize(IsA(http.HttpRequest),
                                  database.id,
                                  new_flavor.id).AndReturn(None)

        self.mox.ReplayAll()
        url = reverse('horizon:project:databases:resize_instance',
                      args=[database.id])
        post = {
            'instance_id': database.id,
            'old_flavor_name': old_flavor.name,
            'old_flavor_id': old_flavor.id,
            'new_flavor': new_flavor.id
        }
        res = self.client.post(url, post)
        self.assertNoFormErrors(res)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({
        api.trove: ('backup_list', 'configuration_list', 'datastore_flavors',
                    'datastore_list', 'datastore_version_list', 'flavor_list',
                    'instance_create', 'instance_get', 'instance_list_all'),
        dash_api.cinder: ('volume_type_list',),
        dash_api.neutron: ('network_list',),
        dash_api.nova: ('availability_zone_list',),
        policy: ('check',),
    })
    def test_create_replica_instance(self):
        policy.check((), IsA(http.HttpRequest)).MultipleTimes().AndReturn(True)
        api.trove.datastore_flavors(IsA(http.HttpRequest),
                                    IsA(six.string_types),
                                    IsA(six.string_types)).\
            MultipleTimes().AndReturn(self.flavors.list())

        api.trove.backup_list(IsA(http.HttpRequest)).AndReturn(
            self.database_backups.list())

        api.trove.instance_list_all(IsA(http.HttpRequest)).AndReturn(
            self.databases.list())

        api.trove.datastore_list(IsA(http.HttpRequest))\
            .AndReturn(self.datastores.list())

        api.trove.datastore_version_list(IsA(http.HttpRequest),
                                         IsA(str))\
            .MultipleTimes().AndReturn(self.datastore_versions.list())

        dash_api.cinder.volume_type_list(IsA(http.HttpRequest)).AndReturn([])

        dash_api.neutron.network_list(IsA(http.HttpRequest),
                                      tenant_id=self.tenant.id,
                                      shared=False).\
            AndReturn(self.networks.list()[:1])

        dash_api.neutron.network_list(IsA(http.HttpRequest),
                                      shared=True).\
            AndReturn(self.networks.list()[1:])

        nics = [{"net-id": self.networks.first().id, "v4-fixed-ip": ''}]

        dash_api.nova.availability_zone_list(IsA(http.HttpRequest)) \
            .AndReturn(self.availability_zones.list())

        api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))\
            .AndReturn(self.databases.first())

        datastore = 'mysql'
        datastore_version = '5.5'
        field_name = self._build_flavor_widget_name(datastore,
                                                    datastore_version)
        # Actual create database call
        api.trove.instance_create(
            IsA(http.HttpRequest),
            IsA(six.text_type),
            IsA(int),
            IsA(six.text_type),
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
            availability_zone=IsA(six.text_type)
        ).AndReturn(self.databases.first())

        self.mox.ReplayAll()
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
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({
        api.trove: ('promote_to_replica_source',),
        views.PromoteToReplicaSourceView: ('get_initial',)})
    def test_promote_replica_instance(self):
        replica_source = self.databases.first()
        replica = self.databases.list()[1]

        initial = {'instance_id': replica_source.id,
                   'replica': replica,
                   'replica_source': replica_source}
        views.PromoteToReplicaSourceView.get_initial().AndReturn(initial)

        api.trove.promote_to_replica_source(
            IsA(http.HttpRequest), replica_source.id)

        self.mox.ReplayAll()
        url = reverse('horizon:project:databases:promote_to_replica_source',
                      args=[replica_source.id])
        form = {
            'instance_id': replica_source.id
        }
        res = self.client.post(url, form)
        self.assertNoFormErrors(res)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({
        api.trove: ('promote_to_replica_source',),
        views.PromoteToReplicaSourceView: ('get_initial',)})
    def test_promote_replica_instance_exception(self):
        replica_source = self.databases.first()
        replica = self.databases.list()[1]

        initial = {'instance_id': replica_source.id,
                   'replica': replica,
                   'replica_source': replica_source}
        views.PromoteToReplicaSourceView.get_initial().AndReturn(initial)

        api.trove.promote_to_replica_source(
            IsA(http.HttpRequest), replica_source.id).\
            AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()
        url = reverse('horizon:project:databases:promote_to_replica_source',
                      args=[replica_source.id])
        form = {
            'instance_id': replica_source.id
        }
        res = self.client.post(url, form)
        self.assertEqual(res.status_code, 302)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({
        api.trove: ('flavor_list', 'instance_list',
                    'eject_replica_source',),
    })
    def test_eject_replica_source(self):
        databases = common.Paginated(self.databases.list())
        database = databases[2]

        api.trove.eject_replica_source(
            IsA(http.HttpRequest), database.id)

        databases = common.Paginated(self.databases.list())
        api.trove.instance_list(IsA(http.HttpRequest), marker=None)\
            .AndReturn(databases)
        api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndReturn(self.flavors.list())

        self.mox.ReplayAll()

        res = self.client.post(
            INDEX_URL,
            {'action': 'databases__eject_replica_source__%s' % database.id})

        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({
        api.trove: ('flavor_list', 'instance_list',
                    'eject_replica_source',),
    })
    def test_eject_replica_source_exception(self):
        databases = common.Paginated(self.databases.list())
        database = databases[2]

        api.trove.eject_replica_source(
            IsA(http.HttpRequest), database.id)\
            .AndRaise(self.exceptions.trove)

        databases = common.Paginated(self.databases.list())
        api.trove.instance_list(IsA(http.HttpRequest), marker=None)\
            .AndReturn(databases)
        api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndReturn(self.flavors.list())

        self.mox.ReplayAll()

        res = self.client.post(
            INDEX_URL,
            {'action': 'databases__eject_replica_source__%s' % database.id})

        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({
        api.trove: ('instance_list',)
    })
    def test_master_list_pagination(self):
        request = http.HttpRequest()

        first_part = common.Paginated(items=self.databases.list()[:1],
                                      next_marker='marker')
        second_part = common.Paginated(items=self.databases.list()[1:])

        api.trove.instance_list(request).AndReturn(first_part)
        (api.trove.instance_list(request, marker='marker')
         .AndReturn(second_part))
        api.trove.instance_list(request).AndReturn(first_part)

        self.mox.ReplayAll()

        advanced_page = create_instance.AdvancedAction(request, None)
        choices = advanced_page.populate_master_choices(request, None)
        self.assertTrue(len(choices) == len(self.databases.list()) + 1)

    def _build_datastore_display_text(self, datastore, datastore_version):
        return datastore + ' - ' + datastore_version

    def _build_flavor_widget_name(self, datastore, datastore_version):
        return binascii.hexlify(self._build_datastore_display_text(
            datastore, datastore_version))

    @test.create_stubs({
        api.trove: ('instance_get',
                    'configuration_list',
                    'instance_attach_configuration'),
    })
    def test_attach_configuration(self):
        database = self.databases.first()
        configuration = self.database_configurations.first()

        api.trove.instance_get(IsA(http.HttpRequest), IsA(unicode))\
            .AndReturn(database)

        api.trove.configuration_list(IsA(http.HttpRequest))\
            .AndReturn(self.database_configurations.list())

        api.trove.instance_attach_configuration(
            IsA(http.HttpRequest), database.id, configuration.id)\
            .AndReturn(None)

        self.mox.ReplayAll()
        url = reverse('horizon:project:databases:attach_config',
                      args=[database.id])
        form = {
            'instance_id': database.id,
            'configuration': configuration.id,
        }
        res = self.client.post(url, form)
        self.assertNoFormErrors(res)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({
        api.trove: ('instance_get',
                    'configuration_list',
                    'instance_attach_configuration'),
    })
    def test_attach_configuration_exception(self):
        database = self.databases.first()
        configuration = self.database_configurations.first()

        api.trove.instance_get(IsA(http.HttpRequest), IsA(unicode))\
            .AndReturn(database)

        api.trove.configuration_list(IsA(http.HttpRequest))\
            .AndReturn(self.database_configurations.list())

        api.trove.instance_attach_configuration(
            IsA(http.HttpRequest), database.id, configuration.id)\
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()
        url = reverse('horizon:project:databases:attach_config',
                      args=[database.id])
        form = {
            'instance_id': database.id,
            'configuration': configuration.id,
        }
        res = self.client.post(url, form)
        self.assertEqual(res.status_code, 302)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({
        api.trove: ('instance_list',
                    'flavor_list',
                    'instance_detach_configuration',),
    })
    def test_detach_configuration(self):
        databases = common.Paginated(self.databases.list())
        database = databases[2]

        api.trove.instance_list(IsA(http.HttpRequest), marker=None)\
            .AndReturn(databases)

        api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndReturn(self.flavors.list())

        api.trove.instance_detach_configuration(
            IsA(http.HttpRequest), database.id)\
            .AndReturn(None)

        self.mox.ReplayAll()

        res = self.client.post(
            INDEX_URL,
            {'action': 'databases__detach_configuration__%s' % database.id})

        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({
        api.trove: ('instance_list',
                    'flavor_list',
                    'instance_detach_configuration',),
    })
    def test_detach_configuration_exception(self):
        databases = common.Paginated(self.databases.list())
        database = databases[2]

        api.trove.instance_list(IsA(http.HttpRequest), marker=None)\
            .AndReturn(databases)

        api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndReturn(self.flavors.list())

        api.trove.instance_detach_configuration(
            IsA(http.HttpRequest), database.id)\
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()

        res = self.client.post(
            INDEX_URL,
            {'action': 'databases__detach_configuration__%s' % database.id})

        self.assertRedirectsNoFollow(res, INDEX_URL)
