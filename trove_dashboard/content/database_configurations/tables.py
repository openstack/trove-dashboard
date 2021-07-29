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

from django import shortcuts
from django import urls
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import forms
from horizon import messages
from horizon import tables
from oslo_serialization import jsonutils

from trove_dashboard import api
from trove_dashboard.content.database_configurations \
    import config_param_manager


class CreateConfiguration(tables.LinkAction):
    name = "create_configuration"
    verbose_name = _("Create Configuration Group")
    url = "horizon:project:database_configurations:create"
    classes = ('ajax-modal', )
    icon = "plus"


class DeleteConfiguration(tables.DeleteAction):
    data_type_singular = _("Configuration Group")
    data_type_plural = _("Configuration Groups")

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Configuration Group",
            u"Delete Configuration Groups",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Configuration Group",
            u"Deleted Configuration Groups",
            count
        )

    def delete(self, request, obj_id):
        api.trove.configuration_delete(request, obj_id)


class ConfigurationsTable(tables.DataTable):
    name = tables.Column(
        'name',
        verbose_name=_('Configuration Group Name'),
        link="horizon:project:database_configurations:detail")
    description = tables.Column(
        lambda obj: getattr(obj, 'description', None),
        verbose_name=_('Description'))
    datastore = tables.Column(
        'datastore_name',
        verbose_name=_('Datastore'))
    datastore_version = tables.Column(
        'datastore_version_name',
        verbose_name=_('Datastore Version'))

    class Meta(object):
        name = "configurations"
        verbose_name = _("Configuration Groups")
        table_actions = [CreateConfiguration, DeleteConfiguration]
        row_actions = [DeleteConfiguration]


class AddParameter(tables.LinkAction):
    name = "add_parameter"
    verbose_name = _("Add Parameter")
    url = "horizon:project:database_configurations:add"
    classes = ('ajax-modal', )
    icon = "plus"

    def get_link_url(self, datum=None):
        configuration_id = self.table.kwargs['configuration_id']
        return urls.reverse(self.url, args=[configuration_id])


class ApplyChanges(tables.Action):
    name = "apply_changes"
    verbose_name = _("Apply Changes")
    verbose_name_plural = _("Apply Changes")
    icon = "pencil"

    def __init__(self, **kwargs):
        super(ApplyChanges, self).__init__(**kwargs)
        self.requires_input = False

    def handle(self, table, request, obj_ids):
        configuration_id = table.kwargs['configuration_id']
        if config_param_manager.get(request, configuration_id).has_changes():
            try:
                api.trove.configuration_update(
                    request, configuration_id,
                    config_param_manager.get(
                        request, configuration_id).to_json())
                messages.success(request, _('Applied changes to server'))
            except Exception:
                messages.error(request, _('Error applying changes'))
            finally:
                config_param_manager.delete(configuration_id)

        return shortcuts.redirect(request.build_absolute_uri())


class DiscardChanges(tables.Action):
    name = "discard_changes"
    verbose_name = _("Discard Changes")
    verbose_name_plural = _("Discard Changes")

    def __init__(self, **kwargs):
        super(DiscardChanges, self).__init__(**kwargs)
        self.requires_input = False

    def handle(self, table, request, obj_ids):
        configuration_id = table.kwargs['configuration_id']
        if config_param_manager.get(request, configuration_id).has_changes():
            try:
                config_param_manager.delete(configuration_id)
                messages.success(request, _('Reset Parameters'))
            except Exception as ex:
                messages.error(
                    request,
                    _('Error resetting parameters: %s') % ex)

        return shortcuts.redirect(request.build_absolute_uri())


class DeleteParameter(tables.DeleteAction):
    data_type_singular = _("Parameter")
    data_type_plural = _("Parameters")

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Parameter",
            u"Delete Parameters",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Parameter",
            u"Deleted Parameters",
            count
        )

    def delete(self, request, names):
        if type(names) is not list:
            names = [names]

        configuration_id = self.table.kwargs['configuration_id']
        configuration = api.trove.configuration_get(request, configuration_id)
        cur_values = dict.copy(configuration.values)

        for name in names:
            if name in cur_values:
                cur_values.pop(name)

        api.trove.configuration_update(
            request, configuration_id, jsonutils.dumps(cur_values))


class UpdateRow(tables.Row):
    def get_data(self, request, name):
        return config_param_manager.get(
            request, self.table.kwargs["configuration_id"]).get_param(name)


class ValuesTable(tables.DataTable):
    name = tables.Column("name", verbose_name=_("Name"))
    value = tables.Column("value", verbose_name=_("Value"),
                          form_field=forms.CharField(required=False))

    class Meta(object):
        name = "values"
        verbose_name = _("Configuration Group Values")
        table_actions = [AddParameter, DeleteParameter]
        row_class = UpdateRow
        row_actions = [DeleteParameter]

    def get_object_id(self, datum):
        return datum.name


class DetachConfiguration(tables.BatchAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Detach Configuration Group",
            u"Detach Configuration Groups",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Detached Configuration Group",
            u"Detached Configuration Groups",
            count
        )

    name = "detach_configuration"
    classes = ('btn-danger', 'btn-detach-config')

    def action(self, request, obj_id):
        api.trove.instance_detach_configuration(request, obj_id)


class InstancesTable(tables.DataTable):
    name = tables.Column("name",
                         link="horizon:project:databases:detail",
                         verbose_name=_("Name"))

    class Meta(object):
        name = "instances"
        verbose_name = _("Configuration Group Instances")
        multi_select = False
        row_actions = [DetachConfiguration]
