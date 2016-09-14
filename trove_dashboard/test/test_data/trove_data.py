# Copyright 2013 Rackspace Hosting.
# Copyright 2015 HP Software, LLC
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

from troveclient.v1 import backups
from troveclient.v1 import clusters
from troveclient.v1 import configurations
from troveclient.v1 import databases
from troveclient.v1 import datastores
from troveclient.v1 import flavors
from troveclient.v1 import instances
from troveclient.v1 import users

from openstack_dashboard.test.test_data import utils


CLUSTER_DATA_ONE = {
    "status": "ACTIVE",
    "id": "dfbbd9ca-b5e1-4028-adb7-f78643e17998",
    "name": "Test Cluster",
    "created": "2014-04-25T20:19:23",
    "updated": "2014-04-25T20:19:23",
    "links": [],
    "datastore": {
        "type": "mongodb",
        "version": "2.6"
    },
    "ip": ["10.0.0.1"],
    "instances": [
        {
            "id": "416b0b16-ba55-4302-bbd3-ff566032e1c1",
            "shard_id": "5415b62f-f301-4e84-ba90-8ab0734d15a7",
            "name": "inst1",
            "status": "ACTIVE",
            "flavor": {
                "id": "7",
                "links": []
            },
            "volume": {
                "size": 100
            }
        },
        {
            "id": "965ef811-7c1d-47fc-89f2-a89dfdd23ef2",
            "shard_id": "5415b62f-f301-4e84-ba90-8ab0734d15a7",
            "name": "inst2",
            "status": "ACTIVE",
            "flavor": {
                "id": "7",
                "links": []
            },
            "volume": {
                "size": 100
            }
        },
        {
            "id": "3642f41c-e8ad-4164-a089-3891bf7f2d2b",
            "shard_id": "5415b62f-f301-4e84-ba90-8ab0734d15a7",
            "name": "inst3",
            "status": "ACTIVE",
            "flavor": {
                "id": "7",
                "links": []
            },
            "volume": {
                "size": 100
            }
        }
    ],
    "task": {
        "name": "test_task"
    },
    "locality": "anti-affinity"
}

CLUSTER_DATA_TWO = {
    "status": "ACTIVE",
    "id": "dfbbd9ca-b5e1-4028-adb7-f78199182122232",
    "name": "Test Cluster2",
    "created": "2014-04-25T20:19:23",
    "updated": "2014-04-25T20:19:23",
    "links": [],
    "datastore": {
        "type": "vertica",
        "version": "7.1"
    },
    "ip": ["10.0.0.1"],
    "instances": [
        {
            "id": "416b0b16-ba55-4302-bbd3-ff8199182122232",
            "name": "inst1",
            "status": "ACTIVE",
            "flavor": {
                "id": "7",
                "links": []
            },
            "volume": {
                "size": 100
            }
        },
        {
            "id": "965ef811-7c1d-47fc-89f2-a88199182122232",
            "name": "inst2",
            "status": "ACTIVE",
            "flavor": {
                "id": "7",
                "links": []
            },
            "volume": {
                "size": 100
            }
        },
        {
            "id": "3642f41c-e8ad-4164-a089-388199182122232",
            "name": "inst3",
            "status": "ACTIVE",
            "flavor": {
                "id": "7",
                "links": []
            },
            "volume": {
                "size": 100
            }
        }
    ],
    "task": {
        "name": "building"
    },
}

DATABASE_DATA_ONE = {
    "status": "ACTIVE",
    "updated": "2013-08-12T22:00:09",
    "name": "Test Database",
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
    "id": "6ddc36d9-73db-4e23-b52e-368937d72719",
    "locality": "anti-affinity"
}

DATABASE_DATA_TWO = {
    "status": "ACTIVE",
    "updated": "2013-08-12T22:00:09",
    "name": "Test Database With DNS",
    "links": [],
    "created": "2013-08-12T22:00:03",
    "hostname": "trove.instance-2.com",
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
        "version": "5.6"
    },
    "id": "4d7b3f57-44f5-41d2-8e86-36b88cad572a",
}

DATABASE_DATA_THREE = {
    "status": "ACTIVE",
    "updated": "2015-01-12T22:00:09",
    "name": "Test Database with Config",
    "links": [],
    "created": "2015-01-12T22:00:03",
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
    "id": "c3369597-b53a-4bd4-bf54-41957c1291b8",
    "configuration": {
        "id": "0ef978d3-7c83-4192-ab86-b7a0a5010fa0",
        "links": [],
        "name": "config1"
    },
    "replicas": {
        "id": "0ef978d3-7c83-4192-ab86-b7a0a5010fa0",
        "links": [],
    }
}

