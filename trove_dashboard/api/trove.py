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

from django.conf import settings
from horizon.utils import functions as utils
from horizon.utils.memoized import memoized  # noqa
from keystoneauth1 import session
from keystoneclient.auth import token_endpoint
from novaclient import client as nova_client
from openstack_auth import utils as auth_utils
from openstack_dashboard.api import base
from oslo_log import log as logging
from troveclient.v1 import client

# Supported compute versions
NOVA_VERSIONS = base.APIVersionManager("compute", preferred_version=2)
NOVA_VERSIONS.load_supported_version(1.1,
                                     {"client": nova_client, "version": 1.1})
NOVA_VERSIONS.load_supported_version(2, {"client": nova_client, "version": 2})
NOVA_VERSION = NOVA_VERSIONS.get_active_version()['version']

LOG = logging.getLogger(__name__)


@memoized
def troveclient(request):
    insecure = getattr(settings, 'OPENSTACK_SSL_NO_VERIFY', False)
    cacert = getattr(settings, 'OPENSTACK_SSL_CACERT', None)
    endpoint_type = getattr(settings, 'OPENSTACK_ENDPOINT_TYPE', 'publicURL')
    region = request.user.services_region

    endpoint = base.url_for(request, 'database')
    auth_url, _ = auth_utils.fix_auth_url_version_prefix(
        settings.OPENSTACK_KEYSTONE_URL)
    auth = token_endpoint.Token(auth_url, request.user.token.id)
    verify = not insecure and (cacert or True)

    t_client = client.Client(session=session.Session(auth=auth, verify=verify),
                             service_type='database',
                             endpoint_type=endpoint_type,
                             region_name=region,
                             endpoint_override=endpoint)
    return t_client


def cluster_list(request, marker=None):
    page_size = utils.get_page_size(request)
    return troveclient(request).clusters.list(limit=page_size, marker=marker)


def cluster_get(request, cluster_id):
    return troveclient(request).clusters.get(cluster_id)


def cluster_delete(request, cluster_id):
    return troveclient(request).clusters.delete(cluster_id)


def cluster_create(request, name, volume, flavor, num_instances,
                   datastore, datastore_version,
                   nics=None, root_password=None, locality=None):
    instances = []
    for i in range(num_instances):
        instance = {}
        instance["flavorRef"] = flavor
        if volume > 0:
            instance["volume"] = {'size': volume}
        if nics:
            instance["nics"] = [{"net-id": nics}]
        instances.append(instance)

    # TODO(saurabhs): vertica needs root password on cluster create
    return troveclient(request).clusters.create(
        name,
        datastore,
        datastore_version,
        instances=instances,
        locality=locality)


def cluster_grow(request, cluster_id, new_instances):
    instances = []
    for new_instance in new_instances:
        instance = {}
        instance["flavorRef"] = new_instance.flavor_id
        if new_instance.volume > 0:
            instance["volume"] = {'size': new_instance.volume}
        if new_instance.name:
            instance["name"] = new_instance.name
        if new_instance.type:
            instance["type"] = new_instance.type
        if new_instance.related_to:
            instance["related_to"] = new_instance.related_to
        if new_instance.nics:
            instance["nics"] = [{'net-id': new_instance.nics}]
        instances.append(instance)
    return troveclient(request).clusters.grow(cluster_id, instances)


def cluster_shrink(request, cluster_id, instances):
    return troveclient(request).clusters.shrink(cluster_id, instances)


def create_cluster_root(request, cluster_id, password):
    # It appears the code below depends on this trove change
    # https://review.opendev.org/#/c/166954/.  Comment out when that
    # change merges.
    # return troveclient(request).cluster.reset_root_password(cluster_id)
    troveclient(request).root.create_cluster_root(cluster_id, password)


def instance_list(request, marker=None):
    page_size = utils.get_page_size(request)
    return troveclient(request).instances.list(limit=page_size, marker=marker)


def instance_list_all(request):
    instances = instance_list(request)
    marker = instances.next
    while marker:
        temp_instances = instance_list(request, marker=marker)
        marker = temp_instances.next
        for instance in temp_instances:
            instances.append(instance)
        instances.links = temp_instances.links
    instances.next = None
    return instances


def instance_get(request, instance_id):
    return troveclient(request).instances.get(instance_id)


