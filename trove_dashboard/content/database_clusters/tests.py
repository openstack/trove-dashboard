# Copyright (c) 2014 eBay Software Foundation
# Copyright 2015 HP Software, LLC
# All Rights Reserved.
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

from django.urls import reverse

import mock

from openstack_dashboard import api
from troveclient import common

from trove_dashboard import api as trove_api
from trove_dashboard.content.database_clusters \
    import cluster_manager
from trove_dashboard.content.database_clusters import tables
from trove_dashboard.test import helpers as test
from trove_dashboard.utils import common as common_utils

INDEX_URL = reverse('horizon:project:database_clusters:index')
LAUNCH_URL = reverse('horizon:project:database_clusters:launch')
DETAILS_URL = reverse('horizon:project:database_clusters:detail', args=['id'])
RESET_PASSWORD_VIEWNAME = 'horizon:project:database_clusters:reset_password'


class ClustersTests(test.TestCase):
    @test.create_mocks({trove_api.trove: ('cluster_list',
                                          'flavor_list')})
    def test_index(self):
        clusters = common.Paginated(self.trove_clusters.list())
        self.mock_cluster_list.return_value = clusters
        self.mock_flavor_list.return_value = self.flavors.list()

        res = self.client.get(INDEX_URL)
        self.mock_cluster_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, 'project/database_clusters/index.html')

    @test.create_mocks({trove_api.trove: ('cluster_list',
                                          'flavor_list')})
    def test_index_flavor_exception(self):
        clusters = common.Paginated(self.trove_clusters.list())
        self.mock_cluster_list.return_value = clusters
        self.mock_flavor_list.side_effect = self.exceptions.trove

        res = self.client.get(INDEX_URL)
        self.mock_cluster_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, 'project/database_clusters/index.html')
        self.assertMessageCount(res, error=1)

    @test.create_mocks({trove_api.trove: ('cluster_list',)})
    def test_index_list_exception(self):
        self.mock_cluster_list.side_effect = self.exceptions.trove

        res = self.client.get(INDEX_URL)
        self.mock_cluster_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        self.assertTemplateUsed(res, 'project/database_clusters/index.html')
        self.assertMessageCount(res, error=1)

    @test.create_mocks({trove_api.trove: ('cluster_list',
                                          'flavor_list')})
    def test_index_pagination(self):
        clusters = self.trove_clusters.list()
        last_record = clusters[1]
        clusters = common.Paginated(clusters, next_marker="foo")
        self.mock_cluster_list.return_value = clusters
        self.mock_flavor_list.return_value = self.flavors.list()

        res = self.client.get(INDEX_URL)
        self.mock_cluster_list.assert_called_once_with(
            test.IsHttpRequest(), marker=None)
        self.mock_flavor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, 'project/database_clusters/index.html')
        self.assertContains(
            res, 'marker=' + last_record.id)

    @test.create_mocks({trove_api.trove: ('datastore_flavors',
                                          'datastore_list',
                                          'datastore_version_list'),
                        api.base: ['is_service_enabled']})
    def test_launch_cluster(self):
        self.mock_is_service_enabled.return_value = False
        self.mock_datastore_flavors.return_value = self.flavors.list()

        filtered_datastores = self._get_filtered_datastores('mongodb')
        self.mock_datastore_list.return_value = filtered_datastores
        self.mock_datastore_version_list.return_value = (
            self._get_filtered_datastore_versions(filtered_datastores))

        res = self.client.get(LAUNCH_URL)
        self.mock_is_service_enabled.assert_called_once_with(
            test.IsHttpRequest(), 'network')
        self.mock_datastore_flavors.assert_called_once_with(
            test.IsHttpRequest(), 'mongodb', '2.6')
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_datastore_version_list.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.assertTemplateUsed(res, 'project/database_clusters/launch.html')

    def test_launch_cluster_mongo_fields(self):
        datastore = 'mongodb'
        datastore_version = '2.6'
        fields = self.launch_cluster_fields_setup(datastore,
                                                  datastore_version)
        field_name = self._build_flavor_widget_name(datastore,
                                                    datastore_version)

        self.assertTrue(self._contains_datastore_in_attribute(
            fields[field_name], field_name))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['num_instances'], field_name))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['num_shards'], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['root_password'], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_instances_vertica'], field_name))

    def test_launch_cluster_redis_fields(self):
        datastore = 'redis'
        datastore_version = '3.0'
        fields = self.launch_cluster_fields_setup(datastore,
                                                  datastore_version)
        field_name = self._build_flavor_widget_name(datastore,
                                                    datastore_version)

        self.assertTrue(self._contains_datastore_in_attribute(
            fields[field_name], field_name))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['num_instances'], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_shards'], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['root_password'], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_instances_vertica'], field_name))

    def test_launch_cluster_vertica_fields(self):
        datastore = 'vertica'
        datastore_version = '7.1'
        fields = self.launch_cluster_fields_setup(datastore,
                                                  datastore_version)
        field_name = self._build_flavor_widget_name(datastore,
                                                    datastore_version)

        self.assertTrue(self._contains_datastore_in_attribute(
            fields[field_name], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_instances'], field_name))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_shards'], field_name))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['root_password'], field_name))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['num_instances_vertica'], field_name))

    @test.create_mocks({trove_api.trove: ('datastore_flavors',
                                          'datastore_list',
                                          'datastore_version_list'),
                        api.base: ['is_service_enabled']})
    def launch_cluster_fields_setup(self, datastore, datastore_version):
        self.mock_is_service_enabled.return_value = False
        self.mock_datastore_flavors.return_value = self.flavors.list()

        filtered_datastores = self._get_filtered_datastores(datastore)
        self.mock_datastore_list.return_value = filtered_datastores
        self.mock_datastore_version_list.return_value = (
            self._get_filtered_datastore_versions(filtered_datastores))

        res = self.client.get(LAUNCH_URL)
        self.mock_is_service_enabled.assert_called_once_with(
            test.IsHttpRequest(), 'network')
        self.mock_datastore_flavors.assert_called_once_with(
            test.IsHttpRequest(), datastore, datastore_version)
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_datastore_version_list.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        return res.context_data['form'].fields

    @test.create_mocks({trove_api.trove: ['datastore_flavors',
                                          'cluster_create',
                                          'datastore_list',
                                          'datastore_version_list'],
                        api.base: ['is_service_enabled']})
    def test_create_simple_cluster(self):
        self.mock_is_service_enabled.return_value = False
        self.mock_datastore_flavors.return_value = self.flavors.list()

        filtered_datastores = self._get_filtered_datastores('mongodb')
        self.mock_datastore_list.return_value = filtered_datastores
        self.mock_datastore_version_list.return_value = (
            self._get_filtered_datastore_versions(filtered_datastores))

        self.mock_cluster_create.return_value = self.trove_clusters.first()

        cluster_name = u'MyCluster'
        cluster_volume = 1
        cluster_flavor = u'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        cluster_instances = 3
        cluster_datastore = u'mongodb'
        cluster_datastore_version = u'2.6'
        cluster_network = u''

        field_name = self._build_flavor_widget_name(cluster_datastore,
                                                    cluster_datastore_version)
        post = {
            'name': cluster_name,
            'volume': cluster_volume,
            'num_instances': cluster_instances,
            'num_shards': 1,
            'datastore': field_name,
            field_name: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        }

        res = self.client.post(LAUNCH_URL, post)
        self.mock_is_service_enabled.assert_called_once_with(
            test.IsHttpRequest(), 'network')
        self.mock_datastore_flavors.assert_called_once_with(
            test.IsHttpRequest(), 'mongodb', '2.6')
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_datastore_version_list.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_cluster_create.assert_called_once_with(
            test.IsHttpRequest(),
            cluster_name,
            cluster_volume,
            cluster_flavor,
            cluster_instances,
            datastore=cluster_datastore,
            datastore_version=cluster_datastore_version,
            nics=cluster_network,
            root_password=None,
            locality=None)
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)

    @test.create_mocks({trove_api.trove: ['datastore_flavors',
                                          'cluster_create',
                                          'datastore_list',
                                          'datastore_version_list'],
                        api.neutron: ['network_list_for_tenant'],
                        api.base: ['is_service_enabled']})
    def test_create_simple_cluster_neutron(self):
        self.mock_is_service_enabled.return_value = True
        self.mock_network_list_for_tenant.return_value = self.networks.list()
        self.mock_datastore_flavors.return_value = self.flavors.list()

        filtered_datastores = self._get_filtered_datastores('mongodb')
        self.mock_datastore_list.return_value = filtered_datastores
        self.mock_datastore_version_list.return_value = (
            self._get_filtered_datastore_versions(filtered_datastores))

        self.mock_cluster_create.return_value = self.trove_clusters.first()

        cluster_name = u'MyCluster'
        cluster_volume = 1
        cluster_flavor = u'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        cluster_instances = 3
        cluster_datastore = u'mongodb'
        cluster_datastore_version = u'2.6'
        cluster_network = u'82288d84-e0a5-42ac-95be-e6af08727e42'

        field_name = self._build_flavor_widget_name(cluster_datastore,
                                                    cluster_datastore_version)
        post = {
            'name': cluster_name,
            'volume': cluster_volume,
            'num_instances': cluster_instances,
            'num_shards': 1,
            'datastore': field_name,
            field_name: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'network': cluster_network,
        }

        res = self.client.post(LAUNCH_URL, post)
        self.mock_is_service_enabled.assert_called_once_with(
            test.IsHttpRequest(), 'network')
        self.mock_network_list_for_tenant.assert_called_once_with(
            test.IsHttpRequest(), '1')
        self.mock_datastore_flavors.assert_called_once_with(
            test.IsHttpRequest(), 'mongodb', '2.6')
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_datastore_version_list.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_cluster_create.assert_called_once_with(
            test.IsHttpRequest(),
            cluster_name,
            cluster_volume,
            cluster_flavor,
            cluster_instances,
            datastore=cluster_datastore,
            datastore_version=cluster_datastore_version,
            nics=cluster_network,
            root_password=None,
            locality=None)
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)

    @test.create_mocks({trove_api.trove: ['datastore_flavors',
                                          'cluster_create',
                                          'datastore_list',
                                          'datastore_version_list'],
                        api.neutron: ['network_list_for_tenant']})
    def test_create_simple_cluster_exception(self):
        self.mock_network_list_for_tenant.return_value = self.networks.list()
        self.mock_datastore_flavors.return_value = self.flavors.list()

        filtered_datastores = self._get_filtered_datastores('mongodb')
        self.mock_datastore_list.return_value = filtered_datastores
        self.mock_datastore_version_list.return_value = (
            self._get_filtered_datastore_versions(filtered_datastores))

        self.mock_cluster_create.side_effect = self.exceptions.trove

        cluster_name = u'MyCluster'
        cluster_volume = 1
        cluster_flavor = u'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        cluster_instances = 3
        cluster_datastore = u'mongodb'
        cluster_datastore_version = u'2.6'
        cluster_network = u''

        field_name = self._build_flavor_widget_name(cluster_datastore,
                                                    cluster_datastore_version)
        post = {
            'name': cluster_name,
            'volume': cluster_volume,
            'num_instances': cluster_instances,
            'num_shards': 1,
            'datastore': field_name,
            field_name: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        }

        res = self.client.post(LAUNCH_URL, post)
        self.mock_network_list_for_tenant.assert_called_once_with(
            test.IsHttpRequest(), '1')
        self.mock_datastore_flavors.assert_called_once_with(
            test.IsHttpRequest(), 'mongodb', '2.6')
        self.mock_datastore_list.assert_called_once_with(test.IsHttpRequest())
        self.mock_datastore_version_list.assert_called_once_with(
            test.IsHttpRequest(), test.IsA(str))
        self.mock_cluster_create.assert_called_once_with(
            test.IsHttpRequest(),
            cluster_name,
            cluster_volume,
            cluster_flavor,
            cluster_instances,
            datastore=cluster_datastore,
            datastore_version=cluster_datastore_version,
            nics=cluster_network,
            root_password=None,
            locality=None)
        self.assertRedirectsNoFollow(res, INDEX_URL)
        self.assertMessageCount(error=1)

    @test.create_mocks({trove_api.trove: ('cluster_get',
                                          'instance_get',
                                          'flavor_get',)})
    def test_details(self):
        cluster = self.trove_clusters.first()
        self.mock_cluster_get.return_value = cluster
        self.mock_instance_get.return_value = self.databases.first()
        self.mock_flavor_get.return_value = self.flavors.first()

        details_url = reverse('horizon:project:database_clusters:detail',
                              args=[cluster.id])
        res = self.client.get(details_url)
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_cluster_get, 2,
            mock.call(test.IsHttpRequest(), cluster.id))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_instance_get, 3,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_flavor_get, 4,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.assertTemplateUsed(res, 'horizon/common/_detail.html')
        self.assertContains(res, cluster.ip[0])

    @test.create_mocks({trove_api.trove: ('cluster_get',
                                          'instance_get',
                                          'flavor_get',)})
    def test_details_without_locality(self):
        cluster = self.trove_clusters.list()[1]
        self.mock_cluster_get.return_value = cluster
        self.mock_instance_get.return_value = self.databases.first()
        self.mock_flavor_get.return_value = self.flavors.first()

        details_url = reverse('horizon:project:database_clusters:detail',
                              args=[cluster.id])
        res = self.client.get(details_url)
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_cluster_get, 2,
            mock.call(test.IsHttpRequest(), cluster.id))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_instance_get, 3,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_flavor_get, 4,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.assertTemplateUsed(res, 'horizon/common/_detail.html')
        self.assertNotContains(res, "Locality")

    @test.create_mocks({trove_api.trove: ('cluster_get',
                                          'instance_get',
                                          'flavor_get',)})
    def test_details_with_locality(self):
        cluster = self.trove_clusters.first()
        self.mock_cluster_get.return_value = cluster
        self.mock_instance_get.return_value = self.databases.first()
        self.mock_flavor_get.return_value = self.flavors.first()

        details_url = reverse('horizon:project:database_clusters:detail',
                              args=[cluster.id])
        res = self.client.get(details_url)
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_cluster_get, 2,
            mock.call(test.IsHttpRequest(), cluster.id))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_instance_get, 3,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_flavor_get, 4,
            mock.call(test.IsHttpRequest(), test.IsA(str)))
        self.assertTemplateUsed(res, 'project/database_clusters/'
                                     '_detail_overview.html')
        self.assertContains(res, "Locality")

    @test.create_mocks(
        {trove_api.trove: ('cluster_get',
                           'cluster_grow'),
         cluster_manager: ('get',)})
    def test_grow_cluster(self):
        cluster = self.trove_clusters.first()
        self.mock_cluster_get.return_value = cluster
        cluster_volume = 1
        flavor = self.flavors.first()
        cluster_flavor = flavor.id
        cluster_flavor_name = flavor.name
        instances = [
            cluster_manager.ClusterInstance("id1", "name1", cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, "master", None,
                                            None),
            cluster_manager.ClusterInstance("id2", "name2", cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, "slave",
                                            "master", None),
            cluster_manager.ClusterInstance("id3", None, cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, None, None, None),
        ]

        manager = cluster_manager.ClusterInstanceManager(cluster.id)
        manager.instances = instances
        self.mock_get.return_value = manager

        url = reverse('horizon:project:database_clusters:cluster_grow_details',
                      args=[cluster.id])
        res = self.client.get(url)
        self.assertTemplateUsed(
            res, 'project/database_clusters/cluster_grow_details.html')
        table = res.context_data[
            "".join([tables.ClusterGrowInstancesTable.Meta.name, '_table'])]
        self.assertEqual(len(cluster.instances), len(table.data))

        action = "".join([tables.ClusterGrowInstancesTable.Meta.name, '__',
                          tables.ClusterGrowRemoveInstance.name, '__',
                          'id1'])
        self.client.post(url, {'action': action})
        self.assertEqual(len(cluster.instances) - 1, len(table.data))

        action = "".join([tables.ClusterGrowInstancesTable.Meta.name, '__',
                          tables.ClusterGrowAction.name, '__',
                          cluster.id])
        res = self.client.post(url, {'action': action})
        self.mock_cluster_get.assert_called_once_with(
            test.IsHttpRequest(), cluster.id)
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_get, 5, mock.call(cluster.id))
        self.mock_cluster_grow.assert_called_once_with(
            test.IsHttpRequest(), cluster.id, instances)
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({trove_api.trove: ('cluster_get',)})
    def test_grow_cluster_no_instances(self):
        cluster = self.trove_clusters.first()
        self.mock_cluster_get.return_value = cluster

        url = reverse('horizon:project:database_clusters:cluster_grow_details',
                      args=[cluster.id])
        res = self.client.get(url)
        self.assertTemplateUsed(
            res, 'project/database_clusters/cluster_grow_details.html')

        action = "".join([tables.ClusterGrowInstancesTable.Meta.name, '__',
                          tables.ClusterGrowAction.name, '__',
                          cluster.id])
        self.client.post(url, {'action': action})
        self.mock_cluster_get.assert_called_once_with(
            test.IsHttpRequest(), cluster.id)
        self.assertMessageCount(info=1)

    @test.create_mocks(
        {trove_api.trove: ('cluster_get',
                           'cluster_grow',),
         cluster_manager: ('get',)})
    def test_grow_cluster_exception(self):
        cluster = self.trove_clusters.first()
        self.mock_cluster_get.return_value = cluster
        cluster_volume = 1
        flavor = self.flavors.first()
        cluster_flavor = flavor.id
        cluster_flavor_name = flavor.name
        instances = [
            cluster_manager.ClusterInstance("id1", "name1", cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, "master", None,
                                            None),
            cluster_manager.ClusterInstance("id2", "name2", cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, "slave",
                                            "master", None),
            cluster_manager.ClusterInstance("id3", None, cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, None, None, None),
        ]

        manager = cluster_manager.ClusterInstanceManager(cluster.id)
        manager.instances = instances
        self.mock_get.return_value = manager
        self.mock_cluster_grow.side_effect = self.exceptions.trove

        url = reverse('horizon:project:database_clusters:cluster_grow_details',
                      args=[cluster.id])
        res = self.client.get(url)
        self.assertTemplateUsed(
            res, 'project/database_clusters/cluster_grow_details.html')

        toSuppress = ["trove_dashboard.content.database_clusters.tables"]

        # Suppress expected log messages in the test output
        loggers = []
        for cls in toSuppress:
            logger = logging.getLogger(cls)
            loggers.append((logger, logger.getEffectiveLevel()))
            logger.setLevel(logging.CRITICAL)

        try:
            action = "".join([tables.ClusterGrowInstancesTable.Meta.name, '__',
                              tables.ClusterGrowAction.name, '__',
                              cluster.id])
            res = self.client.post(url, {'action': action})

            self.mock_cluster_get.assert_called_once_with(
                test.IsHttpRequest(), cluster.id)
            self.assert_mock_multiple_calls_with_same_arguments(
                self.mock_get, 3, mock.call(cluster.id))
            self.mock_cluster_grow.assert_called_once_with(
                test.IsHttpRequest(), cluster.id, instances)
            self.assertMessageCount(error=1)
            self.assertRedirectsNoFollow(res, INDEX_URL)
        finally:
            # Restore the previous log levels
            for (log, level) in loggers:
                log.setLevel(level)

    @test.create_mocks({trove_api.trove: ('cluster_get',
                                          'cluster_shrink')})
    def test_shrink_cluster(self):
        cluster = self.trove_clusters.first()
        self.mock_cluster_get.return_value = cluster
        instance_id = cluster.instances[0]['id']
        cluster_instances = [{'id': instance_id}]

        url = reverse(
            'horizon:project:database_clusters:cluster_shrink_details',
            args=[cluster.id])
        res = self.client.get(url)
        self.assertTemplateUsed(
            res, 'project/database_clusters/cluster_shrink_details.html')
        table = res.context_data[
            "".join([tables.ClusterShrinkInstancesTable.Meta.name, '_table'])]
        self.assertEqual(len(cluster.instances), len(table.data))

        action = "".join([tables.ClusterShrinkInstancesTable.Meta.name, '__',
                          tables.ClusterShrinkAction.name, '__',
                          instance_id])
        res = self.client.post(url, {'action': action})
        self.assert_mock_multiple_calls_with_same_arguments(
            self.mock_cluster_get, 2,
            mock.call(test.IsHttpRequest(), cluster.id))
        self.mock_cluster_shrink.assert_called_once_with(
            test.IsHttpRequest(), cluster.id, cluster_instances)
        self.assertNoFormErrors(res)
        self.assertMessageCount(info=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_mocks({trove_api.trove: ('cluster_get',
                                          'cluster_shrink')})
    def test_shrink_cluster_exception(self):
        cluster = self.trove_clusters.first()
        self.mock_cluster_get.return_value = cluster
        instance_id = cluster.instances[0]['id']
        cluster_instances = [{'id': instance_id}]
        self.mock_cluster_shrink.side_effect = self.exceptions.trove

        url = reverse(
            'horizon:project:database_clusters:cluster_shrink_details',
            args=[cluster.id])
        action = "".join([tables.ClusterShrinkInstancesTable.Meta.name, '__',
                          tables.ClusterShrinkAction.name, '__',
                          instance_id])

        toSuppress = ["trove_dashboard.content.database_clusters.tables"]

        # Suppress expected log messages in the test output
        loggers = []
        for cls in toSuppress:
            logger = logging.getLogger(cls)
            loggers.append((logger, logger.getEffectiveLevel()))
            logger.setLevel(logging.CRITICAL)

        try:
            res = self.client.post(url, {'action': action})
            self.mock_cluster_get.assert_called_once_with(
                test.IsHttpRequest(), cluster.id)
            self.mock_cluster_shrink.assert_called_once_with(
                test.IsHttpRequest(), cluster.id, cluster_instances)
            self.assertMessageCount(error=1)
            self.assertRedirectsNoFollow(res, INDEX_URL)
        finally:
            # Restore the previous log levels
            for (log, level) in loggers:
                log.setLevel(level)

    def _get_filtered_datastores(self, datastore):
        filtered_datastore = []
        for ds in self.datastores.list():
            if datastore in ds.name:
                filtered_datastore.append(ds)
        return filtered_datastore

    def _get_filtered_datastore_versions(self, datastores):
        filtered_datastore_versions = []
        for ds in datastores:
            for dsv in self.datastore_versions.list():
                if ds.id == dsv.datastore:
                    filtered_datastore_versions.append(dsv)
        return filtered_datastore_versions

    def _contains_datastore_in_attribute(self, field, datastore):
        for key, value in field.widget.attrs.items():
            if datastore in key:
                return True
        return False

    def _build_datastore_display_text(self, datastore, datastore_version):
        return datastore + ' - ' + datastore_version

    def _build_flavor_widget_name(self, datastore, datastore_version):
        return common_utils.hexlify(self._build_datastore_display_text(
            datastore, datastore_version))
