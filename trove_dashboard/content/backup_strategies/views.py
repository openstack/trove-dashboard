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

"""
Views for displaying database backups.
"""
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tables as horizon_tables

from trove_dashboard import api
from trove_dashboard.content.backup_strategies import tables


class IndexView(horizon_tables.DataTableView):
    table_class = tables.BackupStrategiesTable
    template_name = 'project/backup_strategies/index.html'
    page_title = _("Backup Strategies")

    def get_data(self):
        try:
            backups = api.trove.backup_strategy_list(self.request)
        except Exception:
            backups = []
            msg = _('Error getting backup strategies list.')
            exceptions.handle(self.request, msg)
        return backups
