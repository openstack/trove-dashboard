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

from django.core import urlresolvers
from django import shortcuts
from django.template.defaultfilters import title  # noqa
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import messages
from horizon import tables
from horizon.templatetags import sizeformat
from horizon.utils import filters
from horizon.utils import functions
from horizon.utils import memoized

from trove_dashboard import api
from trove_dashboard.content.database_clusters import cluster_manager
from trove_dashboard.content.databases import db_capability

LOG = logging.getLogger(__name__)

ACTIVE_STATES = ("ACTIVE",)


class DeleteCluster(tables.BatchAction):
    name = "delete"
    icon = "remove"
    classes = ('btn-danger',)
    help_text = _("Deleted cluster is not recoverable.")

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Cluster",
            u"Delete Clusters",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled deletion of Cluster",
            u"Scheduled deletion of Clusters",
            count
        )

    def action(self, request, obj_id):
        api.trove.cluster_delete(request, obj_id)


class LaunchLink(tables.LinkAction):
    name = "launch"
    verbose_name = _("Launch Cluster")
    url = "horizon:project:database_clusters:launch"
    classes = ("btn-launch", "ajax-modal")
    icon = "cloud-upload"


class ClusterGrow(tables.LinkAction):
    name = "cluster_grow"
    verbose_name = _("Grow Cluster")
    url = "horizon:project:database_clusters:cluster_grow_details"

    def allowed(self, request, cluster=None):
        if (cluster and cluster.task["name"] == 'NONE' and
                db_capability.can_modify_cluster(cluster.datastore['type'])):
            return True
        return False


class ClusterShrink(tables.LinkAction):
    name = "cluster_shrink"
    verbose_name = _("Shrink Cluster")
    url = "horizon:project:database_clusters:cluster_shrink_details"

    def allowed(self, request, cluster=None):
        if (cluster and cluster.task["name"] == 'NONE' and
                db_capability.can_modify_cluster(cluster.datastore['type'])):
            return True
        return False


class ResetPassword(tables.LinkAction):
    name = "reset_password"
    verbose_name = _("Reset Root Password")
    url = "horizon:project:database_clusters:reset_password"
    classes = ("ajax-modal",)

    def allowed(self, request, cluster=None):
        if (cluster and cluster.task["name"] == 'NONE' and
                db_capability.is_vertica_datastore(cluster.datastore['type'])):
            return True
        return False

    def get_link_url(self, datum):
        cluster_id = self.table.get_object_id(datum)
        return urlresolvers.reverse(self.url, args=[cluster_id])


class UpdateRow(tables.Row):
    ajax = True

    @memoized.memoized_method
    def get_data(self, request, cluster_id):
        cluster = api.trove.cluster_get(request, cluster_id)
        try:
            # TODO(michayu): assumption that cluster is homogeneous
            flavor_id = cluster.instances[0]['flavor']['id']
            cluster.full_flavor = api.trove.flavor_get(request, flavor_id)
        except Exception:
            pass
        return cluster


def get_datastore(cluster):
    return cluster.datastore["type"]


def get_datastore_version(cluster):
    return cluster.datastore["version"]


def get_size(cluster):
    if db_capability.is_vertica_datastore(cluster.datastore['type']):
        return "3"

    if hasattr(cluster, "full_flavor"):
        size_string = _("%(name)s | %(RAM)s RAM | %(instances)s instances")
        vals = {'name': cluster.full_flavor.name,
                'RAM': sizeformat.mbformat(cluster.full_flavor.ram),
                'instances': len(cluster.instances)}
        return size_string % vals
    elif hasattr(cluster, "instances"):
        return "%s instances" % len(cluster.instances)
    return _("Not available")


def get_task(cluster):
    return cluster.task["name"]


class ClustersTable(tables.DataTable):
    TASK_CHOICES = (
        ("none", True),
    )
    name = tables.Column("name",
                         link=("horizon:project:database_clusters:detail"),
                         verbose_name=_("Cluster Name"))
    datastore = tables.Column(get_datastore,
                              verbose_name=_("Datastore"))
    datastore_version = tables.Column(get_datastore_version,
                                      verbose_name=_("Datastore Version"))
    size = tables.Column(get_size,
                         verbose_name=_("Cluster Size"),
                         attrs={'data-type': 'size'})
    task = tables.Column(get_task,
                         filters=(title, filters.replace_underscores),
                         verbose_name=_("Current Task"),
                         status=True,
                         status_choices=TASK_CHOICES)

    class Meta(object):
        name = "clusters"
        verbose_name = _("Clusters")
        status_columns = ["task"]
        row_class = UpdateRow
        table_actions = (LaunchLink, DeleteCluster)
        row_actions = (ClusterGrow, ClusterShrink, ResetPassword,
                       DeleteCluster)