BACKUP_ONE = {
    "instance_id": "6ddc36d9-73db-4e23-b52e-368937d72719",
    "status": "COMPLETED",
    "updated": "2013-08-13T19:39:38",
    "locationRef": "http://swift/v1/AUTH/database_backups/0edb.tar.gz",
    "name": "backup1",
    "created": "2013-08-15T18:10:14",
    "size": 0.13,
    "id": "0edb3c14-8919-4583-9add-00df9e524081",
    "description": "Long description of backup",
}

BACKUP_TWO = {
    "instance_id": "4d7b3f57-44f5-41d2-8e86-36b88cad572a",
    "status": "COMPLETED",
    "updated": "2013-08-10T20:20:44",
    "locationRef": "http://swift/v1/AUTH/database_backups/e460.tar.gz",
    "name": "backup2",
    "created": "2013-08-10T20:20:37",
    "size": 0.13,
    "id": "e4602a3c-2bca-478f-b059-b6c215510fb4",
    "description": "Longer description of backup",
}

BACKUP_TWO_INC = {
    "instance_id": "4d7b3f57-44f5-41d2-8e86-36b88cad572a",
    "status": "COMPLETED",
    "updated": "2013-08-10T20:20:55",
    "locationRef": "http://swift/v1/AUTH/database_backups/f145.tar.gz",
    "name": "backup2-Incr",
    "created": "2013-08-10T20:20:37",
    "size": 0.13,
    "id": "e4602a3c-2bca-478f-b059-b6c215510fb5",
    "description": "Longer description of backup",
    "parent_id": "e4602a3c-2bca-478f-b059-b6c215510fb4",
}

CONFIG_ONE = {
    "updated": "2014-07-11T14:33:35",
    "name": "config1",
    "created": "2014-07-11T14:33:35",
    "instance_count": 1,
    "values": {
        "collation_server": "latin1_swedish_ci",
        "max_connections": 6000
    },
    "id": "0ef978d3-7c83-4192-ab86-b7a0a5010fa0",
    "description": "Long description of configuration one",
    "datastore_name": "mysql",
    "datastore_version_name": "5.5"
}

CONFIG_TWO = {
    "updated": "2014-08-11T14:33:35",
    "name": "config2",
    "created": "2014-08-11T14:33:35",
    "instance_count": 0,
    "values": {
        "collation_server": "latin1_swedish_ci",
        "max_connections": 5000
    },
    "id": "87948232-10e7-4636-a3d3-a5e1593b7d16",
    "description": "Long description of configuration two",
    "datastore_name": "mysql",
    "datastore_version_name": "5.6"
}

CONFIG_INSTANCE_ONE = {
    "id": "c3369597-b53a-4bd4-bf54-41957c1291b8",
    "name": "Test Database with Config",
}

CONFIG_PARAMS_ONE = [
    {
        "name": "autocommit",
        "restart_required": False,
        "max": 1,
        "min": 0,
        "type": "integer",
    },
    {
        "name": "connect_timeout",
        "restart_required": False,
        "max": 65535,
        "min": 1,
        "type": "integer",
    },
    {
        "name": "sort_buffer_size",
        "restart_required": False,
        "max": 18446744073709547520,
        "min": 32768,
        "type": "integer",
    },
    {
        "name": "character_set_client",
        "restart_required": False,
        "type": "string",
    },
    {
        "name": "character_set_connection",
        "restart_required": False,
        "type": "string",
    },
]

USER_ONE = {
    "name": "Test_User",
    "host": "%",
    "databases": [DATABASE_DATA_ONE["name"]],
}

USER_ROOT_ONE = {
    "name": "root",
    "rootEnabled": True
}

USER_DB_ONE = {
    "name": "db1",
}

DATASTORE_ONE = {
    "id": "537fb940-b5eb-40d9-bdbd-91a3dcb9c17d",
    "links": [],
    "name": "mysql"
}

DATASTORE_TWO = {
    "id": "ccb31517-c472-409d-89b4-1a13db6bdd36",
    "links": [],
    "name": "mysql"
}

