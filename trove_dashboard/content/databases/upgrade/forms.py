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

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages

from trove_dashboard import api


class UpgradeInstanceForm(forms.SelfHandlingForm):
    instance_name = forms.CharField(widget=forms.HiddenInput())
    old_datastore_version = forms.CharField(
        label=_("Current Version"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    new_datastore_version = forms.ChoiceField(
        label=_("New Version"))

    def __init__(self, request, *args, **kwargs):
        self.instance_id = kwargs.pop('instance_id')
        super(UpgradeInstanceForm, self).__init__(request, *args, **kwargs)

        initial = kwargs.get('initial', {})
        self.fields['instance_name'].initial = initial.get('instance_name')
        current_datastore_version = initial.get('old_version_name')
        self.fields['old_datastore_version'].initial = (
            current_datastore_version)
        datastore_versions = initial.get('datastore_versions') or []
        choices = [(dsv.id, dsv.name) for dsv in datastore_versions]
        self.fields['new_datastore_version'].choices = choices

    def handle(self, request, data):
        new_datastore_version = data.get('new_datastore_version')
        try:
            api.trove.instance_upgrade(
                request, self.instance_id, new_datastore_version)
            messages.success(
                request, _('Upgrading "%s"') % data.get('instance_name'))
        except Exception as e:
            redirect = reverse("horizon:project:databases:index")
            exceptions.handle(
                request,
                _('Unable to upgrade instance. %s') % str(e),
                redirect=redirect)
        return True