def get_instance_size(instance):
    if hasattr(instance, "full_flavor"):
        size_string = _("%(name)s | %(RAM)s RAM")
        vals = {'name': instance.full_flavor.name,
                'RAM': sizeformat.mbformat(instance.full_flavor.ram)}
        return size_string % vals
    return _("Not available")


def get_instance_type(instance):
    if hasattr(instance, "type"):
        return instance.type
    return _("Not available")


def get_host(instance):
    if hasattr(instance, "hostname"):
        return instance.hostname
    elif hasattr(instance, "ip") and instance.ip:
        return instance.ip[0]
    return _("Not Assigned")


class InstancesTable(tables.DataTable):
    name = tables.Column("name",
                         verbose_name=_("Name"))
    type = tables.Column(get_instance_type,
                         verbose_name=_("Type"))
    host = tables.Column(get_host,
                         verbose_name=_("Host"))
    size = tables.Column(get_instance_size,
                         verbose_name=_("Size"),
                         attrs={'data-type': 'size'})
    status = tables.Column("status",
                           filters=(title, filters.replace_underscores),
                           verbose_name=_("Status"))

    class Meta(object):
        name = "instances"
        verbose_name = _("Instances")


class ClusterShrinkAction(tables.BatchAction):
    name = "cluster_shrink_action"
    icon = "remove"
    classes = ('btn-danger',)
    success_url = 'horizon:project:database_clusters:index'
    help_text = _("Shrinking a cluster is not recoverable.")

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Shrink Cluster",
            u"Shrink Cluster",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled Shrinking of Cluster",
            u"Scheduled Shrinking of Cluster",
            count
        )

    def handle(self, table, request, obj_ids):
        datum_display_objs = []
        for datum_id in obj_ids:
            datum = table.get_object_by_id(datum_id)
            datum_display = table.get_object_display(datum) or datum_id
            datum_display_objs.append(datum_display)
        display_str = functions.lazy_join(", ", datum_display_objs)

        try:
            cluster_id = table.kwargs['cluster_id']
            data = [{'id': instance_id} for instance_id in obj_ids]
            api.trove.cluster_shrink(request, cluster_id, data)
            LOG.info('%s: "%s"' %
                     (self._get_action_name(past=True),
                      display_str))
            msg = _('Removed instances from cluster.')
            messages.info(request, msg)
        except Exception as ex:
            LOG.error('Action %(action)s failed with %(ex)s for %(data)s' %
                      {'action': self._get_action_name(past=True).lower(),
                       'ex': ex.message,
                       'data': display_str})
            msg = _('Unable to remove instances from cluster: %s')
            messages.error(request, msg % ex.message)

        return shortcuts.redirect(self.get_success_url(request))


class ClusterShrinkInstancesTable(tables.DataTable):
    name = tables.Column("name",
                         verbose_name=_("Name"))
    status = tables.Column("status",
                           filters=(title, filters.replace_underscores),
                           verbose_name=_("Status"))

    class Meta(object):
        name = "shrink_cluster_table"
        verbose_name = _("Instances")
        table_actions = (ClusterShrinkAction,)
        row_actions = (ClusterShrinkAction,)


class ClusterGrowAddInstance(tables.LinkAction):
    name = "cluster_grow_add_instance"
    verbose_name = _("Add Instance")
    url = "horizon:project:database_clusters:add_instance"
    classes = ("ajax-modal",)

    def get_link_url(self):
        return urlresolvers.reverse(
            self.url, args=[self.table.kwargs['cluster_id']])


