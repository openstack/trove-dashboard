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

from django.conf import settings
from troveclient.v1 import client

from openstack_dashboard.api import base

from horizon.utils import functions as utils
from horizon.utils.memoized import memoized  # noqa

LOG = logging.getLogger(__name__)


@memoized
def troveclient(request):
    insecure = getattr(settings, 'OPENSTACK_SSL_NO_VERIFY', False)
    cacert = getattr(settings, 'OPENSTACK_SSL_CACERT', None)
    trove_url = base.url_for(request, 'database')
    c = client.Client(request.user.username,
                      request.user.token.id,
                      project_id=request.user.project_id,
                      auth_url=trove_url,
                      insecure=insecure,
                      cacert=cacert,
                      http_log_debug=settings.DEBUG)
    c.client.auth_token = request.user.token.id
    c.client.management_url = trove_url
    return c


def cluster_list(request, marker=None):
    page_size = utils.get_page_size(request)
    return troveclient(request).clusters.list(limit=page_size, marker=marker)


def cluster_get(request, cluster_id):
    return troveclient(request).clusters.get(cluster_id)


def cluster_delete(request, cluster_id):
    return troveclient(request).clusters.delete(cluster_id)


def cluster_create(request, name, volume, flavor, num_instances,
                   datastore, datastore_version,
                   nics=None, root_password=None):
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
        instances=instances)


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
        instances.append(instance)
    return troveclient(request).clusters.grow(cluster_id, instances)


def cluster_shrink(request, cluster_id, instances):
    return troveclient(request).clusters.shrink(cluster_id, instances)


def create_cluster_root(request, cluster_id, password):
    # It appears the code below depends on this trove change
    # https://review.openstack.org/#/c/166954/.  Comment out when that
    # change merges.
    # return troveclient(request).cluster.reset_root_password(cluster_id)
    troveclient(request).root.create_cluster_root(cluster_id, password)


def instance_list(request, marker=None):
    page_size = utils.get_page_size(request)
    return troveclient(request).instances.list(limit=page_size, marker=marker)


def instance_get(request, instance_id):
    return troveclient(request).instances.get(instance_id)


def instance_delete(request, instance_id):
    return troveclient(request).instances.delete(instance_id)


def instance_create(request, name, volume, flavor, databases=None,
                    users=None, restore_point=None, nics=None,
                    datastore=None, datastore_version=None,
                    replica_of=None, volume_type=None):
    # TODO(dklyle): adding conditional to support trove without volume
    # support for now until API supports checking for volume support
    if volume > 0:
        volume_params = {'size': volume}
        if volume_type:
            volume_params['type'] = volume_type
    else:
        volume_params = None
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
        replica_of=replica_of)


def instance_resize_volume(request, instance_id, size):
    return troveclient(request).instances.resize_volume(instance_id, size)


def instance_resize(request, instance_id, flavor_id):
    return troveclient(request).instances.resize_instance(instance_id,
                                                          flavor_id)


def instance_backups(request, instance_id):
    return troveclient(request).instances.backups(instance_id)


def instance_restart(request, instance_id):
    return troveclient(request).instances.restart(instance_id)


def instance_detach_replica(request, instance_id):
    return troveclient(request).instances.edit(instance_id,
                                               detach_replica_source=True)


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
                  parent_id=None):
    return troveclient(request).backups.create(name, instance_id,
                                               description, parent_id)


def flavor_list(request):
    return troveclient(request).flavors.list()


def datastore_flavors(request, datastore_name=None,
                      datastore_version=None):
    # if datastore info is available then get datastore specific flavors
    if datastore_name and datastore_version:
        try:
            return troveclient(request).flavors.\
                list_datastore_version_associated_flavors(datastore_name,
                                                          datastore_version)
        except Exception:
            LOG.warning("Failed to retrieve datastore specific flavors")
    return flavor_list(request)


def flavor_get(request, flavor_id):
    return troveclient(request).flavors.get(flavor_id)


def root_enable(request, instance_ids):
    username, password = troveclient(request).root.create(instance_ids[0])
    return username, password


def root_show(request, instance_id):
    return troveclient(request).root.is_root_enabled(instance_id)


def users_list(request, instance_id):
    return troveclient(request).users.list(instance_id)


def user_create(request, instance_id, username, password,
                host=None, databases=[]):
    user = {'name': username, 'password': password, 'databases': databases}
    if host:
        user['host'] = host

    return troveclient(request).users.create(instance_id, [user])


def user_delete(request, instance_id, user):
    return troveclient(request).users.delete(instance_id, user)


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


def datastore_list(request):
    return troveclient(request).datastores.list()


def datastore_version_list(request, datastore):
    return troveclient(request).datastore_versions.list(datastore)
