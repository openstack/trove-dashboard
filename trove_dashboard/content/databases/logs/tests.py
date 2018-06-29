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

import logging

from django import http
from django.urls import reverse

import mock
import six

from trove_dashboard import api
from trove_dashboard.test import helpers as test

from swiftclient import client as swift_client

LINES = 50


class LogsTests(test.TestCase):
    @test.create_mocks({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'root_show')})
    def test_log_tab(self):
        database = self.databases.first()
        database_id = database.id

        self.mock_instance_get.return_value = database
        self.mock_log_list.return_value = self.logs.list()
        self.mock_flavor_get.return_value = self.flavors.first()
        self.mock_root_show.return_value = self.database_user_roots.first()

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        res = self.client.get(url)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(six.text_type))
        self.mock_log_list.assert_called_once_with(
            test.IsHttpRequest(), database_id)
        self.mock_flavor_get.assert_called_once_with(
            test.IsHttpRequest(), database.flavor["id"])
        self.mock_root_show.assert_called_once_with(
            test.IsHttpRequest(), database.id)
        table_data = res.context['logs_table'].data
        self.assertItemsEqual(self.logs.list(), table_data)
        self.assertTemplateUsed(
            res, 'horizon/common/_detail_table.html')

    @test.create_mocks({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'root_show')})
    def test_log_tab_exception(self):
        database = self.databases.first()
        database_id = database.id

        self.mock_instance_get.return_value = database
        self.mock_log_list.side_effect = self.exceptions.trove
        self.mock_flavor_get.return_value = self.flavors.first()
        self.mock_root_show.return_value = self.database_user_roots.first()

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'

        toSuppress = ["trove_dashboard.content.databases.tabs"]

        loggers = []
        for cls in toSuppress:
            logger = logging.getLogger(cls)
            loggers.append((logger, logger.getEffectiveLevel()))
            logger.setLevel(logging.CRITICAL)

        try:
            res = self.client.get(url)
            self.mock_instance_get.assert_called_once_with(
                test.IsHttpRequest(), test.IsA(six.text_type))
            self.mock_log_list.assert_called_once_with(
                test.IsHttpRequest(), database_id)
            self.mock_flavor_get.assert_called_once_with(
                test.IsHttpRequest(), database.flavor["id"])
            self.mock_root_show.assert_called_once_with(
                test.IsHttpRequest(), database.id)
            table_data = res.context['logs_table'].data
            self.assertNotEqual(len(self.logs.list()), len(table_data))
            self.assertTemplateUsed(
                res, 'horizon/common/_detail_table.html')
        finally:
            # Restore the previous log levels
            for (log, level) in loggers:
                log.setLevel(level)

    @test.create_mocks({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_publish',)
    })
    def test_log_publish(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.first()
        self.mock_instance_get.return_value = database
        self.mock_log_list.return_value = self.logs.list()
        self.mock_flavor_get.return_value = self.flavors.first()
        self.mock_log_publish.return_value = None

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('publish', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(six.text_type))
        self.mock_log_list.assert_called_once_with(
            test.IsHttpRequest(), database_id)
        self.mock_flavor_get.assert_called_once_with(
            test.IsHttpRequest(), database.flavor["id"])
        self.mock_log_publish.assert_called_once_with(
            test.IsHttpRequest(), database_id, log.name)
        self.assertRedirectsNoFollow(res, url)

    @test.create_mocks({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_publish',)
    })
    def test_log_publish_exception(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.first()
        self.mock_instance_get.return_value = database
        self.mock_log_list.return_value = self.logs.list()
        self.mock_flavor_get.return_value = self.flavors.first()
        self.mock_log_publish.side_effect = self.exceptions.trove

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('publish', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(six.text_type))
        self.mock_log_list.assert_called_once_with(
            test.IsHttpRequest(), database_id)
        self.mock_flavor_get.assert_called_once_with(
            test.IsHttpRequest(), database.flavor["id"])
        self.mock_log_publish.assert_called_once_with(
            test.IsHttpRequest(), database_id, log.name)
        self.assertRedirectsNoFollow(res, url)

    @test.create_mocks({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_enable',)
    })
    def test_log_enable(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.first()
        self.mock_instance_get.return_value = database
        self.mock_log_list.return_value = self.logs.list()
        self.mock_flavor_get.return_value = self.flavors.first()
        self.mock_log_enable.return_value = None

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('enable', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(six.text_type))
        self.mock_log_list.assert_called_once_with(
            test.IsHttpRequest(), database_id)
        self.mock_flavor_get.assert_called_once_with(
            test.IsHttpRequest(), database.flavor["id"])
        self.mock_log_enable.assert_called_once_with(
            test.IsHttpRequest(), database_id, log.name)
        self.assertRedirectsNoFollow(res, url)

    @test.create_mocks({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_enable',)
    })
    def test_log_enable_exception(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.first()
        self.mock_instance_get.return_value = database
        self.mock_log_list.return_value = self.logs.list()
        self.mock_flavor_get.return_value = self.flavors.first()
        self.mock_log_enable.side_effect = self.exceptions.trove

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('enable', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(six.text_type))
        self.mock_log_list.assert_called_once_with(
            test.IsHttpRequest(), database_id)
        self.mock_flavor_get.assert_called_once_with(
            test.IsHttpRequest(), database.flavor["id"])
        self.mock_log_enable.assert_called_once_with(
            test.IsHttpRequest(), database_id, log.name)
        self.assertRedirectsNoFollow(res, url)

    @test.create_mocks({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_discard',)
    })
    def test_log_discard(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.first()
        self.mock_instance_get.return_value = database
        self.mock_log_list.return_value = self.logs.list()
        self.mock_flavor_get.return_value = self.flavors.first()
        self.mock_log_discard.return_value = None

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('discard', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(six.text_type))
        self.mock_log_list.assert_called_once_with(
            test.IsHttpRequest(), database_id)
        self.mock_flavor_get.assert_called_once_with(
            test.IsHttpRequest(), database.flavor["id"])
        self.mock_log_discard.assert_called_once_with(
            test.IsHttpRequest(), database_id, log.name)
        self.assertRedirectsNoFollow(res, url)

    @test.create_mocks({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_discard',)
    })
    def test_log_discard_exception(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.first()
        self.mock_instance_get.return_value = database
        self.mock_log_list.return_value = self.logs.list()
        self.mock_flavor_get.return_value = self.flavors.first()
        self.mock_log_discard.side_effect = self.exceptions.trove

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('discard', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(six.text_type))
        self.mock_log_list.assert_called_once_with(
            test.IsHttpRequest(), database_id)
        self.mock_flavor_get.assert_called_once_with(
            test.IsHttpRequest(), database.flavor["id"])
        self.mock_log_discard.assert_called_once_with(
            test.IsHttpRequest(), database_id, log.name)
        self.assertRedirectsNoFollow(res, url)

    @test.create_mocks({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_disable',)
    })
    def test_log_disable(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.list()[3]
        self.mock_instance_get.return_value = database
        self.mock_log_list.return_value = self.logs.list()
        self.mock_flavor_get.return_value = self.flavors.first()
        self.mock_log_disable.return_value = None

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('disable', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(six.text_type))
        self.mock_log_list.assert_called_once_with(
            test.IsHttpRequest(), database_id)
        self.mock_flavor_get.assert_called_once_with(
            test.IsHttpRequest(), database.flavor["id"])
        self.mock_log_disable.assert_called_once_with(
            test.IsHttpRequest(), database_id, log.name)
        self.assertRedirectsNoFollow(res, url)

    @test.create_mocks({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_disable',)
    })
    def test_log_disable_exception(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.list()[3]
        self.mock_instance_get.return_value = database
        self.mock_log_list.return_value = self.logs.list()
        self.mock_flavor_get.return_value = self.flavors.first()
        self.mock_log_disable.side_effect = self.exceptions.trove

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('disable', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.mock_instance_get.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(six.text_type))
        self.mock_log_list.assert_called_once_with(
            test.IsHttpRequest(), database_id)
        self.mock_flavor_get.assert_called_once_with(
            test.IsHttpRequest(), database.flavor["id"])
        self.mock_log_disable.assert_called_once_with(
            test.IsHttpRequest(), database_id, log.name)
        self.assertRedirectsNoFollow(res, url)

    @test.create_mocks({
        api.trove: ('log_tail',),
        swift_client: ('Connection',),
    })
    def test_view_log(self):
        CONSOLE_OUTPUT = 'superspecialuniquetext'
        self.mock_log_tail.return_value = lambda: [CONSOLE_OUTPUT]

        url = reverse('horizon:project:databases:logs:log_contents',
                      args=('id', 'guest.log'))
        res = self.client.get(url)

        self.mock_Connection.assert_called_once_with(
            None,
            mock.ANY,
            None,
            preauthtoken=mock.ANY,
            preauthurl=mock.ANY,
            cacert=None,
            insecure=False,
            auth_version="2.0")
        self.mock_log_tail.assert_called_once_with(
            test.IsHttpRequest(),
            test.IsA(six.string_types),
            'guest.log',
            False,
            LINES,
            self.mock_Connection())
        self.assertNoMessages()
        self.assertIsInstance(res, http.HttpResponse)
        self.assertContains(res, CONSOLE_OUTPUT)

    @test.create_mocks({
        api.trove: ('log_tail',),
        swift_client: ('Connection',),
    })
    def test_view_log_exception(self):
        self.mock_log_tail.side_effect = self.exceptions.trove

        url = reverse('horizon:project:databases:logs:log_contents',
                      args=('id', 'guest.log'))
        res = self.client.get(url)

        self.mock_Connection.assert_called_once_with(
            None,
            mock.ANY,
            None,
            preauthtoken=mock.ANY,
            preauthurl=mock.ANY,
            cacert=None,
            insecure=False,
            auth_version="2.0")
        self.mock_log_tail.assert_called_once_with(
            test.IsHttpRequest(),
            test.IsA(six.string_types),
            'guest.log',
            False,
            LINES,
            self.mock_Connection())
        self.assertContains(res, "Unable to load")
