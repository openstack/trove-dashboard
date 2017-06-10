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

import logging

from django import template
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tabs
from trove_dashboard import api
from trove_dashboard.content.database_configurations import (
    config_param_manager)
from trove_dashboard.content.databases import db_capability
from trove_dashboard.content.databases.logs import tables as log_tables
from trove_dashboard.content.databases import tables


LOG = logging.getLogger(__name__)


class OverviewTab(tabs.Tab):
    name = _("Overview")
    slug = "overview"

    def get_context_data(self, request):
        instance = self.tab_group.kwargs['instance']
        context = {"instance": instance}
        try:
            root_show = api.trove.root_show(request, instance.id)
            context["root_enabled"] = template.defaultfilters.yesno(
                root_show.rootEnabled)
        except Exception:
            context["root_enabled"] = _('Unable to obtain information on '
                                        'root user')
        return context

    def get_template_name(self, request):
        instance = self.tab_group.kwargs['instance']
        template_file = ('project/databases/_detail_overview_%s.html' %
                         self._get_template_type(instance.datastore['type']))
        try:
            template.loader.get_template(template_file)
            return template_file
        except template.TemplateDoesNotExist:
            # This datastore type does not have a template file
            # Just use the base template file
            return ('project/databases/_detail_overview.html')

    def _get_template_type(self, datastore):
        if db_capability.is_mysql_compatible(datastore):
            return 'mysql'

        return datastore


class UserTab(tabs.TableTab):
    table_classes = [tables.UsersTable]
    name = _("Users")
    slug = "users_tab"
    instance = None
    template_name = "horizon/common/_detail_table.html"
    preload = False

    def get_users_data(self):
        instance = self.tab_group.kwargs['instance']
        try:
            data = api.trove.users_list(self.request, instance.id)
            for user in data:
                user.instance = instance
                try:
                    user.access = api.trove.user_list_access(self.request,
                                                             instance.id,
                                                             user.name,
                                                             host=user.host)
                except exceptions.NOT_FOUND:
                    pass
                except Exception:
                    msg = _('Unable to get user access data.')
                    exceptions.handle(self.request, msg)
        except Exception:
            msg = _('Unable to get user data.')
            exceptions.handle(self.request, msg)
            data = []
        return data

    def allowed(self, request):
        return tables.has_user_add_perm(request)


class DatabaseTab(tabs.TableTab):
    table_classes = [tables.DatabaseTable]
    name = _("Databases")
    slug = "database_tab"
    instance = None
    template_name = "horizon/common/_detail_table.html"
    preload = False

    def get_databases_data(self):
        instance = self.tab_group.kwargs['instance']
        try:
            data = api.trove.database_list(self.request, instance.id)
            add_instance = lambda d: setattr(d, 'instance', instance)
            map(add_instance, data)
        except Exception:
            msg = _('Unable to get databases data.')
            exceptions.handle(self.request, msg)
            data = []
        return data

    def allowed(self, request):
        return tables.has_database_add_perm(request)


class ConfigDefaultsTab(tabs.TableTab):
    table_classes = [tables.ConfigDefaultsTable]
    name = _("Defaults")
    slug = "config_defaults"
    instance = None
    template_name = "horizon/common/_detail_table.html"
    preload = False

    def get_config_defaults_data(self):
        instance = self.tab_group.kwargs['instance']
        values_data = []
        data = api.trove.configuration_default(self.request, instance.id)
        if data is not None:
            for k, v in data.configuration.items():
                values_data.append(
                    config_param_manager.ConfigParam(None, k, v))
        return sorted(values_data, key=lambda config: config.name)


class BackupsTab(tabs.TableTab):
    table_classes = [tables.InstanceBackupsTable]
    name = _("Backups")
    slug = "backups_tab"
    instance = None
    template_name = "horizon/common/_detail_table.html"
    preload = False

    def get_backups_data(self):
        instance = self.tab_group.kwargs['instance']
        try:
            data = api.trove.instance_backups(self.request, instance.id)
        except Exception:
            msg = _('Unable to get database backup data.')
            exceptions.handle(self.request, msg)
            data = []
        return data

    def allowed(self, request):
        return request.user.has_perm('openstack.services.object-store')


class LogsTab(tabs.TableTab):
    table_classes = [log_tables.LogsTable]
    name = _("Logs")
    slug = "logs_tab"
    template_name = "horizon/common/_detail_table.html"
    preload = False

    def get_logs_data(self):
        instance = self.tab_group.kwargs['instance']
        try:
            logs = api.trove.log_list(self.request, instance.id)
            return logs
        except Exception as e:
            LOG.exception(
                _('Unable to retrieve list of logs.\n%s') % e.message)
            logs = []
        return logs


class InstanceDetailTabs(tabs.TabGroup):
    slug = "instance_details"
    tabs = (OverviewTab, UserTab, DatabaseTab, BackupsTab, LogsTab,
            ConfigDefaultsTab)
    sticky = True
