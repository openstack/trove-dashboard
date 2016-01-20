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


from django.core import cache


def get(cluster_id):
    if not has_cluster(cluster_id):
        manager = ClusterInstanceManager(cluster_id)
        cache.cache.set(cluster_id, manager)

    return cache.cache.get(cluster_id)


def delete(cluster_id):
    manager = get(cluster_id)
    manager.clear_instances()
    cache.cache.delete(cluster_id)


def update(cluster_id, manager):
    cache.cache.set(cluster_id, manager)


def has_cluster(cluster_id):
    if cache.cache.get(cluster_id):
        return True
    else:
        return False


class ClusterInstanceManager(object):

    instances = []

    def __init__(self, cluster_id):
        self.cluster_id = cluster_id

    def get_instances(self):
        return self.instances

    def get_instance(self, id):
        for instance in self.instances:
            if instance.id == id:
                return instance
        return None

    def add_instance(self, id, name, flavor_id,
                     flavor, volume, type, related_to):
        instance = ClusterInstance(id, name, flavor_id, flavor,
                                   volume, type, related_to)
        self.instances.append(instance)
        update(self.cluster_id, self)
        return self.instances

    def delete_instance(self, id):
        instance = self.get_instance(id)
        if instance:
            self.instances.remove(instance)
            update(self.cluster_id, self)

    def clear_instances(self):
        del self.instances[:]


class ClusterInstance(object):
    def __init__(self, id, name, flavor_id, flavor, volume, type, related_to):
        self.id = id
        self.name = name
        self.flavor_id = flavor_id
        self.flavor = flavor
        self.volume = volume
        self.type = type
        self.related_to = related_to
