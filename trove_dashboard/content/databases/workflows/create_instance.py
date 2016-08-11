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

import binascii
import logging

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon.utils import memoized
from horizon import workflows
from openstack_dashboard import api as dash_api
from openstack_dashboard.dashboards.project.instances \
    import utils as instance_utils
from openstack_dashboard.dashboards.project.instances.workflows \
    import create_instance as dash_create_instance


from trove_dashboard import api

LOG = logging.getLogger(__name__)


def parse_datastore_and_version_text(datastore_and_version):
    if datastore_and_version:
        datastore, datastore_version = datastore_and_version.split('-', 1)
        return datastore.strip(), datastore_version.strip()
    return None, None


class SetInstanceDetailsAction(workflows.Action):
    availability_zone = forms.ChoiceField(
        label=_("Availability Zone"),
        required=False)
    name = forms.CharField(max_length=80, label=_("Instance Name"))
    volume = forms.IntegerField(label=_("Volume Size"),
                                min_value=0,
                                initial=1,
                                help_text=_("Size of the volume in GB."))
    volume_type = forms.ChoiceField(
        label=_("Volume Type"),
        required=False,
        help_text=_("Applicable only if the volume size is specified."))
    datastore = forms.ChoiceField(
        label=_("Datastore"),
        help_text=_("Type and version of datastore."),
        widget=forms.Select(attrs={
            'class': 'switchable',
            'data-slug': 'datastore'
        }))

    def __init__(self, request, *args, **kwargs):
        super(SetInstanceDetailsAction, self).__init__(request,
                                                       *args,
                                                       **kwargs)
        # Add this field to the end after the dynamic fields
        self.fields['locality'] = forms.ChoiceField(
            label=_("Locality"),
            choices=[("", "None"),
                     ("affinity", "affinity"),
                     ("anti-affinity", "anti-affinity")],
            required=False,
            help_text=_("Specify whether future replicated instances will "
                        "be created on the same hypervisor (affinity) or on "
                        "different hypervisors (anti-affinity). "
                        "This value is ignored if the instance to be "
                        "launched is a replica.")
        )

    class Meta(object):
        name = _("Details")
        help_text_template = "project/databases/_launch_details_help.html"

    def clean(self):
        datastore_and_version = self.data.get("datastore", None)
        if not datastore_and_version:
            msg = _("You must select a datastore type and version.")
            self._errors["datastore"] = self.error_class([msg])
        else:
            datastore, datastore_version = parse_datastore_and_version_text(
                binascii.unhexlify(datastore_and_version))
            field_name = self._build_flavor_field_name(datastore,
                                                       datastore_version)
            flavor = self.data.get(field_name, None)
            if not flavor:
                msg = _("You must select a flavor.")
                self._errors[field_name] = self.error_class([msg])

        if not self.data.get("locality", None):
            self.cleaned_data["locality"] = None

        return self.cleaned_data

    def handle(self, request, context):
        datastore_and_version = context["datastore"]
        if datastore_and_version:
            datastore, datastore_version = parse_datastore_and_version_text(
                binascii.unhexlify(context["datastore"]))
            field_name = self._build_flavor_field_name(datastore,
                                                       datastore_version)
            flavor = self.data[field_name]
            if flavor:
                context["flavor"] = flavor
                return context
        return None

    @memoized.memoized_method
    def availability_zones(self, request):
        try:
            return dash_api.nova.availability_zone_list(request)
        except Exception:
            LOG.exception("Exception while obtaining availablity zones")
            self._availability_zones = []

    def populate_availability_zone_choices(self, request, context):
        try:
            zones = self.availability_zones(request)
        except Exception:
            zones = []
            redirect = reverse('horizon:project:databases:index')
            exceptions.handle(request,
                              _('Unable to retrieve availability zones.'),
                              redirect=redirect)

        zone_list = [(zone.zoneName, zone.zoneName)
                     for zone in zones if zone.zoneState['available']]
        zone_list.sort()
        if not zone_list:
            zone_list.insert(0, ("", _("No availability zones found")))
        elif len(zone_list) > 1:
            zone_list.insert(0, ("", _("Any Availability Zone")))
        return zone_list

    @memoized.memoized_method
    def datastore_flavors(self, request, datastore_name, datastore_version):
        try:
            return api.trove.datastore_flavors(
                request, datastore_name, datastore_version)
        except Exception:
            LOG.exception("Exception while obtaining flavors list")
            redirect = reverse("horizon:project:databases:index")
            exceptions.handle(request,
                              _('Unable to obtain flavors.'),
                              redirect=redirect)

    @memoized.memoized_method
    def populate_volume_type_choices(self, request, context):
        try:
            volume_types = dash_api.cinder.volume_type_list(request)
            return ([("no_type", _("No volume type"))] +
                    [(type.name, type.name)
                     for type in volume_types])
        except Exception:
            LOG.exception("Exception while obtaining volume types list")
            self._volume_types = []

    @memoized.memoized_method
    def datastores(self, request):
        try:
            return api.trove.datastore_list(request)
        except Exception:
            LOG.exception("Exception while obtaining datastores list")
            self._datastores = []

    @memoized.memoized_method
    def datastore_versions(self, request, datastore):
        try:
            return api.trove.datastore_version_list(request, datastore)
        except Exception:
            LOG.exception("Exception while obtaining datastore version list")
            self._datastore_versions = []

    def populate_datastore_choices(self, request, context):
        choices = ()
        datastores = self.datastores(request)
        if datastores is not None:
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
                        self._add_datastore_flavor_field(request,
                                                         ds.name,
                                                         v.name)
                    choices = choices + version_choices
        return choices

    def _add_datastore_flavor_field(self,
                                    request,
                                    datastore,
                                    datastore_version):
        name = self._build_widget_field_name(datastore, datastore_version)
        attr_key = 'data-datastore-' + name
        field_name = self._build_flavor_field_name(datastore,
                                                   datastore_version)
        self.fields[field_name] = forms.ChoiceField(
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
            self.fields[field_name].choices = instance_utils.sort_flavor_list(
                request, valid_flavors)

    def _build_datastore_display_text(self, datastore, datastore_version):
        return datastore + ' - ' + datastore_version

    def _build_widget_field_name(self, datastore, datastore_version):
        # Since the fieldnames cannot contain an uppercase character
        # we generate a hex encoded string representation of the
        # datastore and version as the fieldname
        return binascii.hexlify(
            self._build_datastore_display_text(datastore, datastore_version))

    def _build_flavor_field_name(self, datastore, datastore_version):
        return self._build_widget_field_name(datastore,
                                             datastore_version)


TROVE_ADD_USER_PERMS = getattr(settings, 'TROVE_ADD_USER_PERMS', [])
TROVE_ADD_DATABASE_PERMS = getattr(settings, 'TROVE_ADD_DATABASE_PERMS', [])
TROVE_ADD_PERMS = TROVE_ADD_USER_PERMS + TROVE_ADD_DATABASE_PERMS


class SetInstanceDetails(workflows.Step):
    action_class = SetInstanceDetailsAction
    contributes = ("name", "volume", "volume_type", "flavor", "datastore",
                   "locality", "availability_zone")


class AddDatabasesAction(workflows.Action):
    """Initialize the database with users/databases. This tab will honor
    the settings which should be a list of permissions required:

    * TROVE_ADD_USER_PERMS = []
    * TROVE_ADD_DATABASE_PERMS = []
    """
    databases = forms.CharField(label=_('Initial Databases'),
                                required=False,
                                help_text=_('Comma separated list of '
                                            'databases to create'))
    user = forms.CharField(label=_('Initial Admin User'),
                           required=False,
                           help_text=_("Initial admin user to add"))
    password = forms.CharField(widget=forms.PasswordInput(),
                               label=_("Password"),
                               required=False)
    host = forms.CharField(label=_("Allowed Host (optional)"),
                           required=False,
                           help_text=_("Host or IP that the user is allowed "
                                       "to connect through."))

    class Meta(object):
        name = _("Initialize Databases")
        permissions = TROVE_ADD_PERMS
        help_text_template = "project/databases/_launch_initialize_help.html"

    def clean(self):
        cleaned_data = super(AddDatabasesAction, self).clean()
        if cleaned_data.get('user'):
            if not cleaned_data.get('password'):
                msg = _('You must specify a password if you create a user.')
                self._errors["password"] = self.error_class([msg])
            if not cleaned_data.get('databases'):
                msg = _('You must specify at least one database if '
                        'you create a user.')
                self._errors["databases"] = self.error_class([msg])
        return cleaned_data


class InitializeDatabase(workflows.Step):
    action_class = AddDatabasesAction
    contributes = ["databases", 'user', 'password', 'host']


class AdvancedAction(workflows.Action):
    config = forms.ChoiceField(
        label=_("Configuration Group"),
        required=False,
        help_text=_('Select a configuration group'))
    initial_state = forms.ChoiceField(
        label=_('Source for Initial State'),
        required=False,
        help_text=_("Choose initial state."),
        choices=[
            ('', _('None')),
            ('backup', _('Restore from Backup')),
            ('master', _('Replicate from Instance'))],
        widget=forms.Select(attrs={
            'class': 'switchable',
            'data-slug': 'initial_state'
        }))
    backup = forms.ChoiceField(
        label=_('Backup Name'),
        required=False,
        help_text=_('Select a backup to restore'),
        widget=forms.Select(attrs={
            'class': 'switched',
            'data-switch-on': 'initial_state',
            'data-initial_state-backup': _('Backup Name')
        }))
    master = forms.ChoiceField(
        label=_('Master Instance Name'),
        required=False,
        help_text=_('Select a master instance'),
        widget=forms.Select(attrs={
            'class': 'switched',
            'data-switch-on': 'initial_state',
            'data-initial_state-master': _('Master Instance Name')
        }))
    replica_count = forms.IntegerField(
        label=_('Replica Count'),
        required=False,
        min_value=1,
        initial=1,
        help_text=_('Specify the number of replicas to be created'),
        widget=forms.TextInput(attrs={
            'class': 'switched',
            'data-switch-on': 'initial_state',
            'data-initial_state-master': _('Replica Count')
        }))

    class Meta(object):
        name = _("Advanced")
        help_text_template = "project/databases/_launch_advanced_help.html"

    def populate_config_choices(self, request, context):
        try:
            configs = api.trove.configuration_list(request)
            config_name = "%(name)s (%(datastore)s - %(version)s)"
            choices = [(c.id,
                        config_name % {'name': c.name,
                                       'datastore': c.datastore_name,
                                       'version': c.datastore_version_name})
                       for c in configs]
        except Exception:
            choices = []

        if choices:
            choices.insert(0, ("", _("Select configuration")))
        else:
            choices.insert(0, ("", _("No configurations available")))
        return choices

    def populate_backup_choices(self, request, context):
        try:
            backups = api.trove.backup_list(request)
            choices = [(b.id, b.name) for b in backups
                       if b.status == 'COMPLETED']
        except Exception:
            choices = []

        if choices:
            choices.insert(0, ("", _("Select backup")))
        else:
            choices.insert(0, ("", _("No backups available")))
        return choices

    def _get_instances(self):
        instances = []
        try:
            instances = api.trove.instance_list_all(self.request)
        except Exception:
            msg = _('Unable to retrieve database instances.')
            exceptions.handle(self.request, msg)
        return instances

    def populate_master_choices(self, request, context):
        try:
            instances = self._get_instances()
            choices = sorted([(i.id, i.name) for i in
                             instances if i.status == 'ACTIVE'],
                             key=lambda i: i[1])
        except Exception:
            choices = []

        if choices:
            choices.insert(0, ("", _("Select instance")))
        else:
            choices.insert(0, ("", _("No instances available")))
        return choices

    def clean(self):
        cleaned_data = super(AdvancedAction, self).clean()

        config = self.cleaned_data['config']
        if config:
            try:
                # Make sure the user is not "hacking" the form
                # and that they have access to this configuration
                cfg = api.trove.configuration_get(self.request, config)
                self.cleaned_data['config'] = cfg.id
            except Exception:
                raise forms.ValidationError(_("Unable to find configuration "
                                              "group!"))
        else:
            self.cleaned_data['config'] = None

        initial_state = cleaned_data.get("initial_state")

        if initial_state == 'backup':
            cleaned_data['replica_count'] = None
            backup = self.cleaned_data['backup']
            if backup:
                try:
                    bkup = api.trove.backup_get(self.request, backup)
                    self.cleaned_data['backup'] = bkup.id
                except Exception:
                    raise forms.ValidationError(_("Unable to find backup!"))
            else:
                raise forms.ValidationError(_("A backup must be selected!"))

            cleaned_data['master'] = None
        elif initial_state == 'master':
            master = self.cleaned_data['master']
            if master:
                try:
                    api.trove.instance_get(self.request, master)
                except Exception:
                    raise forms.ValidationError(
                        _("Unable to find master instance!"))
            else:
                raise forms.ValidationError(
                    _("A master instance must be selected!"))

            cleaned_data['backup'] = None
        else:
            cleaned_data['master'] = None
            cleaned_data['backup'] = None
            cleaned_data['replica_count'] = None

        return cleaned_data


class Advanced(workflows.Step):
    action_class = AdvancedAction
    contributes = ['config', 'backup', 'master', 'replica_count']


class LaunchInstance(workflows.Workflow):
    slug = "launch_instance"
    name = _("Launch Instance")
    finalize_button_name = _("Launch")
    success_message = _('Launched %(count)s named "%(name)s".')
    failure_message = _('Unable to launch %(count)s named "%(name)s".')
    success_url = "horizon:project:databases:index"
    default_steps = (SetInstanceDetails,
                     dash_create_instance.SetNetwork,
                     InitializeDatabase,
                     Advanced)

    def __init__(self, request=None, context_seed=None, entry_point=None,
                 *args, **kwargs):
        super(LaunchInstance, self).__init__(request, context_seed,
                                             entry_point, *args, **kwargs)
        self.attrs['autocomplete'] = (
            settings.HORIZON_CONFIG.get('password_autocomplete'))

    def format_status_message(self, message):
        name = self.context.get('name', 'unknown instance')
        return message % {"count": _("instance"), "name": name}

    def _get_databases(self, context):
        """Returns the initial databases for this instance."""
        databases = None
        if context.get('databases'):
            dbs = context['databases']
            databases = [{'name': d.strip()} for d in dbs.split(',')]
        return databases

    def _get_users(self, context):
        users = None
        if context.get('user'):
            user = {
                'name': context['user'],
                'password': context['password'],
                'databases': self._get_databases(context),
            }
            if context['host']:
                user['host'] = context['host']
            users = [user]
        return users

    def _get_backup(self, context):
        backup = None
        if context.get('backup'):
            backup = {'backupRef': context['backup']}
        return backup

    def _get_nics(self, context):
        netids = context.get('network_id', None)
        if netids:
            return [{"net-id": netid, "v4-fixed-ip": ""}
                    for netid in netids]
        else:
            return None

    def _get_volume_type(self, context):
        volume_type = None
        if context.get('volume_type') != 'no_type':
            volume_type = context['volume_type']
        return volume_type

    def _get_locality(self, context):
        # If creating a replica from a master then always set to None
        if context.get('master'):
            return None

        locality = None
        if context.get('locality'):
            locality = context['locality']
        return locality

    def handle(self, request, context):
        try:
            datastore, datastore_version = parse_datastore_and_version_text(
                binascii.unhexlify(self.context['datastore']))
            avail_zone = context.get('availability_zone', None)
            LOG.info("Launching database instance with parameters "
                     "{name=%s, volume=%s, volume_type=%s, flavor=%s, "
                     "datastore=%s, datastore_version=%s, "
                     "dbs=%s, users=%s, "
                     "backups=%s, nics=%s, replica_of=%s replica_count=%s, "
                     "configuration=%s, locality=%s, "
                     "availability_zone=%s}",
                     context['name'], context['volume'],
                     self._get_volume_type(context), context['flavor'],
                     datastore, datastore_version,
                     self._get_databases(context), self._get_users(context),
                     self._get_backup(context), self._get_nics(context),
                     context.get('master'), context['replica_count'],
                     context.get('config'), self._get_locality(context),
                     avail_zone)
            api.trove.instance_create(request,
                                      context['name'],
                                      context['volume'],
                                      context['flavor'],
                                      datastore=datastore,
                                      datastore_version=datastore_version,
                                      databases=self._get_databases(context),
                                      users=self._get_users(context),
                                      restore_point=self._get_backup(context),
                                      nics=self._get_nics(context),
                                      replica_of=context.get('master'),
                                      replica_count=context['replica_count'],
                                      volume_type=self._get_volume_type(
                                          context),
                                      configuration=context.get('config'),
                                      locality=self._get_locality(context),
                                      availability_zone=avail_zone)
            return True
        except Exception:
            exceptions.handle(request)
            return False
