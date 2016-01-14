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

import logging

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon.utils import memoized

from trove_dashboard import api
from trove_dashboard.content.database_configurations \
    import config_param_manager

LOG = logging.getLogger(__name__)


class CreateConfigurationForm(forms.SelfHandlingForm):
    name = forms.CharField(label=_("Name"))
    description = forms.CharField(label=_("Description"), required=False)
    datastore = forms.ChoiceField(
        label=_("Datastore"),
        help_text=_("Type and version of datastore."))

    def __init__(self, request, *args, **kwargs):
        super(CreateConfigurationForm, self).__init__(request, *args, **kwargs)

        choices = self.get_datastore_choices(request)
        self.fields['datastore'].choices = choices

    @memoized.memoized_method
    def datastores(self, request):
        try:
            return api.trove.datastore_list(request)
        except Exception:
            LOG.exception("Exception while obtaining datastores list")
            redirect = reverse('horizon:project:database_configurations:index')
            exceptions.handle(request,
                              _('Unable to obtain datastores.'),
                              redirect=redirect)

    @memoized.memoized_method
    def datastore_versions(self, request, datastore):
        try:
            return api.trove.datastore_version_list(request, datastore)
        except Exception:
            LOG.exception("Exception while obtaining datastore version list")
            redirect = reverse('horizon:project:database_configurations:index')
            exceptions.handle(request,
                              _('Unable to obtain datastore versions.'),
                              redirect=redirect)

    def get_datastore_choices(self, request):
        choices = ()
        set_initial = False
        datastores = self.datastores(request)
        if datastores is not None:
            num_datastores_with_one_version = 0
            for ds in datastores:
                versions = self.datastore_versions(request, ds.name)
                if not set_initial:
                    if len(versions) >= 2:
                        set_initial = True
                    elif len(versions) == 1:
                        num_datastores_with_one_version += 1
                        if num_datastores_with_one_version > 1:
                            set_initial = True
                if len(versions) > 0:
                    # only add to choices if datastore has at least one version
                    version_choices = ()
                    for v in versions:
                        version_choices = (version_choices +
                                           ((ds.name + ',' + v.name, v.name),))
                    datastore_choices = (ds.name, version_choices)
                    choices = choices + (datastore_choices,)
            if set_initial:
                # prepend choice to force user to choose
                initial = ('', _('Select datastore type and version'))
                choices = (initial,) + choices
        return choices

    def handle(self, request, data):
        try:
            datastore = data['datastore'].split(',')[0]
            datastore_version = data['datastore'].split(',')[1]

            api.trove.configuration_create(request, data['name'], "{}",
                                           description=data['description'],
                                           datastore=datastore,
                                           datastore_version=datastore_version)

            messages.success(request, _('Created configuration group'))
        except Exception as e:
            redirect = reverse("horizon:project:database_configurations:index")
            exceptions.handle(request, _('Unable to create configuration '
                                         'group. %s')
                              % e.message, redirect=redirect)
        return True


class AddParameterForm(forms.SelfHandlingForm):
    name = forms.ChoiceField(label=_("Name"))
    value = forms.CharField(label=_("Value"))

    def __init__(self, request, *args, **kwargs):
        super(AddParameterForm, self).__init__(request, *args, **kwargs)

        configuration = (config_param_manager
                         .get(request, kwargs["initial"]["configuration_id"])
                         .get_configuration())

        self.fields['name'].choices = self.get_parameters(
            request, configuration.datastore_name,
            configuration.datastore_version_name)

        self.fields['value'].parameters = self.parameters

    @memoized.memoized_method
    def parameters(self, request, datastore, datastore_version):
        try:
            return api.trove.configuration_parameters_list(
                request, datastore, datastore_version)
        except Exception:
            LOG.exception(
                "Exception while obtaining configuration parameter list")
            redirect = reverse('horizon:project:database_configurations:index')
            exceptions.handle(request,
                              _('Unable to obtain list of parameters.'),
                              redirect=redirect)

    def get_parameters(self, request, datastore, datastore_version):
        try:
            choices = []

            self.parameters = self.parameters(
                request, datastore, datastore_version)
            for parameter in self.parameters:
                choices.append((parameter.name, parameter.name))

            return sorted(choices)
        except Exception:
            LOG.exception(
                "Exception while obtaining configuration parameters list")
            redirect = reverse('horizon:project:database_configurations:index')
            exceptions.handle(request,
                              _('Unable to create list of parameters.'),
                              redirect=redirect)

    def clean(self):
        cleaned_data = super(AddParameterForm, self).clean()

        if "value" in cleaned_data:
            config_param = config_param_manager.find_parameter(
                cleaned_data["name"], self.parameters)
            if config_param:
                error_msg = config_param_manager.validate_config_param_value(
                    config_param, cleaned_data["value"])
                if error_msg:
                    self._errors['value'] = self.error_class([error_msg])
        return cleaned_data

    def handle(self, request, data):
        try:
            (config_param_manager
                .get(request, self.initial["configuration_id"])
                .add_param(data["name"],
                           config_param_manager.adjust_type(
                               config_param_manager.find_parameter(
                                   data["name"], self.parameters).type,
                               data["value"])))
            messages.success(request, _('Successfully added parameter'))
        except Exception as e:
            redirect = reverse("horizon:project:database_configurations:index")
            exceptions.handle(request, _('Unable to add new parameter: %s')
                              % e.message, redirect=redirect)
        return True