def instance_delete(request, instance_id):
    return troveclient(request).instances.delete(instance_id)


def instance_create(request, name, volume, flavor=None, databases=None,
                    users=None, restore_point=None, nics=None,
                    datastore=None, datastore_version=None,
                    replica_of=None, replica_count=None,
                    volume_type=None, configuration=None, locality=None,
                    availability_zone=None, access=None):
    # TODO(dklyle): adding conditional to support trove without volume
    # support for now until API supports checking for volume support
    if volume > 0 and not replica_of:
        volume_params = {'size': volume}
        if volume_type:
            volume_params['type'] = volume_type
    else:
        volume_params = None

    if replica_of:
        flavor = None
        volume_params = None
        datastore = None
        datastore_version = None

    return troveclient(request).instances.create(
        name,
        flavor,
        volume=volume_params,
        databases=databases,
        users=users,
        restorePoint=restore_point,
        nics=nics,
        datastore=datastore,
        datastore_version=datastore_version,
        replica_of=replica_of,
        replica_count=replica_count,
        configuration=configuration,
        locality=locality,
        availability_zone=availability_zone,
        access=access)


def instance_resize_volume(request, instance_id, size):
    return troveclient(request).instances.resize_volume(instance_id, size)


def instance_resize(request, instance_id, flavor_id):
    return troveclient(request).instances.resize_instance(instance_id,
                                                          flavor_id)


def instance_backups(request, instance_id):
    return troveclient(request).instances.backups(instance_id)


def instance_restart(request, instance_id):
    return troveclient(request).instances.restart(instance_id)


def instance_update(request, instance_id, **kwargs):
    return troveclient(request).instances.update(instance_id, **kwargs)


def instance_detach_replica(request, instance_id):
    return troveclient(request).instances.update(instance_id,
                                                 detach_replica_source=True)


def promote_to_replica_source(request, instance_id):
    return troveclient(request).instances.promote_to_replica_source(
        instance_id)


def eject_replica_source(request, instance_id):
    return troveclient(request).instances.eject_replica_source(instance_id)


def instance_attach_configuration(request, instance_id, configuration):
    return troveclient(request).instances.modify(instance_id,
                                                 configuration=configuration)


def instance_detach_configuration(request, instance_id):
    return troveclient(request).instances.modify(instance_id)


def database_list(request, instance_id):
    return troveclient(request).databases.list(instance_id)


def database_create(request, instance_id, db_name, character_set=None,
                    collation=None):
    database = {'name': db_name}
    if collation:
        database['collate'] = collation
    if character_set:
        database['character_set'] = character_set
    return troveclient(request).databases.create(instance_id, [database])


def database_delete(request, instance_id, db_name):
    return troveclient(request).databases.delete(instance_id, db_name)


def backup_list(request):
    return troveclient(request).backups.list()


def backup_get(request, backup_id):
    return troveclient(request).backups.get(backup_id)


def backup_delete(request, backup_id):
    return troveclient(request).backups.delete(backup_id)


def backup_create(request, name, instance_id, description=None,
                  parent_id=None, swift_container=None):
    return troveclient(request).backups.create(name, instance_id,
                                               description=description,
                                               parent_id=parent_id,
                                               swift_container=swift_container)


def backup_strategy_create(request, instance_id=None, swift_container=None):
    return troveclient(request).backup_strategies.create(
        instance_id=instance_id, swift_container=swift_container)


def backup_strategy_list(request, instance_id=None, project_id=None):
    return troveclient(request).backup_strategies.list(instance_id=instance_id,
                                                       project_id=project_id)


def backup_strategy_delete(request, instance_id=None, project_id=None):
    return troveclient(request).backup_strategies.delete(
        instance_id=instance_id, project_id=project_id)


def nova_client_client(request):
    insecure = getattr(settings, 'OPENSTACK_SSL_NO_VERIFY', False)
    cacert = getattr(settings, 'OPENSTACK_SSL_CACERT', None)
    endpoint_type = getattr(settings, 'OPENSTACK_ENDPOINT_TYPE', 'publicURL')
    region = request.user.services_region

    endpoint = base.url_for(request, 'compute')
    auth_url, _ = auth_utils.fix_auth_url_version_prefix(
        settings.OPENSTACK_KEYSTONE_URL)
    auth = token_endpoint.Token(auth_url, request.user.token.id)
    verify = not insecure and (cacert or True)

    nova = nova_client.Client(
        NOVA_VERSION,
        session=session.Session(auth=auth, verify=verify),
        endpoint_type=endpoint_type,
        service_type='compute',
        region_name=region,
        endpoint_override=endpoint)

    return nova


