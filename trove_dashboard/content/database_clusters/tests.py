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

from django.core.urlresolvers import reverse
from django import http

from mox3.mox import IsA  # noqa

from openstack_dashboard import api
from troveclient import common

from trove_dashboard import api as trove_api
from trove_dashboard.content.database_clusters \
    import cluster_manager
from trove_dashboard.content.database_clusters import tables
from trove_dashboard.test import helpers as test

INDEX_URL = reverse('horizon:project:database_clusters:index')
LAUNCH_URL = reverse('horizon:project:database_clusters:launch')
DETAILS_URL = reverse('horizon:project:database_clusters:detail', args=['id'])
RESET_PASSWORD_VIEWNAME = 'horizon:project:database_clusters:reset_password'


class ClustersTests(test.TestCase):
    @test.create_stubs({trove_api.trove: ('cluster_list',
                                          'flavor_list')})
    def test_index(self):
        clusters = common.Paginated(self.trove_clusters.list())
        trove_api.trove.cluster_list(IsA(http.HttpRequest), marker=None)\
            .AndReturn(clusters)
        trove_api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndReturn(self.flavors.list())

        self.mox.ReplayAll()
        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, 'project/database_clusters/index.html')

    @test.create_stubs({trove_api.trove: ('cluster_list',
                                          'flavor_list')})
    def test_index_flavor_exception(self):
        clusters = common.Paginated(self.trove_clusters.list())
        trove_api.trove.cluster_list(IsA(http.HttpRequest), marker=None)\
            .AndReturn(clusters)
        trove_api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()
        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, 'project/database_clusters/index.html')
        self.assertMessageCount(res, error=1)

    @test.create_stubs({trove_api.trove: ('cluster_list',)})
    def test_index_list_exception(self):
        trove_api.trove.cluster_list(IsA(http.HttpRequest), marker=None)\
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()
        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, 'project/database_clusters/index.html')
        self.assertMessageCount(res, error=1)

    @test.create_stubs({trove_api.trove: ('cluster_list',
                                          'flavor_list')})
    def test_index_pagination(self):
        clusters = self.trove_clusters.list()
        last_record = clusters[0]
        clusters = common.Paginated(clusters, next_marker="foo")
        trove_api.trove.cluster_list(IsA(http.HttpRequest), marker=None)\
            .AndReturn(clusters)
        trove_api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndReturn(self.flavors.list())

        self.mox.ReplayAll()
        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, 'project/database_clusters/index.html')
        self.assertContains(
            res, 'marker=' + last_record.id)

    @test.create_stubs({trove_api.trove: ('cluster_list',
                                          'flavor_list')})
    def test_index_flavor_list_exception(self):
        clusters = common.Paginated(self.trove_clusters.list())
        trove_api.trove.cluster_list(IsA(http.HttpRequest), marker=None)\
            .AndReturn(clusters)
        trove_api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndRaise(self.exceptions.trove)

        self.mox.ReplayAll()

        res = self.client.get(INDEX_URL)

        self.assertTemplateUsed(res, 'project/database_clusters/index.html')
        self.assertMessageCount(res, error=1)

    @test.create_stubs({trove_api.trove: ('datastore_flavors',
                                          'datastore_list',
                                          'datastore_version_list'),
                        api.base: ['is_service_enabled']})
    def test_launch_cluster(self):
        api.base.is_service_enabled(IsA(http.HttpRequest), 'network')\
            .AndReturn(False)
        filtered_datastores = self._get_filtered_datastores('mongodb')
        trove_api.trove.datastore_flavors(IsA(http.HttpRequest),
                                          'mongodb', '2.6')\
            .AndReturn(self.flavors.list())
        trove_api.trove.datastore_list(IsA(http.HttpRequest))\
            .AndReturn(filtered_datastores)
        trove_api.trove.datastore_version_list(IsA(http.HttpRequest),
                                               IsA(str))\
            .AndReturn(
                self._get_filtered_datastore_versions(filtered_datastores))
        self.mox.ReplayAll()
        res = self.client.get(LAUNCH_URL)
        self.assertTemplateUsed(res, 'project/database_clusters/launch.html')

    def test_launch_cluster_mongo_fields(self):
        datastore = 'mongodb'
        fields = self.launch_cluster_fields_setup(datastore, '2.6')

        self.assertTrue(self._contains_datastore_in_attribute(
            fields['flavor'], datastore))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['num_instances'], datastore))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['num_shards'], datastore))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['root_password'], datastore))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_instances_vertica'], datastore))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['vertica_flavor'], datastore))

    def test_launch_cluster_redis_fields(self):
        datastore = 'redis'
        fields = self.launch_cluster_fields_setup(datastore, '3.0')

        self.assertTrue(self._contains_datastore_in_attribute(
            fields['flavor'], datastore))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['num_instances'], datastore))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_shards'], datastore))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['root_password'], datastore))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_instances_vertica'], datastore))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['vertica_flavor'], datastore))

    def test_launch_cluster_vertica_fields(self):
        datastore = 'vertica'
        fields = self.launch_cluster_fields_setup(datastore, '7.1')

        self.assertFalse(self._contains_datastore_in_attribute(
            fields['flavor'], datastore))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_instances'], datastore))
        self.assertFalse(self._contains_datastore_in_attribute(
            fields['num_shards'], datastore))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['root_password'], datastore))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['num_instances_vertica'], datastore))
        self.assertTrue(self._contains_datastore_in_attribute(
            fields['vertica_flavor'], datastore))

    @test.create_stubs({trove_api.trove: ('datastore_flavors',
                                          'datastore_list',
                                          'datastore_version_list'),
                        api.base: ['is_service_enabled']})
    def launch_cluster_fields_setup(self, datastore, datastore_version):
        api.base.is_service_enabled(IsA(http.HttpRequest), 'network')\
            .AndReturn(False)
        filtered_datastores = self._get_filtered_datastores(datastore)
        trove_api.trove.datastore_flavors(IsA(http.HttpRequest),
                                          datastore, datastore_version)\
            .AndReturn(self.flavors.list())
        trove_api.trove.datastore_list(IsA(http.HttpRequest))\
            .AndReturn(filtered_datastores)
        trove_api.trove.datastore_version_list(IsA(http.HttpRequest),
                                               IsA(str))\
            .AndReturn(
                self._get_filtered_datastore_versions(filtered_datastores))
        self.mox.ReplayAll()
        res = self.client.get(LAUNCH_URL)
        return res.context_data['form'].fields

    @test.create_stubs({trove_api.trove: ['datastore_flavors',
                                          'cluster_create',
                                          'datastore_list',
                                          'datastore_version_list'],
                        api.base: ['is_service_enabled']})
    def test_create_simple_cluster(self):
        api.base.is_service_enabled(IsA(http.HttpRequest), 'network')\
            .AndReturn(False)
        filtered_datastores = self._get_filtered_datastores('mongodb')
        trove_api.trove.datastore_flavors(IsA(http.HttpRequest),
                                          'mongodb', '2.6')\
            .AndReturn(self.flavors.list())
        trove_api.trove.datastore_list(IsA(http.HttpRequest))\
            .AndReturn(filtered_datastores)
        trove_api.trove.datastore_version_list(IsA(http.HttpRequest),
                                               IsA(str))\
            .AndReturn(
                self._get_filtered_datastore_versions(filtered_datastores))

        cluster_name = u'MyCluster'
        cluster_volume = 1
        cluster_flavor = u'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        cluster_instances = 3
        cluster_datastore = u'mongodb'
        cluster_datastore_version = u'2.6'
        cluster_network = u''
        trove_api.trove.cluster_create(
            IsA(http.HttpRequest),
            cluster_name,
            cluster_volume,
            cluster_flavor,
            cluster_instances,
            datastore=cluster_datastore,
            datastore_version=cluster_datastore_version,
            nics=cluster_network,
            root_password=None).AndReturn(self.trove_clusters.first())

        self.mox.ReplayAll()
        post = {
            'name': cluster_name,
            'volume': cluster_volume,
            'num_instances': cluster_instances,
            'num_shards': 1,
            'num_instances_per_shards': cluster_instances,
            'datastore': cluster_datastore + u'-' + cluster_datastore_version,
            'flavor': cluster_flavor,
            'network': cluster_network
        }

        res = self.client.post(LAUNCH_URL, post)
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)

    @test.create_stubs({trove_api.trove: ['datastore_flavors',
                                          'cluster_create',
                                          'datastore_list',
                                          'datastore_version_list'],
                        api.neutron: ['network_list_for_tenant'],
                        api.base: ['is_service_enabled']})
    def test_create_simple_cluster_neutron(self):
        api.base.is_service_enabled(IsA(http.HttpRequest), 'network')\
            .AndReturn(True)
        api.neutron.network_list_for_tenant(IsA(http.HttpRequest), '1')\
            .AndReturn(self.networks.list())
        filtered_datastores = self._get_filtered_datastores('mongodb')
        trove_api.trove.datastore_flavors(IsA(http.HttpRequest),
                                          'mongodb', '2.6')\
            .AndReturn(self.flavors.list())
        trove_api.trove.datastore_list(IsA(http.HttpRequest))\
            .AndReturn(filtered_datastores)
        trove_api.trove.datastore_version_list(IsA(http.HttpRequest),
                                               IsA(str))\
            .AndReturn(
                self._get_filtered_datastore_versions(filtered_datastores))

        cluster_name = u'MyCluster'
        cluster_volume = 1
        cluster_flavor = u'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        cluster_instances = 3
        cluster_datastore = u'mongodb'
        cluster_datastore_version = u'2.6'
        cluster_network = u'82288d84-e0a5-42ac-95be-e6af08727e42'
        trove_api.trove.cluster_create(
            IsA(http.HttpRequest),
            cluster_name,
            cluster_volume,
            cluster_flavor,
            cluster_instances,
            datastore=cluster_datastore,
            datastore_version=cluster_datastore_version,
            nics=cluster_network,
            root_password=None).AndReturn(self.trove_clusters.first())

        self.mox.ReplayAll()
        post = {
            'name': cluster_name,
            'volume': cluster_volume,
            'num_instances': cluster_instances,
            'num_shards': 1,
            'num_instances_per_shards': cluster_instances,
            'datastore': cluster_datastore + u'-' + cluster_datastore_version,
            'flavor': cluster_flavor,
            'network': cluster_network
        }

        res = self.client.post(LAUNCH_URL, post)
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)

    @test.create_stubs({trove_api.trove: ['datastore_flavors',
                                          'cluster_create',
                                          'datastore_list',
                                          'datastore_version_list'],
                        api.neutron: ['network_list_for_tenant']})
    def test_create_simple_cluster_exception(self):
        api.neutron.network_list_for_tenant(IsA(http.HttpRequest), '1')\
            .AndReturn(self.networks.list())
        filtered_datastores = self._get_filtered_datastores('mongodb')
        trove_api.trove.datastore_flavors(IsA(http.HttpRequest),
                                          'mongodb', '2.6')\
            .AndReturn(self.flavors.list())
        trove_api.trove.datastore_list(IsA(http.HttpRequest))\
            .AndReturn(filtered_datastores)
        trove_api.trove.datastore_version_list(IsA(http.HttpRequest),
                                               IsA(str))\
            .AndReturn(
                self._get_filtered_datastore_versions(filtered_datastores))

        cluster_name = u'MyCluster'
        cluster_volume = 1
        cluster_flavor = u'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        cluster_instances = 3
        cluster_datastore = u'mongodb'
        cluster_datastore_version = u'2.6'
        cluster_network = u'82288d84-e0a5-42ac-95be-e6af08727e42'
        trove_api.trove.cluster_create(
            IsA(http.HttpRequest),
            cluster_name,
            cluster_volume,
            cluster_flavor,
            cluster_instances,
            datastore=cluster_datastore,
            datastore_version=cluster_datastore_version,
            nics=cluster_network,
            root_password=None).AndReturn(self.trove_clusters.first())

        self.mox.ReplayAll()
        post = {
            'name': cluster_name,
            'volume': cluster_volume,
            'num_instances': cluster_instances,
            'num_shards': 1,
            'num_instances_per_shards': cluster_instances,
            'datastore': cluster_datastore + u'-' + cluster_datastore_version,
            'flavor': cluster_flavor,
            'network': cluster_network
        }

        res = self.client.post(LAUNCH_URL, post)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({trove_api.trove: ('cluster_get',
                                          'instance_get',
                                          'flavor_get',)})
    def test_details(self):
        cluster = self.trove_clusters.first()
        trove_api.trove.cluster_get(IsA(http.HttpRequest), cluster.id)\
            .MultipleTimes().AndReturn(cluster)
        trove_api.trove.instance_get(IsA(http.HttpRequest), IsA(str))\
            .MultipleTimes().AndReturn(self.databases.first())
        trove_api.trove.flavor_get(IsA(http.HttpRequest), IsA(str))\
            .MultipleTimes().AndReturn(self.flavors.first())
        self.mox.ReplayAll()

        details_url = reverse('horizon:project:database_clusters:detail',
                              args=[cluster.id])
        res = self.client.get(details_url)
        self.assertTemplateUsed(res, 'horizon/common/_detail.html')
        self.assertContains(res, cluster.ip[0])

    @test.create_stubs(
        {trove_api.trove: ('cluster_get',
                           'cluster_grow'),
         cluster_manager: ('get',)})
    def test_grow_cluster(self):
        cluster = self.trove_clusters.first()
        trove_api.trove.cluster_get(IsA(http.HttpRequest), cluster.id)\
            .AndReturn(cluster)
        cluster_volume = 1
        flavor = self.flavors.first()
        cluster_flavor = flavor.id
        cluster_flavor_name = flavor.name
        instances = [
            cluster_manager.ClusterInstance("id1", "name1", cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, "master", None),
            cluster_manager.ClusterInstance("id2", "name2", cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, "slave", "master"),
            cluster_manager.ClusterInstance("id3", None, cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, None, None),
        ]

        manager = cluster_manager.ClusterInstanceManager(cluster.id)
        manager.instances = instances
        cluster_manager.get(cluster.id).MultipleTimes().AndReturn(manager)
        trove_api.trove.cluster_grow(IsA(http.HttpRequest),
                                     cluster.id,
                                     instances)
        self.mox.ReplayAll()

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
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({trove_api.trove: ('cluster_get',)})
    def test_grow_cluster_no_instances(self):
        cluster = self.trove_clusters.first()
        trove_api.trove.cluster_get(IsA(http.HttpRequest), cluster.id)\
            .AndReturn(cluster)
        self.mox.ReplayAll()

        url = reverse('horizon:project:database_clusters:cluster_grow_details',
                      args=[cluster.id])
        res = self.client.get(url)
        self.assertTemplateUsed(
            res, 'project/database_clusters/cluster_grow_details.html')

        action = "".join([tables.ClusterGrowInstancesTable.Meta.name, '__',
                          tables.ClusterGrowAction.name, '__',
                          cluster.id])
        self.client.post(url, {'action': action})
        self.assertMessageCount(info=1)

    @test.create_stubs(
        {trove_api.trove: ('cluster_get',
                           'cluster_grow',),
         cluster_manager: ('get',)})
    def test_grow_cluster_exception(self):
        cluster = self.trove_clusters.first()
        trove_api.trove.cluster_get(IsA(http.HttpRequest), cluster.id)\
            .AndReturn(cluster)
        cluster_volume = 1
        flavor = self.flavors.first()
        cluster_flavor = flavor.id
        cluster_flavor_name = flavor.name
        instances = [
            cluster_manager.ClusterInstance("id1", "name1", cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, "master", None),
            cluster_manager.ClusterInstance("id2", "name2", cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, "slave", "master"),
            cluster_manager.ClusterInstance("id3", None, cluster_flavor,
                                            cluster_flavor_name,
                                            cluster_volume, None, None),
        ]

        manager = cluster_manager.ClusterInstanceManager(cluster.id)
        manager.instances = instances
        cluster_manager.get(cluster.id).MultipleTimes().AndReturn(manager)
        trove_api.trove.cluster_grow(IsA(http.HttpRequest),
                                     cluster.id,
                                     instances).AndRaise(self.exceptions.trove)
        self.mox.ReplayAll()

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

            self.assertMessageCount(error=1)
            self.assertRedirectsNoFollow(res, INDEX_URL)
        finally:
            # Restore the previous log levels
            for (log, level) in loggers:
                log.setLevel(level)

    @test.create_stubs({trove_api.trove: ('cluster_get',
                                          'cluster_shrink')})
    def test_shrink_cluster(self):
        cluster = self.trove_clusters.first()
        trove_api.trove.cluster_get(IsA(http.HttpRequest), cluster.id)\
            .MultipleTimes().AndReturn(cluster)
        instance_id = cluster.instances[0]['id']
        cluster_instances = [{'id': instance_id}]
        trove_api.trove.cluster_shrink(IsA(http.HttpRequest),
                                       cluster.id,
                                       cluster_instances)
        self.mox.ReplayAll()

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
        self.assertNoFormErrors(res)
        self.assertMessageCount(info=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({trove_api.trove: ('cluster_get',
                                          'cluster_shrink')})
    def test_shrink_cluster_exception(self):
        cluster = self.trove_clusters.first()
        trove_api.trove.cluster_get(IsA(http.HttpRequest), cluster.id)\
            .MultipleTimes().AndReturn(cluster)
        cluster_id = cluster.instances[0]['id']
        cluster_instances = [cluster_id]
        trove_api.trove.cluster_shrink(IsA(http.HttpRequest),
                                       cluster.id,
                                       cluster_instances)\
            .AndRaise(self.exceptions.trove)
        self.mox.ReplayAll()

        url = reverse(
            'horizon:project:database_clusters:cluster_shrink_details',
            args=[cluster.id])
        action = "".join([tables.ClusterShrinkInstancesTable.Meta.name, '__',
                          tables.ClusterShrinkAction.name, '__',
                          cluster_id])

        toSuppress = ["trove_dashboard.content.database_clusters.tables"]

        # Suppress expected log messages in the test output
        loggers = []
        for cls in toSuppress:
            logger = logging.getLogger(cls)
            loggers.append((logger, logger.getEffectiveLevel()))
            logger.setLevel(logging.CRITICAL)

        try:
            res = self.client.post(url, {'action': action})
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
        for key, value in field.widget.attrs.iteritems():
            if datastore in key:
                return True
        return False