DATASTORE_MONGODB = {
    "id": "ccb31517-c472-409d-89b4-1a13db6bdd37",
    "links": [],
    "name": "mongodb"
}

DATASTORE_REDIS = {
    "id": "ccb31517-c472-409d-89b4-1a13db6bdd38",
    "links": [],
    "name": "redis"
}

DATASTORE_VERTICA = {
    "id": "ccb31517-c472-409d-89b4-1a13db6bdd39",
    "links": [],
    "name": "vertica"
}

VERSION_ONE = {
    "name": "5.5",
    "links": [],
    "image": "b7956bb5-920e-4299-b68e-2347d830d939",
    "active": 1,
    "datastore": "537fb940-b5eb-40d9-bdbd-91a3dcb9c17d",
    "packages": "5.5",
    "id": "390a6d52-8347-4e00-8e4c-f4fa9cf96ae9"
}

VERSION_TWO = {
    "name": "5.6",
    "links": [],
    "image": "c7956bb5-920e-4299-b68e-2347d830d938",
    "datastore": "537fb940-b5eb-40d9-bdbd-91a3dcb9c17d",
    "packages": "5.6",
    "id": "500a6d52-8347-4e00-8e4c-f4fa9cf96ae9"
}

FLAVOR_ONE = {
    "ram": 512,
    "id": "1",
    "links": [],
    "name": "m1.tiny"
}

FLAVOR_TWO = {
    "ram": 768,
    "id": "10",
    "links": [],
    "name": "eph.rd-smaller"
}

FLAVOR_THREE = {
    "ram": 800,
    "id": "100",
    "links": [],
    "name": "test.1"
}

VERSION_MONGODB_2_6 = {
    "name": "2.6",
    "links": [],
    "image": "c7956bb5-920e-4299-b68e-2347d830d937",
    "active": 1,
    "datastore": "ccb31517-c472-409d-89b4-1a13db6bdd37",
    "packages": "2.6",
    "id": "600a6d52-8347-4e00-8e4c-f4fa9cf96ae9"
}

VERSION_REDIS_3_0 = {
    "name": "3.0",
    "links": [],
    "image": "c7956bb5-920e-4299-b68e-2347d830d938",
    "active": 1,
    "datastore": "ccb31517-c472-409d-89b4-1a13db6bdd38",
    "packages": "3.0",
    "id": "600a6d52-8347-4e00-8e4c-f4fa9cf96af0"
}

VERSION_VERTICA_7_1 = {
    "name": "7.1",
    "links": [],
    "image": "c7956bb5-920e-4299-b68e-2347d830d939",
    "active": 1,
    "datastore": "ccb31517-c472-409d-89b4-1a13db6bdd39",
    "packages": "7.1",
    "id": "600a6d52-8347-4e00-8e4c-f4fa9cf96af1"
}

LOG_1 = {
    "name": "guest",
    "type": "SYS",
    "status": "Partial",
    "published": 5000,
    "pending": 100,
    "container": "guest_container"
}

LOG_2 = {
    "name": "slow_query",
    "type": "USER",
    "status": "Disabled",
    "published": 0,
    "pending": 0,
    "container": "None"
}

LOG_3 = {
    "name": "error",
    "type": "SYS",
    "status": "Unavailable",
    "published": 0,
    "pending": 0,
    "container": "None"
}

LOG_4 = {
    "name": "general",
    "type": "USER",
    "status": "Ready",
    "published": 0,
    "pending": 1000,
    "container": "None"
}