def flavor_list(request):
    return nova_client_client(request).flavors.list()


def datastore_flavors(request, datastore_name=None,
                      datastore_version=None):
    return flavor_list(request)


def flavor_get(request, flavor_id):
    return nova_client_client(request).flavors.get(flavor_id)


def root_enable(request, instance_ids):
    username, password = troveclient(request).root.create(instance_ids[0])
    return username, password


def root_show(request, instance_id):
    return troveclient(request).root.is_root_enabled(instance_id)


def root_disable(request, instance_id):
    return troveclient(request).root.delete(instance_id)


def users_list(request, instance_id):
    return troveclient(request).users.list(instance_id)


def user_create(request, instance_id, username, password,
                host=None, databases=[]):
    user = {'name': username, 'password': password, 'databases': databases}
    if host:
        user['host'] = host

    return troveclient(request).users.create(instance_id, [user])


def user_delete(request, instance_id, user, host=None):
    return troveclient(request).users.delete(instance_id, user, hostname=host)


def user_update_attributes(request, instance_id, name, host=None,
                           new_name=None, new_password=None, new_host=None):
    new_attributes = {}
    if new_name:
        new_attributes['name'] = new_name
    if new_password:
        new_attributes['password'] = new_password
    if new_host:
        new_attributes['host'] = new_host
    return troveclient(request).users.update_attributes(
        instance_id, name, newuserattr=new_attributes, hostname=host)


def user_list_access(request, instance_id, username, host=None):
    return troveclient(request).users.list_access(
        instance_id, username, hostname=host)


def user_grant_access(request, instance_id, username, databases, host=None):
    return troveclient(request).users.grant(
        instance_id, username, databases, hostname=host)


def user_revoke_access(request, instance_id, username, database, host=None):
    return troveclient(request).users.revoke(
        instance_id, username, database, hostname=host)


def user_show_access(request, instance_id, username, host=None):
    return troveclient(request).users.list_access(
        instance_id, username, hostname=host)


def datastore_list(request):
    return troveclient(request).datastores.list()


def datastore_version_list(request, datastore):
    return troveclient(request).datastore_versions.list(datastore)


def log_list(request, instance_id):
    return troveclient(request).instances.log_list(instance_id)


def log_enable(request, instance_id, log_name):
    return troveclient(request).instances.log_action(instance_id, log_name,
                                                     enable=True)


def log_disable(request, instance_id, log_name):
    return troveclient(request).instances.log_action(instance_id, log_name,
                                                     disable=True)


def log_publish(request, instance_id, log_name):
    return troveclient(request).instances.log_action(instance_id, log_name,
                                                     publish=True)


def log_discard(request, instance_id, log_name):
    return troveclient(request).instances.log_action(instance_id, log_name,
                                                     discard=True)


def log_tail(request, instance_id, log_name, publish, lines, swift=None):
    return troveclient(request).instances.log_generator(instance_id,
                                                        log_name,
                                                        publish=publish,
                                                        lines=lines,
                                                        swift=swift)


def configuration_list(request):
    return troveclient(request).configurations.list()


def configuration_get(request, group_id):
    return troveclient(request).configurations.get(group_id)


def configuration_parameters_list(request, datastore, datastore_version):
    return troveclient(request).configuration_parameters.parameters(
        datastore, datastore_version)


def configuration_create(request,
                         name,
                         values,
                         description=None,
                         datastore=None,
                         datastore_version=None):
    return troveclient(request).configurations.create(name,
                                                      values,
                                                      description,
                                                      datastore,
                                                      datastore_version)


def configuration_delete(request, group_id):
    return troveclient(request).configurations.delete(group_id)


def configuration_instances(request, group_id):
    return troveclient(request).configurations.instances(group_id)


def configuration_update(request, group_id, values):
    return troveclient(request).configurations.update(group_id, values)


def configuration_default(request, instance_id):
    return troveclient(request).instances.configuration(instance_id)


def stop_database(request, instance_id):
    return troveclient(request).mgmt_instances.stop(instance_id)
