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
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horizon import exceptions
from horizon import forms as horizon_forms

from horizon.utils import memoized

from trove_dashboard import api
from trove_dashboard.content.databases.upgrade import forms


class UpgradeInstanceView(horizon_forms.ModalFormView):
    form_class = forms.UpgradeInstanceForm
    form_id = "upgrade_instance_form"
    modal_header = _("Upgrade Instance")
    modal_id = "upgrade_instance_modal"
    template_name = "project/databases/upgrade/upgrade_instance.html"
    submit_url = 'horizon:project:databases:upgrade:upgrade_instance'
    success_url = reverse_lazy('horizon:project:databases:index')

    def get_form_kwargs(self):
        kwargs = super(UpgradeInstanceView, self).get_form_kwargs()
        kwargs['instance_id'] = self.kwargs['instance_id']
        return kwargs

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        instance_id = self.kwargs['instance_id']

        try:
            return api.trove.instance_get(self.request, instance_id)
        except Exception:
            redirect = reverse('horizon:project:databases:index')
            msg = _('Unable to retrieve instance details.')
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_context_data(self, **kwargs):
        context = super(UpgradeInstanceView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        args = (self.kwargs['instance_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    @memoized.memoized_method
    def get_datastore_versions(self, datastore, *args, **kwargs):
        try:
            return api.trove.datastore_version_list(self.request, datastore)
        except Exception:
            redirect = reverse("horizon:project:databases:index")
            exceptions.handle(self.request,
                              _('Unable to retrieve datastore versions.'),
                              redirect=redirect)

    def get_initial(self):
        initial = super(UpgradeInstanceView, self).get_initial()
        obj = self.get_object()
        if obj:
            initial.update({'instance_id': self.kwargs['instance_id'],
                            'instance_name': obj.name,
                            'old_version_name': obj.datastore['version'],
                            'datastore_versions': self.get_datastore_versions(
                                obj.datastore['type'])})
        return initial