class ClusterGrowRemoveInstance(tables.BatchAction):
    name = "cluster_grow_remove_instance"

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Remove Instance",
            u"Remove Instances",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Removed Instance",
            u"Removed Instances",
            count
        )

    def action(self, request, datum_id):
        manager = cluster_manager.get(self.table.kwargs['cluster_id'])
        manager.delete_instance(datum_id)

    def handle(self, table, request, obj_ids):
        action_success = []
        action_failure = []
        action_not_allowed = []
        for datum_id in obj_ids:
            datum = table.get_object_by_id(datum_id)
            datum_display = table.get_object_display(datum) or datum_id
            if not table._filter_action(self, request, datum):
                action_not_allowed.append(datum_display)
                LOG.warning('Permission denied to %s: "%s"' %
                            (self._get_action_name(past=True).lower(),
                             datum_display))
                continue
            try:
                self.action(request, datum_id)
                # Call update to invoke changes if needed
                self.update(request, datum)
                action_success.append(datum_display)
                self.success_ids.append(datum_id)
                LOG.info('%s: "%s"' %
                         (self._get_action_name(past=True), datum_display))
            except Exception as ex:
                # Handle the exception but silence it since we'll display
                # an aggregate error message later. Otherwise we'd get
                # multiple error messages displayed to the user.
                action_failure.append(datum_display)
                action_description = (
                    self._get_action_name(past=True).lower(), datum_display)
                LOG.error(
                    'Action %(action)s Failed for %(reason)s', {
                        'action': action_description, 'reason': ex})

        if action_not_allowed:
            msg = _('You are not allowed to %(action)s: %(objs)s')
            params = {"action":
                      self._get_action_name(action_not_allowed).lower(),
                      "objs": functions.lazy_join(", ", action_not_allowed)}
            messages.error(request, msg % params)
        if action_failure:
            msg = _('Unable to %(action)s: %(objs)s')
            params = {"action": self._get_action_name(action_failure).lower(),
                      "objs": functions.lazy_join(", ", action_failure)}
            messages.error(request, msg % params)

        return shortcuts.redirect(self.get_success_url(request))


class ClusterGrowAction(tables.Action):
    name = "grow_cluster_action"
    verbose_name = _("Grow Cluster")
    verbose_name_plural = _("Grow Cluster")
    requires_input = False
    icon = "plus"

    def handle(self, table, request, obj_ids):
        if not table.data:
            msg = _("Cannot grow cluster.  No instances specified.")
            messages.info(request, msg)
            return shortcuts.redirect(request.build_absolute_uri())

        datum_display_objs = []
        for instance in table.data:
            msg = _("[flavor=%(flavor)s, volume=%(volume)s, name=%(name)s, "
                    "type=%(type)s, related_to=%(related_to)s]")
            params = {"flavor": instance.flavor_id, "volume": instance.volume,
                      "name": instance.name, "type": instance.type,
                      "related_to": instance.related_to}
            datum_display_objs.append(msg % params)
        display_str = functions.lazy_join(", ", datum_display_objs)

        cluster_id = table.kwargs['cluster_id']
        try:
            api.trove.cluster_grow(request, cluster_id, table.data)
            LOG.info('%s: "%s"' % (_("Grow Cluster"), display_str))
            msg = _('Scheduled growing of cluster.')
            messages.success(request, msg)
        except Exception as ex:
            LOG.error('Action grow cluster failed with %(ex)s for %(data)s' %
                      {'ex': ex.message,
                       'data': display_str})
            msg = _('Unable to grow cluster: %s')
            messages.error(request, msg % ex.message)
        finally:
            cluster_manager.delete(cluster_id)

        return shortcuts.redirect(urlresolvers.reverse(
            "horizon:project:database_clusters:index"))


class ClusterGrowInstancesTable(tables.DataTable):
    id = tables.Column("id", hidden=True)
    name = tables.Column("name", verbose_name=_("Name"))
    flavor = tables.Column("flavor", verbose_name=_("Flavor"))
    flavor_id = tables.Column("flavor_id", hidden=True)
    volume = tables.Column("volume", verbose_name=_("Volume"))
    type = tables.Column("type", verbose_name=_("Instance Type"))
    related_to = tables.Column("related_to", verbose_name=_("Related To"))

    class Meta(object):
        name = "cluster_grow_instances_table"
        verbose_name = _("Instances")
        table_actions = (ClusterGrowAddInstance, ClusterGrowRemoveInstance,
                         ClusterGrowAction)
        row_actions = (ClusterGrowRemoveInstance,)
