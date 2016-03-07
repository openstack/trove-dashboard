# Copyright 2015 HP Software, LLC
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import binascii
import collections
import logging
import uuid

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_variables  # noqa

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon.utils import memoized
from openstack_dashboard import api

from openstack_dashboard.dashboards.project.instances \
    import utils as instance_utils
from trove_dashboard import api as trove_api
from trove_dashboard.content.database_clusters \
    import cluster_manager
from trove_dashboard.content.databases import db_capability
from trove_dashboard.content.databases.workflows \
    import create_instance

LOG = logging.getLogger(__name__)


class LaunchForm(forms.SelfHandlingForm):
    name = forms.CharField(label=_("Cluster Name"),
                           max_length=80)
    datastore = forms.ChoiceField(
        label=_("Datastore"),
        help_text=_("Type and version of datastore."),
        widget=forms.Select(attrs={
            'class': 'switchable',
            'data-slug': 'datastore'
        }))
    network = forms.ChoiceField(
        label=_("Network"),
        help_text=_("Network attached to instance."),
        required=False)
    volume = forms.IntegerField(
        label=_("Volume Size"),
        min_value=0,
        initial=1,
        help_text=_("Size of the volume in GB."))
    locality = forms.ChoiceField(
        label=_("Locality"),
        choices=[("", "None"),
                 ("affinity", "affinity"),
                 ("anti-affinity", "anti-affinity")],
        required=False,
        help_text=_("Specify whether instances in the cluster will "
                    "be created on the same hypervisor (affinity) or on "
                    "different hypervisors (anti-affinity)."))
    root_password = forms.CharField(
        label=_("Root Password"),
        required=False,
        help_text=_("Password for root user."),
        widget=forms.PasswordInput(attrs={
            'class': 'switched',
            'data-switch-on': 'datastore',
        }))
    num_instances_vertica = forms.IntegerField(
        label=_("Number of Instances"),
        min_value=3,
        initial=3,
        required=False,
        help_text=_("Number of instances in the cluster. (Read only)"),
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'class': 'switched',
            'data-switch-on': 'datastore',
        }))
    num_shards = forms.IntegerField(
        label=_("Number of Shards"),
        min_value=1,
        initial=1,
        required=False,
        help_text=_("Number of shards. (Read only)"),
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'class': 'switched',
            'data-switch-on': 'datastore',
        }))
    num_instances = forms.IntegerField(
        label=_("Number of Instances"),
        initial=3,
        required=False,
        help_text=_("Number of instances in the cluster."),
        widget=forms.TextInput(attrs={
            'class': 'switched',
            'data-switch-on': 'datastore',
        }))

    # (name of field variable, label)
    default_fields = [
        ('num_instances', _('Number of Instances'))
    ]
    mongodb_fields = default_fields + [
        ('num_shards', _('Number of Shards')),
    ]
    vertica_fields = [
        ('num_instances_vertica', ('Number of Instances')),
        ('root_password', _('Root Password')),
    ]

    def __init__(self, request, *args, **kwargs):
        super(LaunchForm, self).__init__(request, *args, **kwargs)

        self.fields['datastore'].choices = self.populate_datastore_choices(
            request)
        self.fields['network'].choices = self.populate_network_choices(
            request)

    def clean(self):
        datastore_field_value = self.data.get("datastore", None)
        if datastore_field_value:
            datastore, datastore_version = (
                create_instance.parse_datastore_and_version_text(
                    binascii.unhexlify(datastore_field_value)))

            flavor_field_name = self._build_widget_field_name(
                datastore, datastore_version)
            if not self.data.get(flavor_field_name, None):
                msg = _("The flavor must be specified.")
                self._errors[flavor_field_name] = self.error_class([msg])

            if db_capability.is_vertica_datastore(datastore):
                if not self.data.get("root_password", None):
                    msg = _("Password for root user must be specified.")
                    self._errors["root_password"] = self.error_class([msg])
            else:
                if int(self.data.get("num_instances", 0)) < 1:
                    msg = _("The number of instances must be greater than 1.")
                    self._errors["num_instances"] = self.error_class([msg])

                if db_capability.is_mongodb_datastore(datastore):
                    if int(self.data.get("num_shards", 0)) < 1:
                        msg = _("The number of shards must be greater than 1.")
                        self._errors["num_shards"] = self.error_class([msg])

        if not self.data.get("locality", None):
            self.cleaned_data["locality"] = None

        return self.cleaned_data

    @memoized.memoized_method
    def datastore_flavors(self, request, datastore_name, datastore_version):
        try:
            return trove_api.trove.datastore_flavors(
                request, datastore_name, datastore_version)
        except Exception:
            LOG.exception("Exception while obtaining flavors list")
            self._flavors = []
            redirect = reverse('horizon:project:database_clusters:index')
            exceptions.handle(request,
                              _('Unable to obtain flavors.'),
                              redirect=redirect)

    @memoized.memoized_method
    def populate_network_choices(self, request):
        network_list = []
        try:
            if api.base.is_service_enabled(request, 'network'):
                tenant_id = self.request.user.tenant_id
                networks = api.neutron.network_list_for_tenant(request,
                                                               tenant_id)
                network_list = [(network.id, network.name_or_id)
                                for network in networks]
            else:
                self.fields['network'].widget = forms.HiddenInput()
        except exceptions.ServiceCatalogException:
            network_list = []
            redirect = reverse('horizon:project:database_clusters:index')
            exceptions.handle(request,
                              _('Unable to retrieve networks.'),
                              redirect=redirect)
        return network_list

    @memoized.memoized_method
    def datastores(self, request):
        try:
            return trove_api.trove.datastore_list(request)
        except Exception:
            LOG.exception("Exception while obtaining datastores list")
            self._datastores = []
            redirect = reverse('horizon:project:database_clusters:index')
            exceptions.handle(request,
                              _('Unable to obtain datastores.'),
                              redirect=redirect)

    def filter_cluster_datastores(self, request):
        datastores = []
        for ds in self.datastores(request):
            # TODO(michayu): until capabilities lands
            if db_capability.is_cluster_capable_datastore(ds.name):
                datastores.append(ds)
        return datastores

    @memoized.memoized_method
    def datastore_versions(self, request, datastore):
        try:
            return trove_api.trove.datastore_version_list(request, datastore)
        except Exception:
            LOG.exception("Exception while obtaining datastore version list")
            self._datastore_versions = []
            redirect = reverse('horizon:project:database_clusters:index')
            exceptions.handle(request,
                              _('Unable to obtain datastore versions.'),
                              redirect=redirect)

    def populate_datastore_choices(self, request):
        choices = ()
        datastores = self.filter_cluster_datastores(request)
        if datastores is not None:
            datastore_flavor_fields = {}
            for ds in datastores:
                versions = self.datastore_versions(request, ds.name)
                if versions:
                    # only add to choices if datastore has at least one version
                    version_choices = ()
                    for v in versions:
                        if hasattr(v, 'active') and not v.active:
                            continue
                        selection_text = self._build_datastore_display_text(
                            ds.name, v.name)
                        widget_text = self._build_widget_field_name(
                            ds.name, v.name)
                        version_choices = (version_choices +
                                           ((widget_text, selection_text),))
                        k, v = self._add_datastore_flavor_field(request,
                                                                ds.name,
                                                                v.name)
                        datastore_flavor_fields[k] = v
                        self._add_attr_to_optional_fields(ds.name,
                                                          widget_text)

                    choices = choices + version_choices
            self._insert_datastore_version_fields(datastore_flavor_fields)
        return choices

    def _add_datastore_flavor_field(self,
                                    request,
                                    datastore,
                                    datastore_version):
        name = self._build_widget_field_name(datastore, datastore_version)
        attr_key = 'data-datastore-' + name
        field = forms.ChoiceField(
            label=_("Flavor"),
            help_text=_("Size of image to launch."),
            required=False,
            widget=forms.Select(attrs={
                'class': 'switched',
                'data-switch-on': 'datastore',
                attr_key: _("Flavor")
            }))
        valid_flavors = self.datastore_flavors(request,
                                               datastore,
                                               datastore_version)
        if valid_flavors:
            field.choices = instance_utils.sort_flavor_list(
                request, valid_flavors)

        return name, field

    def _build_datastore_display_text(self, datastore, datastore_version):
        return datastore + ' - ' + datastore_version

    def _build_widget_field_name(self, datastore, datastore_version):
        # Since the fieldnames cannot contain an uppercase character
        # we generate a hex encoded string representation of the
        # datastore and version as the fieldname
        return binascii.hexlify(
            self._build_datastore_display_text(datastore, datastore_version))

    def _insert_datastore_version_fields(self, datastore_flavor_fields):
        fields_to_restore_at_the_end = collections.OrderedDict()
        while True:
            k, v = self.fields.popitem()
            if k == 'datastore':
                self.fields[k] = v
                break
            else:
                fields_to_restore_at_the_end[k] = v

        for k, v in datastore_flavor_fields.iteritems():
            self.fields[k] = v

        for k in reversed(fields_to_restore_at_the_end.keys()):
            self.fields[k] = fields_to_restore_at_the_end[k]

    def _add_attr_to_optional_fields(self, datastore, selection_text):
        if db_capability.is_mongodb_datastore(datastore):
            fields = self.mongodb_fields
        elif db_capability.is_vertica_datastore(datastore):
            fields = self.vertica_fields
        else:
            fields = self.default_fields

        for field in fields:
            attr_key = 'data-datastore-' + selection_text
            widget = self.fields[field[0]].widget
            if attr_key not in widget.attrs:
                widget.attrs[attr_key] = field[1]

    def _get_locality(self, data):
        locality = None
        if data.get('locality'):
            locality = data['locality']
        return locality

    @sensitive_variables('data')
    def handle(self, request, data):
        try:
            datastore, datastore_version = (
                create_instance.parse_datastore_and_version_text(
                    binascii.unhexlify(data['datastore'])))

            flavor_field_name = self._build_widget_field_name(
                datastore, datastore_version)
            flavor = data[flavor_field_name]
            num_instances = data['num_instances']
            root_password = None
            if db_capability.is_vertica_datastore(datastore):
                root_password = data['root_password']
                num_instances = data['num_instances_vertica']
            LOG.info("Launching cluster with parameters "
                     "{name=%s, volume=%s, flavor=%s, "
                     "datastore=%s, datastore_version=%s",
                     "locality=%s",
                     data['name'], data['volume'], flavor,
                     datastore, datastore_version, self._get_locality(data))

            trove_api.trove.cluster_create(request,
                                           data['name'],
                                           data['volume'],
                                           flavor,
                                           num_instances,
                                           datastore=datastore,
                                           datastore_version=datastore_version,
                                           nics=data['network'],
                                           root_password=root_password,
                                           locality=self._get_locality(data))
            messages.success(request,
                             _('Launched cluster "%s"') % data['name'])
            return True
        except Exception as e:
            redirect = reverse("horizon:project:database_clusters:index")
            exceptions.handle(request,
                              _('Unable to launch cluster. %s') % e.message,
                              redirect=redirect)


