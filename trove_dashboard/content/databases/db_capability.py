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


CASSANDRA = "cassandra"
MARIA = "maria"
MONGODB = "mongodb"
MYSQL = "mysql"
PERCONA = "percona"
PERCONA_CLUSTER = "pxc"
REDIS = "redis"
VERTICA = "vertica"

_mysql_compatible_datastores = (MYSQL, MARIA, PERCONA, PERCONA_CLUSTER)
_cluster_capable_datastores = (CASSANDRA, MARIA, MONGODB, PERCONA_CLUSTER,
                               REDIS, VERTICA)
_cluster_grow_shrink_capable_datastores = (CASSANDRA, MARIA, MONGODB,
                                           PERCONA_CLUSTER, REDIS)


def can_modify_cluster(datastore):
    return _is_datastore_in_list(datastore,
                                 _cluster_grow_shrink_capable_datastores)


def is_mongodb_datastore(datastore):
    return (datastore is not None) and (MONGODB in datastore.lower())


def is_percona_cluster_datastore(datastore):
    return (datastore is not None) and (PERCONA_CLUSTER in datastore.lower())


def is_redis_datastore(datastore):
    return (datastore is not None) and (REDIS in datastore.lower())


def is_vertica_datastore(datastore):
    return (datastore is not None) and (VERTICA in datastore.lower())


def is_mysql_compatible(datastore):
    return _is_datastore_in_list(datastore, _mysql_compatible_datastores)


def is_cluster_capable_datastore(datastore):
    return _is_datastore_in_list(datastore, _cluster_capable_datastores)


def _is_datastore_in_list(datastore, datastores):
    if datastore is not None:
        datastore_lower = datastore.lower()
        for ds in datastores:
            if ds in datastore_lower:
                return True
    return False
