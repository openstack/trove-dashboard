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

from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tabs

from trove_dashboard import api
from trove_dashboard.content.database_configurations \
    import config_param_manager
from trove_dashboard.content.database_configurations \
    import tables


class DetailsTab(tabs.Tab):
    name = _("Details")
    slug = "details_tab"
    template_name = "project/database_configurations/_detail_overview.html"

    def get_context_data(self, request):
        return {"configuration": self.tab_group.kwargs['configuration']}


class ValuesTab(tabs.TableTab):
    table_classes = [tables.ValuesTable]
    name = _("Values")
    slug = "values_tab"
    template_name = "project/database_configurations/detail_param.html"

    def get_values_data(self):
        values_data = []
        manager = config_param_manager.get(
            self.request, self.tab_group.kwargs['configuration_id'])
        for k, v in manager.get_configuration().values.items():
            manager.add_param(k, v)
            values_data.append(manager.create_config_value(k, v))
        return values_data


class InstancesTab(tabs.TableTab):
    table_classes = [tables.InstancesTable]
    name = _("Instances")
    slug = "instances_tab"
    template_name = "horizon/common/_detail_table.html"

    def get_instances_data(self):
        configuration = self.tab_group.kwargs['configuration']
        try:
            data = api.trove.configuration_instances(self.request,
                                                     configuration.id)
        except Exception:
            msg = _('Unable to get configuration data.')
            exceptions.handle(self.request, msg)
            data = []
        return data


class ConfigurationDetailTabs(tabs.TabGroup):
    slug = "configuration_details"
    tabs = (ValuesTab, InstancesTab, DetailsTab)
    sticky = True
