# Copyright 2013 Rackspace Hosting
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

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import tables

from trove_dashboard import api


class CreateBackupStrategy(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Backup Strategy")
    url = "horizon:project:backup_strategies:create"
    classes = ("ajax-modal", "btn-create")
    icon = "camera"


class DeleteBackupStrategy(tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Backup Strategy",
            u"Delete Backup Strategies",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Backup Strategy Deleted",
            u"Backup Strategies Deleted",
            count
        )

    def delete(self, request, obj_id):
        api.trove.backup_strategy_delete(request, project_id=obj_id)


class BackupStrategiesTable(tables.DataTable):
    backend = tables.Column("backend", verbose_name=_("Backend"))
    instance_id = tables.Column("instance_id",
                                verbose_name=_("instance_id"))
    project_id = tables.Column("project_id",
                               verbose_name=_("Project"))
    swift_container = tables.Column("swift_container",
                                    verbose_name=_("Swift Container"))

    class Meta(object):
        name = "backup_strategies"
        verbose_name = _("Backup Strategies")
        table_actions = (CreateBackupStrategy, DeleteBackupStrategy,)
        row_actions = (DeleteBackupStrategy,)

    def get_object_display(self, backup_strategy):
        name = '(Project ID=%s' % backup_strategy.project_id
        if backup_strategy.instance_id:
            name += ', Instance ID= %s)' % backup_strategy.instance_id
        else:
            name += ')'
        return name

    def get_object_id(self, datum):
        return datum.project_id + datum.instance_id
