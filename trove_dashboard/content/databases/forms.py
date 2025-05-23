# Copyright 2014 Tesora Inc.
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

from django.forms import ValidationError  # noqa
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon.utils import validators

from trove_dashboard import api


class CreateDatabaseForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    name = forms.CharField(label=_("Name"))
    character_set = forms.CharField(
        label=_("Character Set"), required=False,
        help_text=_("Optional character set for the database."))
    collation = forms.CharField(
        label=_("Collation"), required=False,
        help_text=_("Optional collation type for the database."))

    def handle(self, request, data):
        instance = data.get('instance_id')
        try:
            api.trove.database_create(request, instance, data['name'],
                                      character_set=data['character_set'],
                                      collation=data['collation'])

            messages.success(request,
                             _('Created database "%s".') % data['name'])
        except Exception:
            redirect = reverse("horizon:project:databases:detail",
                               args=(instance,))
            exceptions.handle(request, _('Unable to create database.'),
                              redirect=redirect)
        return True


class ResizeVolumeForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    orig_size = forms.IntegerField(
        label=_("Current Size (GB)"),
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False,
    )
    new_size = forms.IntegerField(label=_("New Size (GB)"))

    def __init__(self, request, *args, **kwargs):
        super(ResizeVolumeForm, self).__init__(request, *args, **kwargs)

        self.fields['instance_id'].initial = (kwargs.get('initial', {}).
                                              get('instance_id'))
        self.fields['orig_size'].initial = (kwargs.get('initial', {}).
                                            get('orig_size'))

    def clean(self):
        cleaned_data = super(ResizeVolumeForm, self).clean()
        new_size = cleaned_data.get('new_size')
        if new_size <= self.initial['orig_size']:
            raise ValidationError(
                _("New size for volume must be greater than current size."))

        return cleaned_data

    def handle(self, request, data):
        instance = data.get('instance_id')
        try:
            api.trove.instance_resize_volume(request,
                                             instance,
                                             data['new_size'])

            messages.success(request, _('Resizing volume "%s"') % instance)
        except Exception:
            redirect = reverse("horizon:project:databases:index")
            exceptions.handle(request, _('Unable to resize volume.'),
                              redirect=redirect)
        return True


class ResizeInstanceForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    old_flavor_name = forms.CharField(label=_("Old Flavor"),
                                      required=False,
                                      widget=forms.TextInput(
                                      attrs={'readonly': 'readonly'}))
    new_flavor = forms.ChoiceField(label=_("New Flavor"),
                                   help_text=_("Choose a new instance "
                                               "flavor."))

    def __init__(self, request, *args, **kwargs):
        super(ResizeInstanceForm, self).__init__(request, *args, **kwargs)

        old_flavor_id = kwargs.get('initial', {}).get('old_flavor_id')
        choices = kwargs.get('initial', {}).get('flavors')
        # Remove current flavor from the list of flavor choices
        choices = [(flavor_id, name) for (flavor_id, name) in choices
                   if flavor_id != old_flavor_id]
        if choices:
            choices.insert(0, ("", _("Select a new flavor")))
        else:
            choices.insert(0, ("", _("No flavors available")))
        self.fields['new_flavor'].choices = choices

    def handle(self, request, data):
        instance = data.get('instance_id')
        flavor = data.get('new_flavor')
        try:
            api.trove.instance_resize(request, instance, flavor)

            messages.success(request, _('Resizing instance "%s"') % instance)
        except Exception:
            redirect = reverse("horizon:project:databases:index")
            exceptions.handle(request, _('Unable to resize instance.'),
                              redirect=redirect)
        return True


class PromoteToReplicaSourceForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())

    def handle(self, request, data):
        instance_id = data.get('instance_id')
        name = self.initial['replica'].name
        try:
            api.trove.promote_to_replica_source(request, instance_id)
            messages.success(
                request,
                _('Promoted replica "%s" as the new replica source.') % name)
        except Exception:
            redirect = reverse("horizon:project:databases:index")
            exceptions.handle(
                request,
                _('Unable to promote replica as the new replica source.'),
                redirect=redirect)
        return True


class CreateUserForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    name = forms.CharField(label=_("Name"))
    password = forms.RegexField(
        label=_("Password"),
        widget=forms.PasswordInput(render_value=False),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    host = forms.CharField(
        label=_("Host"), required=False, help_text=_("Optional host of user."))
    databases = forms.CharField(
        label=_('Initial Databases'), required=False,
        help_text=_('Optional comma separated list of databases user has '
                    'access to.'))

    def handle(self, request, data):
        instance = data.get('instance_id')
        try:
            api.trove.user_create(
                request,
                instance,
                data['name'],
                data['password'],
                host=data['host'],
                databases=self._get_databases(data))

            messages.success(request,
                             _('Created user "%s".') % data['name'])
        except Exception:
            redirect = reverse("horizon:project:databases:detail",
                               args=(instance,))
            exceptions.handle(request, _('Unable to create user.'),
                              redirect=redirect)
        return True

    def _get_databases(self, data):
        databases = []
        db_value = data['databases']
        if db_value and db_value != '':
            dbs = data['databases']
            databases = [{'name': d.strip()} for d in dbs.split(',')]
        return databases


class EditUserForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    user_name = forms.CharField(
        label=_("Name"),
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    user_host = forms.CharField(
        label=_("Host"), required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    new_name = forms.CharField(label=_("New Name"), required=False)
    new_password = forms.RegexField(
        label=_("New Password"), required=False,
        widget=forms.PasswordInput(render_value=False),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    new_host = forms.CharField(label=_("New Host"), required=False)

    validation_error_message = _('A new name or new password or '
                                 'new host must be specified.')

    def handle(self, request, data):
        instance = data.get('instance_id')
        try:
            api.trove.user_update_attributes(
                request,
                instance,
                data['user_name'],
                host=data['user_host'],
                new_name=data['new_name'],
                new_password=data['new_password'],
                new_host=data['new_host'])

            messages.success(request,
                             _('Updated user "%s".') % data['user_name'])
        except Exception:
            redirect = reverse("horizon:project:databases:detail",
                               args=(instance,))
            exceptions.handle(request, _('Unable to update user.'),
                              redirect=redirect)
        return True

    def clean(self):
        cleaned_data = super(EditUserForm, self).clean()

        if (not (cleaned_data['new_name'] or
                 cleaned_data['new_password'] or
                 cleaned_data['new_host'])):
            raise ValidationError(self.validation_error_message)

        return cleaned_data


class AttachConfigurationForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    configuration = forms.ChoiceField(label=_("Configuration Group"))

    def __init__(self, request, *args, **kwargs):
        super(AttachConfigurationForm, self).__init__(request, *args, **kwargs)
        instance_id = kwargs.get('initial', {}).get('instance_id')
        datastore = kwargs.get('initial', {}).get('datastore')
        datastore_version = kwargs.get('initial', {}).get('datastore_version')
        self.fields['instance_id'].initial = instance_id

        configurations = api.trove.configuration_list(request)
        choices = [(c.id, c.name) for c in configurations
                   if (c.datastore_name == datastore and
                       c.datastore_version_name == datastore_version)]
        if choices:
            choices.insert(0, ("", _("Select configuration group")))
        else:
            choices.insert(0, ("", _("No configuration groups available")))
        self.fields['configuration'].choices = choices

    def handle(self, request, data):
        instance_id = data.get('instance_id')
        try:
            api.trove.instance_attach_configuration(request,
                                                    instance_id,
                                                    data['configuration'])

            messages.success(request, _('Attaching Configuration group "%s"')
                             % instance_id)
        except Exception:
            redirect = reverse("horizon:project:databases:index")
            exceptions.handle(request, _('Unable to attach configuration '
                                         'group.'),
                              redirect=redirect)
        return True


class UpdateInstanceForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    instance_name = forms.CharField(label=_("Name"))
    allowed_cidrs = forms.MultiIPField(
        label=_("Allowed CIDRs"),
        required=False,
        help_text=_("Classless Inter-Domain Routing "
                    "(e.g. 192.168.0.0/24, or "
                    "2001:db8::/128). Can enter multiple values separating"
                    "by a comma"),
        version=forms.IPv4 | forms.IPv6,
        mask=True,
        widget=forms.TextInput())

    def __init__(self, request, *args, **kwargs):
        super(UpdateInstanceForm, self).__init__(request, *args, **kwargs)
        instance_id = kwargs.get('initial', {}).get('instance_id')
        self.fields['instance_id'].initial = instance_id

    def handle(self, request, data):
        instance_id = data.get('instance_id')
        allowed_cidrs = data.get('allowed_cidrs')
        instance_name = data.get('instance_name')
        update_kwargs = {'name': instance_name}
        if allowed_cidrs:
            update_kwargs['allowed_cidrs'] = allowed_cidrs.split(',')
        try:
            api.trove.instance_update(request, instance_id, **update_kwargs)

            messages.success(request, _('Instance "%s" successfully updated.')
                             % instance_name)
        except Exception:
            redirect = reverse("horizon:project:databases:index")
            exceptions.handle(request, _('Unable to update instance "%s".'
                                         % instance_id),
                              redirect=redirect)
        return True
