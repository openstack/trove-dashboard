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

from django.core.urlresolvers import reverse
from django import http

from mox3 import mox
from mox3.mox import IsA  # noqa
import six

from trove_dashboard import api
from trove_dashboard.test import helpers as test

from swiftclient import client as swift_client

LINES = 50


class LogsTests(test.TestCase):
    def stub_swiftclient(self, expected_calls=1):
        if not hasattr(self, "swiftclient"):
            self.mox.StubOutWithMock(swift_client, 'Connection')
            self.swiftclient = self.mox.CreateMock(swift_client.Connection)
            while expected_calls:
                (swift_client.Connection(None,
                                         mox.IgnoreArg(),
                                         None,
                                         preauthtoken=mox.IgnoreArg(),
                                         preauthurl=mox.IgnoreArg(),
                                         cacert=None,
                                         insecure=False,
                                         auth_version="2.0")
                 .AndReturn(self.swiftclient))
                expected_calls -= 1
        return self.swiftclient

    @test.create_stubs({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'root_show')})
    def test_log_tab(self):
        database = self.databases.first()
        database_id = database.id

        (api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))
            .AndReturn(database))
        (api.trove.log_list(IsA(http.HttpRequest), database_id)
            .AndReturn(self.logs.list()))
        (api.trove.flavor_get(IsA(http.HttpRequest), database.flavor["id"])
            .AndReturn(self.flavors.first()))
        (api.trove.root_show(IsA(http.HttpRequest), database.id)
            .AndReturn(self.database_user_roots.first()))

        self.mox.ReplayAll()

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        res = self.client.get(url)
        table_data = res.context['logs_table'].data
        self.assertItemsEqual(self.logs.list(), table_data)
        self.assertTemplateUsed(
            res, 'horizon/common/_detail_table.html')

    @test.create_stubs({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'root_show')})
    def test_log_tab_exception(self):
        database = self.databases.first()
        database_id = database.id

        (api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))
            .AndReturn(database))
        (api.trove.log_list(IsA(http.HttpRequest), database_id)
            .AndRaise(self.exceptions.trove))
        (api.trove.flavor_get(IsA(http.HttpRequest), database.flavor["id"])
            .AndReturn(self.flavors.first()))
        (api.trove.root_show(IsA(http.HttpRequest), database.id)
            .AndReturn(self.database_user_roots.first()))

        self.mox.ReplayAll()

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
            table_data = res.context['logs_table'].data
            self.assertNotEqual(len(self.logs.list()), len(table_data))
            self.assertTemplateUsed(
                res, 'horizon/common/_detail_table.html')
        finally:
            # Restore the previous log levels
            for (log, level) in loggers:
                log.setLevel(level)

    @test.create_stubs({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_publish',)
    })
    def test_log_publish(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.first()
        (api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))
            .AndReturn(database))
        (api.trove.log_list(IsA(http.HttpRequest), database_id)
            .AndReturn(self.logs.list()))
        (api.trove.flavor_get(IsA(http.HttpRequest), database.flavor["id"])
            .AndReturn(self.flavors.first()))
        (api.trove.log_publish(IsA(http.HttpRequest), database_id, log.name)
            .AndReturn(None))

        self.mox.ReplayAll()

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('publish', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.assertRedirectsNoFollow(res, url)

    @test.create_stubs({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_publish',)
    })
    def test_log_publish_exception(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.first()
        (api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))
            .AndReturn(database))
        (api.trove.log_list(IsA(http.HttpRequest), database_id)
            .AndReturn(self.logs.list()))
        (api.trove.flavor_get(IsA(http.HttpRequest), database.flavor["id"])
            .AndReturn(self.flavors.first()))
        (api.trove.log_publish(IsA(http.HttpRequest), database_id, log.name)
            .AndRaise(self.exceptions.trove))

        self.mox.ReplayAll()

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('publish', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.assertRedirectsNoFollow(res, url)

    @test.create_stubs({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_enable',)
    })
    def test_log_enable(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.first()
        (api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))
            .AndReturn(database))
        (api.trove.log_list(IsA(http.HttpRequest), database_id)
            .AndReturn(self.logs.list()))
        (api.trove.flavor_get(IsA(http.HttpRequest), database.flavor["id"])
            .AndReturn(self.flavors.first()))
        (api.trove.log_enable(IsA(http.HttpRequest), database_id, log.name)
            .AndReturn(None))

        self.mox.ReplayAll()

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('enable', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.assertRedirectsNoFollow(res, url)

    @test.create_stubs({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_enable',)
    })
    def test_log_enable_exception(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.first()
        (api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))
            .AndReturn(database))
        (api.trove.log_list(IsA(http.HttpRequest), database_id)
            .AndReturn(self.logs.list()))
        (api.trove.flavor_get(IsA(http.HttpRequest), database.flavor["id"])
            .AndReturn(self.flavors.first()))
        (api.trove.log_enable(IsA(http.HttpRequest), database_id, log.name)
            .AndRaise(self.exceptions.trove))

        self.mox.ReplayAll()

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('enable', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.assertRedirectsNoFollow(res, url)

    @test.create_stubs({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_discard',)
    })
    def test_log_discard(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.first()
        (api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))
            .AndReturn(database))
        (api.trove.log_list(IsA(http.HttpRequest), database_id)
            .AndReturn(self.logs.list()))
        (api.trove.flavor_get(IsA(http.HttpRequest), database.flavor["id"])
            .AndReturn(self.flavors.first()))
        (api.trove.log_discard(IsA(http.HttpRequest), database_id, log.name)
            .AndReturn(None))

        self.mox.ReplayAll()

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('discard', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.assertRedirectsNoFollow(res, url)

    @test.create_stubs({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_discard',)
    })
    def test_log_discard_exception(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.first()
        (api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))
            .AndReturn(database))
        (api.trove.log_list(IsA(http.HttpRequest), database_id)
            .AndReturn(self.logs.list()))
        (api.trove.flavor_get(IsA(http.HttpRequest), database.flavor["id"])
            .AndReturn(self.flavors.first()))
        (api.trove.log_discard(IsA(http.HttpRequest), database_id, log.name)
            .AndRaise(self.exceptions.trove))

        self.mox.ReplayAll()

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('discard', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.assertRedirectsNoFollow(res, url)

    @test.create_stubs({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_disable',)
    })
    def test_log_disable(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.list()[3]
        (api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))
            .AndReturn(database))
        (api.trove.log_list(IsA(http.HttpRequest), database_id)
            .AndReturn(self.logs.list()))
        (api.trove.flavor_get(IsA(http.HttpRequest), database.flavor["id"])
            .AndReturn(self.flavors.first()))
        (api.trove.log_disable(IsA(http.HttpRequest), database_id, log.name)
            .AndReturn(None))

        self.mox.ReplayAll()

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('disable', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.assertRedirectsNoFollow(res, url)

    @test.create_stubs({
        api.trove: ('flavor_get', 'instance_get', 'log_list', 'log_disable',)
    })
    def test_log_disable_exception(self):
        database = self.databases.first()
        database_id = database.id
        log = self.logs.list()[3]
        (api.trove.instance_get(IsA(http.HttpRequest), IsA(six.text_type))
            .AndReturn(database))
        (api.trove.log_list(IsA(http.HttpRequest), database_id)
            .AndReturn(self.logs.list()))
        (api.trove.flavor_get(IsA(http.HttpRequest), database.flavor["id"])
            .AndReturn(self.flavors.first()))
        (api.trove.log_disable(IsA(http.HttpRequest), database_id, log.name)
            .AndRaise(self.exceptions.trove))

        self.mox.ReplayAll()

        detail_url = reverse('horizon:project:databases:detail',
                             args=[database_id])
        url = detail_url + '?tab=instance_details__logs_tab'
        action_string = u"logs__%s_log__%s" % ('disable', log.name)
        form_data = {'action': action_string}
        res = self.client.post(url, form_data)
        self.assertRedirectsNoFollow(res, url)

    @test.create_stubs({api.trove: ('log_tail',)})
    def test_view_log(self):
        CONSOLE_OUTPUT = 'superspecialuniquetext'
        (api.trove.log_tail(IsA(http.HttpRequest),
                            IsA(six.string_types),
                            'guest.log',
                            False,
                            LINES,
                            self.stub_swiftclient())
         .AndReturn(lambda: [CONSOLE_OUTPUT]))

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:logs:log_contents',
                      args=('id', 'guest.log'))
        res = self.client.get(url)

        self.assertNoMessages()
        self.assertIsInstance(res, http.HttpResponse)
        self.assertContains(res, CONSOLE_OUTPUT)

    @test.create_stubs({api.trove: ('log_tail',)})
    def test_view_log_exception(self):
        (api.trove.log_tail(IsA(http.HttpRequest),
                            IsA(six.string_types),
                            'guest.log',
                            False,
                            LINES,
                            self.stub_swiftclient())
         .AndRaise(self.exceptions.trove))

        self.mox.ReplayAll()

        url = reverse('horizon:project:databases:logs:log_contents',
                      args=('id', 'guest.log'))
        res = self.client.get(url)

        self.assertContains(res, "Unable to load")
