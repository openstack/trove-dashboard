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

import django
from django.core.urlresolvers import reverse
from django import http
import unittest

from mox3.mox import IsA  # noqa
import six

from horizon import exceptions
from openstack_dashboard import api as dash_api
from troveclient import common

from trove_dashboard import api
from trove_dashboard.content.databases import forms
from trove_dashboard.content.databases import tables
from trove_dashboard.content.databases import views
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
        last_record = databases[1]
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
        api.trove: ('flavor_list', 'backup_list',
                    'datastore_list', 'datastore_version_list',
                    'instance_list'),
        dash_api.cinder: ('volume_type_list',),
        dash_api.neutron: ('network_list',)})
    def test_launch_instance(self):
        api.trove.flavor_list(IsA(http.HttpRequest)).AndReturn(
            self.flavors.list())
        api.trove.backup_list(IsA(http.HttpRequest)).AndReturn(
            self.database_backups.list())
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

        toSuppress = ["openstack_dashboard.dashboards.project.databases."
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
        api.trove: ('flavor_list', 'backup_list', 'instance_create',
                    'datastore_list', 'datastore_version_list',
                    'instance_list'),
        dash_api.cinder: ('volume_type_list',),
        dash_api.neutron: ('network_list',)})
    def test_create_simple_instance(self):
        api.trove.flavor_list(IsA(http.HttpRequest)).AndReturn(
            self.flavors.list())

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

        # Actual create database call
        api.trove.instance_create(
            IsA(http.HttpRequest),
            IsA(six.text_type),
            IsA(int),
            IsA(six.text_type),
            databases=None,
            datastore=IsA(six.text_type),
            datastore_version=IsA(six.text_type),
            restore_point=None,
            replica_of=None,
            users=None,
            nics=nics,
            volume_type=None).AndReturn(self.databases.first())

        self.mox.ReplayAll()
        post = {
            'name': "MyDB",
            'volume': '1',
            'flavor': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'network': self.networks.first().id,
            'datastore': 'mysql,5.5',
            'volume_type': 'no_type'
        }

        res = self.client.post(LAUNCH_URL, post)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({
        api.trove: ('flavor_list', 'backup_list', 'instance_create',
                    'datastore_list', 'datastore_version_list',
                    'instance_list'),
        dash_api.cinder: ('volume_type_list',),
        dash_api.neutron: ('network_list',)})
    def test_create_simple_instance_exception(self):
        trove_exception = self.exceptions.nova
        api.trove.flavor_list(IsA(http.HttpRequest)).AndReturn(
            self.flavors.list())

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

        # Actual create database call
        api.trove.instance_create(
            IsA(http.HttpRequest),
            IsA(six.text_type),
            IsA(int),
            IsA(six.text_type),
            databases=None,
            datastore=IsA(six.text_type),
            datastore_version=IsA(six.text_type),
            restore_point=None,
            replica_of=None,
            users=None,
            nics=nics,
            volume_type=None).AndRaise(trove_exception)

        self.mox.ReplayAll()
        post = {
            'name': "MyDB",
            'volume': '1',
            'flavor': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'network': self.networks.first().id,
            'datastore': 'mysql,5.5',
            'volume_type': 'no_type'
        }

        res = self.client.post(LAUNCH_URL, post)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs(
        {api.trove: ('instance_get', 'flavor_get',)})
    def _test_details(self, database, with_designate=False):
        api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))\
            .AndReturn(database)
        api.trove.flavor_get(IsA(http.HttpRequest), IsA(str))\
            .AndReturn(self.flavors.first())

        self.mox.ReplayAll()
        res = self.client.get(DETAILS_URL)
        self.assertTemplateUsed(res, 'horizon/common/_detail.html')
        if with_designate:
            self.assertContains(res, database.hostname)
        else:
            self.assertContains(res, database.ip[0])

    def test_details_with_ip(self):
        database = self.databases.first()
        self._test_details(database, with_designate=False)

    def test_details_with_hostname(self):
        database = self.databases.list()[1]
        self._test_details(database, with_designate=True)

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

    @test.create_stubs({api.trove: ('root_enable',)})
    def test_reset_root(self):
        api.trove.root_enable(IsA(http.HttpRequest), [u'id']) \
            .AndReturn(("root", "newpassword"))

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:manage_root',
                      args=['id'])
        form_data = {"action": "manage_root__reset_root_action__%s" % 'id'}
        req = self.factory.post(url, form_data)

        kwargs = {'instance_id': 'id'}

        enable_root_info_list = []
        enable_root_info = views.EnableRootInfo(
            'id', 'inst1', True, 'password')
        enable_root_info_list.append(enable_root_info)

        table = tables.ManageRootTable(req, enable_root_info_list, **kwargs)
        table.maybe_handle()

        self.assertEqual(table.data[0].enabled, True)
        self.assertEqual(table.data[0].password, "newpassword")

    @test.create_stubs({api.trove: ('root_enable',)})
    def test_reset_root_exception(self):
        api.trove.root_enable(IsA(http.HttpRequest), [u'id']) \
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:manage_root',
                      args=['id'])
        form_data = {"action": "manage_root__reset_root_action__%s" % 'id'}
        req = self.factory.post(url, form_data)

        kwargs = {'instance_id': 'id'}

        enable_root_info_list = []
        enable_root_info = views.EnableRootInfo(
            'id', 'inst1', True, 'password')
        enable_root_info_list.append(enable_root_info)

        table = tables.ManageRootTable(req, enable_root_info_list, **kwargs)
        table.maybe_handle()

        self.assertEqual(table.data[0].enabled, True)
        self.assertNotEqual(table.data[0].password, "newpassword")

    @test.create_stubs(
        {api.trove: ('instance_get', 'flavor_get', 'users_list',
                     'user_list_access', 'user_delete')})
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
                             database_id).AndReturn([user])
        api.trove.user_list_access(IsA(http.HttpRequest),
                                   database_id,
                                   user_id).AndReturn([user_db])

        # tables.py: DeleteUser.delete
        api.trove.user_delete(IsA(http.HttpRequest),
                              database_id,
                              user_id).AndReturn(None)

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
            IsA(http.HttpRequest), database.id, user.name, host=u'',
            new_name=u'new_name', new_password=u'new_password',
            new_host=u'127.0.0.1')

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:edit_user',
                      args=[database.id, user.name])
        post = {
            'method': 'EditUserForm',
            'instance_id': database.id,
            'user_name': user.name,
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
            IsA(http.HttpRequest), database.id, user.name, host=u'',
            new_name=u'new_name', new_password=u'new_password',
            new_host=u'127.0.0.1') \
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:edit_user',
                      args=[database.id, user.name])
        post = {
            'method': 'EditUserForm',
            'instance_id': database.id,
            'user_name': user.name,
            'new_name': 'new_name',
            'new_password': 'new_password',
            'new_host': '127.0.0.1'}

        res = self.client.post(url, post)
        self.assertEqual(res.status_code, 302)

    def test_edit_user_no_values(self):
        database = self.databases.first()
        user = self.users.first()

        url = reverse('horizon:project:databases:edit_user',
                      args=[database.id, user.name])
        post = {
            'method': 'EditUserForm',
            'instance_id': database.id,
            'user_name': user.name}
        res = self.client.post(url, post)

        msg = forms.EditUserForm.validation_error_message
        self.assertFormError(res, "form", None, [msg])

    @test.create_stubs({api.trove: ('database_list', 'user_list_access')})
    def test_access_detail_get(self):
        api.trove.database_list(IsA(http.HttpRequest), u'id') \
            .AndReturn(self.databases.list())

        api.trove.user_list_access(IsA(http.HttpRequest), u'id', u'name') \
            .AndReturn(self.databases.list())

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:access_detail',
                      args=['id', 'name'])
        res = self.client.get(url)
        self.assertTemplateUsed(
            res, 'project/databases/access_detail.html')

    @test.create_stubs({api.trove: ('database_list', 'user_list_access')})
    def test_access_detail_get_exception(self):
        api.trove.database_list(IsA(http.HttpRequest), u'id') \
            .AndReturn(self.databases.list())

        api.trove.user_list_access(IsA(http.HttpRequest), u'id', u'name') \
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:access_detail',
                      args=['id', 'name'])
        res = self.client.get(url)
        self.assertRedirectsNoFollow(res, DETAILS_URL)

    @test.create_stubs({api.trove: ('user_grant_access',)})
    def test_detail_grant_access(self):
        api.trove.user_grant_access(
            IsA(http.HttpRequest), u'id', u'name', [u'db1'], None)

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:access_detail',
                      args=['id', 'name'])
        form_data = {"action": "access__grant_access__%s" % 'db1'}
        req = self.factory.post(url, form_data)

        kwargs = {'instance_id': 'id', 'user_name': 'name'}

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
            IsA(http.HttpRequest), u'id', u'name', [u'db1'], None) \
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:access_detail',
                      args=['id', 'name'])
        form_data = {"action": "access__grant_access__%s" % 'db1'}
        req = self.factory.post(url, form_data)

        kwargs = {'instance_id': 'id', 'user_name': 'name'}

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
            IsA(http.HttpRequest), u'id', u'name', u'db1', None)
        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:access_detail',
                      args=['id', 'name'])
        form_data = {"action": "access__revoke_access__%s" % 'db1'}
        req = self.factory.post(url, form_data)

        kwargs = {'instance_id': 'id', 'user_name': 'name'}

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
            IsA(http.HttpRequest), u'id', u'name', u'db1', None) \
            .AndRaise(self.exceptions.trove)
        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:access_detail',
                      args=['id', 'name'])
        form_data = {"action": "access__revoke_access__%s" % 'db1'}
        req = self.factory.post(url, form_data)

        kwargs = {'instance_id': 'id', 'user_name': 'name'}

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
        api.trove: ('flavor_list', 'backup_list', 'instance_create',
                    'datastore_list', 'datastore_version_list',
                    'instance_list', 'instance_get'),
        dash_api.cinder: ('volume_type_list',),
        dash_api.neutron: ('network_list',)})
    def test_create_replica_instance(self):
        api.trove.flavor_list(IsA(http.HttpRequest)).AndReturn(
            self.flavors.list())

        api.trove.backup_list(IsA(http.HttpRequest)).AndReturn(
            self.database_backups.list())

        api.trove.instance_list(IsA(http.HttpRequest)).AndReturn(
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

        api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))\
            .AndReturn(self.databases.first())

        # Actual create database call
        api.trove.instance_create(
            IsA(http.HttpRequest),
            IsA(six.text_type),
            IsA(int),
            IsA(six.text_type),
            databases=None,
            datastore=IsA(six.text_type),
            datastore_version=IsA(six.text_type),
            restore_point=None,
            replica_of=self.databases.first().id,
            users=None,
            nics=nics,
            volume_type=None).AndReturn(self.databases.first())

        self.mox.ReplayAll()
        post = {
            'name': "MyDB",
            'volume': '1',
            'flavor': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'network': self.networks.first().id,
            'datastore': 'mysql,5.5',
            'initial_state': 'master',
            'master': self.databases.first().id,
            'volume_type': 'no_type'
        }

        res = self.client.post(LAUNCH_URL, post)
        self.assertRedirectsNoFollow(res, INDEX_URL)
