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

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms as horizon_forms
from horizon import tables as horizon_tables
from horizon import tabs as horizon_tabs
from horizon.utils import memoized

from trove_dashboard import api
from trove_dashboard.content.database_configurations \
    import config_param_manager
from trove_dashboard.content.database_configurations \
    import forms
from trove_dashboard.content.database_configurations \
    import tables
from trove_dashboard.content.database_configurations \
    import tabs


class IndexView(horizon_tables.DataTableView):
    table_class = tables.ConfigurationsTable
    template_name = 'project/database_configurations/index.html'
    page_title = _("Configuration Groups")

    def get_data(self):
        try:
            configurations = api.trove.configuration_list(self.request)
        except Exception:
            configurations = []
            msg = _('Error getting configuration group list.')
            exceptions.handle(self.request, msg)
        return configurations


class DetailView(horizon_tabs.TabbedTableView):
    tab_group_class = tabs.ConfigurationDetailTabs
    template_name = "project/database_configurations/details.html"
    page_title = _("Configuration Group Details: {{configuration.name}}")

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        context["configuration"] = self.get_data()
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            configuration_id = self.kwargs['configuration_id']
            return (config_param_manager
                    .get(self.request, configuration_id)
                    .configuration_get(self.request))
        except Exception:
            redirect = reverse('horizon:project:database_configurations:index')
            msg = _('Unable to retrieve details for configuration '
                    'group: %s') % configuration_id
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_tabs(self, request, *args, **kwargs):
        configuration = self.get_data()
        return self.tab_group_class(request,
                                    configuration=configuration,
                                    **kwargs)


class CreateConfigurationView(horizon_forms.ModalFormView):
    form_class = forms.CreateConfigurationForm
    form_id = "create_configuration_form"
    modal_header = _("Create Configuration Group")
    modal_id = "create_configuration_modal"
    template_name = 'project/database_configurations/create.html'
    submit_label = "Create Configuration Group"
    submit_url = reverse_lazy('horizon:project:database_configurations:create')
    success_url = reverse_lazy('horizon:project:database_configurations:index')


class AddParameterView(horizon_forms.ModalFormView):
    form_class = forms.AddParameterForm
    form_id = "add_parameter_form"
    modal_header = _("Add Parameter")
    modal_id = "add_parameter_modal"
    template_name = 'project/database_configurations/add_parameter.html'
    submit_label = "Add Parameter"
    submit_url = 'horizon:project:database_configurations:add'
    success_url = 'horizon:project:database_configurations:detail'

    def get_success_url(self):
        return reverse(self.success_url,
                       args=(self.kwargs['configuration_id'],))

    def get_context_data(self, **kwargs):
        context = super(AddParameterView, self).get_context_data(**kwargs)
        context["configuration_id"] = self.kwargs['configuration_id']
        args = (self.kwargs['configuration_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        configuration_id = self.kwargs['configuration_id']
        return {'configuration_id': configuration_id}