def data(TEST):
    cluster1 = clusters.Cluster(clusters.Clusters(None),
                                CLUSTER_DATA_ONE)
    cluster2 = clusters.Cluster(clusters.Clusters(None),
                                CLUSTER_DATA_TWO)
    database1 = instances.Instance(instances.Instances(None),
                                   DATABASE_DATA_ONE)
    database2 = instances.Instance(instances.Instances(None),
                                   DATABASE_DATA_TWO)
    database3 = instances.Instance(instances.Instances(None),
                                   DATABASE_DATA_THREE)
    bkup1 = backups.Backup(backups.Backups(None), BACKUP_ONE)
    bkup2 = backups.Backup(backups.Backups(None), BACKUP_TWO)
    bkup3 = backups.Backup(backups.Backups(None), BACKUP_TWO_INC)

    cfg1 = configurations.Configuration(configurations.Configurations(None),
                                        CONFIG_ONE)
    cfg2 = configurations.Configuration(configurations.Configurations(None),
                                        CONFIG_TWO)

    user1 = users.User(users.Users(None), USER_ONE)
    user_db1 = databases.Database(databases.Databases(None),
                                  USER_DB_ONE)
    user_root1 = databases.Database(databases.Databases(None),
                                    USER_ROOT_ONE)

    datastore1 = datastores.Datastore(datastores.Datastores(None),
                                      DATASTORE_ONE)
    version1 = datastores.\
        DatastoreVersion(datastores.DatastoreVersions(None),
                         VERSION_ONE)
    version2 = datastores.\
        DatastoreVersion(datastores.DatastoreVersions(None),
                         VERSION_TWO)

    flavor1 = flavors.Flavor(flavors.Flavors(None), FLAVOR_ONE)
    flavor2 = flavors.Flavor(flavors.Flavors(None), FLAVOR_TWO)
    flavor3 = flavors.Flavor(flavors.Flavors(None), FLAVOR_THREE)
    datastore_mongodb = datastores.Datastore(datastores.Datastores(None),
                                             DATASTORE_MONGODB)
    version_mongodb_2_6 = datastores.\
        DatastoreVersion(datastores.DatastoreVersions(None),
                         VERSION_MONGODB_2_6)
    datastore_redis = datastores.Datastore(datastores.Datastores(None),
                                           DATASTORE_REDIS)
    version_redis_3_0 = datastores.\
        DatastoreVersion(datastores.DatastoreVersions(None),
                         VERSION_REDIS_3_0)
    datastore_vertica = datastores.Datastore(datastores.Datastores(None),
                                             DATASTORE_VERTICA)
    version_vertica_7_1 = datastores.\
        DatastoreVersion(datastores.DatastoreVersions(None),
                         VERSION_VERTICA_7_1)

    log1 = instances.DatastoreLog(instances.Instances(None), LOG_1)
    log2 = instances.DatastoreLog(instances.Instances(None), LOG_2)
    log3 = instances.DatastoreLog(instances.Instances(None), LOG_3)
    log4 = instances.DatastoreLog(instances.Instances(None), LOG_4)

    TEST.trove_clusters = utils.TestDataContainer()
    TEST.trove_clusters.add(cluster1)
    TEST.trove_clusters.add(cluster2)
    TEST.databases = utils.TestDataContainer()
    TEST.database_backups = utils.TestDataContainer()
    TEST.database_configurations = utils.TestDataContainer()
    TEST.database_users = utils.TestDataContainer()
    TEST.database_user_dbs = utils.TestDataContainer()
    TEST.database_user_roots = utils.TestDataContainer()
    TEST.database_flavors = utils.TestDataContainer()

    TEST.databases.add(database1)
    TEST.databases.add(database2)
    TEST.databases.add(database3)
    TEST.database_backups.add(bkup1)
    TEST.database_backups.add(bkup2)
    TEST.database_backups.add(bkup3)

    TEST.database_configurations.add(cfg1)
    TEST.database_configurations.add(cfg2)

    TEST.configuration_parameters = utils.TestDataContainer()
    for parameter in CONFIG_PARAMS_ONE:
        TEST.configuration_parameters.add(
            configurations.ConfigurationParameter(
                configurations.ConfigurationParameters(None), parameter))

    TEST.configuration_instances = utils.TestDataContainer()
    TEST.configuration_instances.add(
        configurations.Configuration(
            configurations.Configurations(None), CONFIG_INSTANCE_ONE))

    TEST.database_users.add(user1)
    TEST.database_user_dbs.add(user_db1)
    TEST.database_user_roots.add(user_root1)
    TEST.datastores = utils.TestDataContainer()
    TEST.datastores.add(datastore_mongodb)
    TEST.datastores.add(datastore_redis)
    TEST.datastores.add(datastore_vertica)
    TEST.datastores.add(datastore1)
    TEST.database_flavors.add(flavor1, flavor2, flavor3)
    TEST.datastore_versions = utils.TestDataContainer()
    TEST.datastore_versions.add(version_vertica_7_1)
    TEST.datastore_versions.add(version_redis_3_0)
    TEST.datastore_versions.add(version_mongodb_2_6)
    TEST.datastore_versions.add(version1)
    TEST.datastore_versions.add(version2)

    TEST.logs = utils.TestDataContainer()
    TEST.logs.add(log1, log2, log3, log4)