class ClusterAddInstanceForm(forms.SelfHandlingForm):
    cluster_id = forms.CharField(
        required=False,
        widget=forms.HiddenInput())
    flavor = forms.ChoiceField(
        label=_("Flavor"),
        help_text=_("Size of image to launch."))
    volume = forms.IntegerField(
        label=_("Volume Size"),
        min_value=0,
        initial=1,
        help_text=_("Size of the volume in GB."))
    name = forms.CharField(
        label=_("Name"),
        required=False,
        help_text=_("Optional name of the instance."))
    type = forms.CharField(
        label=_("Instance Type"),
        required=False,
        help_text=_("Optional datastore specific type of the instance."))
    related_to = forms.CharField(
        label=_("Related To"),
        required=False,
        help_text=_("Optional datastore specific value that defines the "
                    "relationship from one instance in the cluster to "
                    "another."))
    network = forms.ChoiceField(
        label=_("Network"),
        help_text=_("Network attached to instance."),
        required=False)

    def __init__(self, request, *args, **kwargs):
        super(ClusterAddInstanceForm, self).__init__(request, *args, **kwargs)
        self.fields['cluster_id'].initial = kwargs['initial']['cluster_id']
        self.fields['flavor'].choices = self.populate_flavor_choices(request)
        self.fields['network'].choices = self.populate_network_choices(
            request)

    @memoized.memoized_method
    def flavors(self, request):
        try:
            datastore = None
            datastore_version = None
            datastore_dict = self.initial.get('datastore', None)
            if datastore_dict:
                datastore = datastore_dict.get('type', None)
                datastore_version = datastore_dict.get('version', None)
            return trove_api.trove.datastore_flavors(
                request,
                datastore_name=datastore,
                datastore_version=datastore_version)
        except Exception:
            LOG.exception("Exception while obtaining flavors list")
            self._flavors = []
            redirect = reverse('horizon:project:database_clusters:index')
            exceptions.handle(request,
                              _('Unable to obtain flavors.'),
                              redirect=redirect)

    def populate_flavor_choices(self, request):
        flavor_list = [(f.id, "%s" % f.name) for f in self.flavors(request)]
        return sorted(flavor_list)

    @memoized.memoized_method
    def populate_network_choices(self, request):
        network_list = []
        try:
            if api.base.is_service_enabled(request, 'network'):
                tenant_id = self.request.user.tenant_id
                networks = api.neutron.network_list_for_tenant(request,
                                                               tenant_id)
                network_list = [(network.id, network.name_or_id)
                                for network in networks]
            else:
                self.fields['network'].widget = forms.HiddenInput()
        except exceptions.ServiceCatalogException:
            network_list = []
            redirect = reverse('horizon:project:database_clusters:index')
            exceptions.handle(request,
                              _('Unable to retrieve networks.'),
                              redirect=redirect)
        return network_list

    def handle(self, request, data):
        try:
            flavor = trove_api.trove.flavor_get(request, data['flavor'])
            manager = cluster_manager.get(data['cluster_id'])
            manager.add_instance(str(uuid.uuid4()),
                                 data.get('name', None),
                                 data['flavor'],
                                 flavor.name,
                                 data['volume'],
                                 data.get('type', None),
                                 data.get('related_to', None),
                                 data.get('network', None))
        except Exception as e:
            redirect = reverse("horizon:project:database_clusters:index")
            exceptions.handle(request,
                              _('Unable to grow cluster. %s') % e.message,
                              redirect=redirect)
        return True


class ResetPasswordForm(forms.SelfHandlingForm):
    cluster_id = forms.CharField(widget=forms.HiddenInput())
    password = forms.CharField(widget=forms.PasswordInput(),
                               label=_("New Password"),
                               help_text=_("New password for cluster access."))

    @sensitive_variables('data')
    def handle(self, request, data):
        password = data.get("password")
        cluster_id = data.get("cluster_id")
        try:
            trove_api.trove.create_cluster_root(request,
                                                cluster_id,
                                                password)
            messages.success(request, _('Root password updated for '
                                        'cluster "%s"') % cluster_id)
        except Exception as e:
            redirect = reverse("horizon:project:database_clusters:index")
            exceptions.handle(request, _('Unable to reset password. %s') %
                              e.message, redirect=redirect)
        return True
