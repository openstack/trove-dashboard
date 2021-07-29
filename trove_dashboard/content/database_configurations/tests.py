# Copyright 2015 Tesora Inc.
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
from unittest import mock

from django.urls import reverse
from oslo_serialization import jsonutils

from trove_dashboard import api
from trove_dashboard.content.database_configurations \
    import config_param_manager
from trove_dashboard.test import helpers as test

INDEX_URL = reverse('horizon:project:database_configurations:index')
CREATE_URL = reverse('horizon:project:database_configurations:create')
DETAIL_URL = 'horizon:project:database_configurations:detail'
ADD_URL = 'horizon:project:database_configurations:add'


class DatabaseConfigurationsTests(test.TestCase):
    @test.create_mocks({api.trove: ('configuration_list',)})
    def test_index(self):
        self.mock_configuration_list.return_value = (
            self.database_configurations.list())
        res = self.client.get(INDEX_URL)
        self.mock_configuration_list.assert_called_once_with(
            test.IsHttpRequest())
        self.assertTemplateUsed(res,
                                'project/database_configurations/index.html')

    @test.create_mocks({api.trove: ('configuration_list',)})
    def test_index_exception(self):
        self.mock_configuration_list.side_effect = self.exceptions.trove
        res = self.client.get(INDEX_URL)
        self.mock_configuration_list.assert_called_once_with(
            test.IsHttpRequest())
        self.assertTemplateUsed(
            res, 'project/database_configurations/index.html')
        self.assertEqual(res.status_code, 200)
        self.assertMessageCount(res, error=1)

    @test.create_mocks({
        api.trove: ('datastore_list', 'datastore_version_list')})
    def test_create_configuration(self):
        self.mock_datastore_list.return_value = self.datastores.list()
        self.mock_datastore_version_list.return_value = (
            self.datastore_versions.list())
        res = self.client.get(CREATE_URL)
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_datastore_version_list, 4,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.assertTemplateUsed(res,
                                'project/database_configurations/create.html')

    @test.create_mocks({api.trove: ('datastore_list',)})
    def test_create_configuration_exception_on_datastore(self):
        self.mock_datastore_list.side_effect = self.exceptions.trove
        toSuppress = ["trove_dashboard.content."
                      "database_configurations.forms", ]

        # Suppress expected log messages in the test output
        loggers = []
        for cls in toSuppress:
            logger = logging.getLogger(cls)
            loggers.append((logger, logger.getEffectiveLevel()))
            logger.setLevel(logging.CRITICAL)

        try:
            res = self.client.get(CREATE_URL)
            self.mock_datastore_list.assert_called_once_with(
                test.IsHttpRequest())
            self.assertEqual(res.status_code, 302)

        finally:
            # Restore the previous log levels
            for (log, level) in loggers:
                log.setLevel(level)

    @test.create_mocks({
        api.trove: ('datastore_list', 'datastore_version_list',
                    'configuration_create')})
    def _test_create_test_configuration(self, config_description=u''):
        self.mock_datastore_list.return_value = self.datastores.list()
        self.mock_datastore_version_list.return_value = (
            self.datastore_versions.list())

        self.mock_configuration_create.return_value = (
            self.database_configurations.first())

        name = u'config1'
        values = "{}"
        ds = self._get_test_datastore('mysql')
        dsv = self._get_test_datastore_version(ds.id, '5.5')
        config_datastore = ds.name
        config_datastore_version = dsv.name

        post = {
            'method': 'CreateConfigurationForm',
            'name': name,
            'description': config_description,
            'datastore': (config_datastore + ',' + config_datastore_version)}

        res = self.client.post(CREATE_URL, post)
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_datastore_version_list, 4,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.mock_configuration_create.assert_called_once_with(
            test.IsHttpRequest(),
            name,
            values,
            description=config_description,
            datastore=config_datastore,
            datastore_version=config_datastore_version)
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)

    def test_create_test_configuration(self):
        self._test_create_test_configuration(u'description of config1')

    def test_create_test_configuration_with_no_description(self):
        self._test_create_test_configuration()

    @test.create_mocks({
        api.trove: ('datastore_list', 'datastore_version_list',
                    'configuration_create')})
    def test_create_test_configuration_exception(self):
        self.mock_datastore_list.return_value = self.datastores.list()
        self.mock_datastore_version_list.return_value = (
            self.datastore_versions.list())

        self.mock_configuration_create.side_effect = self.exceptions.trove

        name = u'config1'
        values = "{}"
        config_description = u'description of config1'
        ds = self._get_test_datastore('mysql')
        dsv = self._get_test_datastore_version(ds.id, '5.5')
        config_datastore = ds.name
        config_datastore_version = dsv.name

        post = {'method': 'CreateConfigurationForm',
                'name': name,
                'description': config_description,
                'datastore': config_datastore + ',' + config_datastore_version}

        res = self.client.post(CREATE_URL, post)
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_datastore_version_list, 4,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.mock_configuration_create.assert_called_once_with(
            test.IsHttpRequest(),
            name,
            values,
            description=config_description,
            datastore=config_datastore,
            datastore_version=config_datastore_version)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({api.trove: ('configuration_get',
                                    'configuration_instances',)})
    def test_details_tab(self):
        config = self.database_configurations.first()
        self.mock_configuration_get.return_value = config
        details_url = self._get_url_with_arg(DETAIL_URL, config.id)
        url = details_url + '?tab=configuration_details__details'
        res = self.client.get(url)
        self.assertEqual(2, self.mock_configuration_get.call_count)
        self.assertTemplateUsed(res,
                                'project/database_configurations/details.html')

    @test.create_mocks({api.trove: ('configuration_get',)})
    def test_overview_tab_exception(self):
        config = self.database_configurations.first()
        self.mock_configuration_get.side_effect = self.exceptions.trove
        details_url = self._get_url_with_arg(DETAIL_URL, config.id)
        url = details_url + '?tab=configuration_details__overview'
        res = self.client.get(url)
        self.mock_configuration_get.assert_called_once_with(
            test.IsHttpRequest(), config.id)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({
        api.trove: ('configuration_parameters_list',),
        config_param_manager.ConfigParamManager:
            ('get_configuration', 'configuration_get',)})
    def test_add_parameter(self):
        config = self.database_configurations.first()
        self.mock_get_configuration.return_value = config

        self.mock_configuration_get.return_value = config
        ds = self._get_test_datastore('mysql')
        dsv = self._get_test_datastore_version(ds.id, '5.5')
        self.mock_configuration_parameters_list.return_value = (
            self.configuration_parameters.list())
        res = self.client.get(self._get_url_with_arg(ADD_URL, 'id'))
        self.mock_get_configuration.assert_called_once()
        self.mock_configuration_get.assert_called_once_with(
            test.IsHttpRequest())
        self.mock_configuration_parameters_list.assert_called_once_with(
            test.IsHttpRequest(),
            ds.name,
            dsv.name)
        self.assertTemplateUsed(
            res, 'project/database_configurations/add_parameter.html')

    @test.create_mocks({
        api.trove: ('configuration_parameters_list',),
        config_param_manager.ConfigParamManager:
            ('get_configuration', 'configuration_get',)})
    def test_add_parameter_exception_on_parameters(self):
        try:
            config = self.database_configurations.first()
            self.mock_get_configuration.return_value = config

            self.mock_configuration_get.return_value = config

            ds = self._get_test_datastore('mysql')
            dsv = self._get_test_datastore_version(ds.id, '5.5')
            self.mock_configuration_parameters_list.side_effect = (
                self.exceptions.trove)
            toSuppress = ["trove_dashboard.content."
                          "database_configurations.forms", ]

            # Suppress expected log messages in the test output
            loggers = []
            for cls in toSuppress:
                logger = logging.getLogger(cls)
                loggers.append((logger, logger.getEffectiveLevel()))
                logger.setLevel(logging.CRITICAL)

            try:
                res = self.client.get(
                    self._get_url_with_arg(ADD_URL, config.id))
                self.mock_get_configuration.assert_called_once()
                self.mock_configuration_get.assert_called_once_with(
                    test.IsHttpRequest())
                self.mock_configuration_parameters_list. \
                    assert_called_once_with(
                        test.IsHttpRequest(),
                        ds.name,
                        dsv.name
                    )
                self.assertEqual(res.status_code, 302)

            finally:
                # Restore the previous log levels
                for (log, level) in loggers:
                    log.setLevel(level)
        finally:
            config_param_manager.delete(config.id)

    @test.create_mocks(
        {
            api.trove:
                ('configuration_parameters_list', 'configuration_update',
                 'configuration_get'),
            config_param_manager.ConfigParamManager: ('add_param',)
        }
    )
    def test_add_new_parameter(self):
        config = self.database_configurations.first()

        try:
            self.mock_configuration_get.return_value = config

            ds = self._get_test_datastore('mysql')
            dsv = self._get_test_datastore_version(ds.id, '5.5')
            self.mock_configuration_parameters_list.return_value = (
                self.configuration_parameters.list())

            name = self.configuration_parameters.first().name
            value = 1
            config.values.update({name: value})

            self.mock_add_param.return_value = value

            post = {
                'method': 'AddParameterForm',
                'name': name,
                'value': value}

            res = self.client.post(self._get_url_with_arg(ADD_URL, config.id),
                                   post)

            self.assertEqual(2, self.mock_configuration_get.call_count)
            self.mock_configuration_parameters_list.assert_called_once_with(
                test.IsHttpRequest(),
                ds.name,
                dsv.name)
            self.mock_add_param.assert_called_once_with(name, value)
            self.mock_configuration_update.assert_called_once_with(
                test.IsHttpRequest(), config.id,
                jsonutils.dumps(config.values)
            )
            self.assertNoFormErrors(res)
            self.assertMessageCount(success=1)
        finally:
            config_param_manager.delete(config.id)

    @test.create_mocks({
        api.trove: ('configuration_get', 'configuration_parameters_list',),
        config_param_manager: ('get',)})
    def test_add_parameter_invalid_value(self):
        try:
            config = self.database_configurations.first()

            # setup the configuration parameter manager
            config_param_mgr = config_param_manager.ConfigParamManager(
                config.id)
            config_param_mgr.configuration = config
            config_param_mgr.original_configuration_values = \
                dict.copy(config.values)

            self.mock_get.return_value = config_param_mgr
            self.mock_configuration_parameters_list.return_value = (
                self.configuration_parameters.list())

            name = self.configuration_parameters.first().name
            value = "non-numeric"

            post = {
                'method': 'AddParameterForm',
                'name': name,
                'value': value}

            res = self.client.post(self._get_url_with_arg(ADD_URL, config.id),
                                   post)
            self.assert_mock_multiple_calls_with_same_arguments(
                self.mock_get, 2,
                mock.call(test.IsHttpRequest(), test.IsA(str)))
            self.assert_mock_multiple_calls_with_same_arguments(
                self.mock_configuration_parameters_list, 2,
                mock.call(test.IsHttpRequest(), test.IsA(str), test.IsA(str)))
            self.assertFormError(res, "form", 'value',
                                 ['Value must be a number.'])
        finally:
            config_param_manager.delete(config.id)

    @test.create_mocks({api.trove: ('configuration_instances',),
                        config_param_manager: ('get',)})
    def test_instances_tab(self):
        try:
            config = self.database_configurations.first()

            # setup the configuration parameter manager
            config_param_mgr = config_param_manager.ConfigParamManager(
                config.id)
            config_param_mgr.configuration = config
            config_param_mgr.original_configuration_values = \
                dict.copy(config.values)

            self.mock_get.return_value = config_param_mgr

            self.mock_configuration_instances.return_value = (
                self.configuration_instances.list())

            details_url = self._get_url_with_arg(DETAIL_URL, config.id)
            url = details_url + '?tab=configuration_details__instance'

            res = self.client.get(url)
            self.assert_mock_multiple_calls_with_same_arguments(
                self.mock_get, 2, mock.call(test.IsHttpRequest(), config.id))
            self.mock_configuration_instances.assert_called_once_with(
                test.IsHttpRequest(), config.id)
            table_data = res.context['instances_table'].data
            self.assertCountEqual(
                self.configuration_instances.list(), table_data)
            self.assertTemplateUsed(
                res, 'project/database_configurations/details.html')
        finally:
            config_param_manager.delete(config.id)

    @test.create_mocks({api.trove: ('configuration_instances',),
                        config_param_manager: ('get',)})
    def test_instances_tab_exception(self):
        try:
            config = self.database_configurations.first()

            # setup the configuration parameter manager
            config_param_mgr = config_param_manager.ConfigParamManager(
                config.id)
            config_param_mgr.configuration = config
            config_param_mgr.original_configuration_values = \
                dict.copy(config.values)

            self.mock_get.return_value = config_param_mgr

            self.mock_configuration_instances.side_effect = (
                self.exceptions.trove)

            details_url = self._get_url_with_arg(DETAIL_URL, config.id)
            url = details_url + '?tab=configuration_details__instance'

            res = self.client.get(url)
            self.assert_mock_multiple_calls_with_same_arguments(
                self.mock_get, 2, mock.call(test.IsHttpRequest(), config.id))
            self.mock_configuration_instances.assert_called_once_with(
                test.IsHttpRequest(), config.id)
            table_data = res.context['instances_table'].data
            self.assertNotEqual(len(self.configuration_instances.list()),
                                len(table_data))
            self.assertTemplateUsed(
                res, 'project/database_configurations/details.html')
        finally:
            config_param_manager.delete(config.id)

    def _get_url_with_arg(self, url, arg):
        return reverse(url, args=[arg])

    def _get_test_datastore(self, datastore_name):
        for ds in self.datastores.list():
            if ds.name == datastore_name:
                return ds
        return None

    def _get_test_datastore_version(self, datastore_id,
                                    datastore_version_name):
        for dsv in self.datastore_versions.list():
            if (dsv.datastore == datastore_id and
                    dsv.name == datastore_version_name):
                return dsv
        return None
