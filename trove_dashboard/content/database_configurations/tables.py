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

import types

from django.core import exceptions as core_exceptions
from django.core import urlresolvers
from django import shortcuts
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import forms
from horizon import messages
from horizon import tables
from horizon.utils import memoized

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
        return urlresolvers.reverse(self.url, args=[configuration_id])


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
                    _('Error resetting parameters: %s') % ex.message)

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

    def delete(self, request, obj_ids):
        configuration_id = self.table.kwargs['configuration_id']
        (config_param_manager
            .get(request, configuration_id)
            .delete_param(obj_ids))


class UpdateRow(tables.Row):
    def get_data(self, request, name):
        return config_param_manager.get(
            request, self.table.kwargs["configuration_id"]).get_param(name)


class UpdateCell(tables.UpdateAction):
    def update_cell(self, request, datum, name,
                    cell_name, new_cell_value):
        config_param = datum

        config = config_param_manager.get(request,
                                          config_param.configuration_id)
        validation_param = config_param_manager.find_parameter(
            name,
            self.parameters(request,
                            config.configuration.datastore_name,
                            config.configuration.datastore_version_name))
        if validation_param:
            error_msg = config_param_manager.validate_config_param_value(
                validation_param, new_cell_value)
            if error_msg:
                raise core_exceptions.ValidationError(error_msg)

        if isinstance(config_param.value, types.IntType):
            value = int(new_cell_value)
        elif isinstance(config_param.value, types.LongType):
            value = long(new_cell_value)
        else:
            value = new_cell_value

        setattr(datum, cell_name, value)

        (config_param_manager
            .get(request, config_param.configuration_id)
            .update_param(name, value))

        return True

    @memoized.memoized_method
    def parameters(self, request, datastore, datastore_version):
        return api.trove.configuration_parameters_list(
            request, datastore, datastore_version)

    def _adjust_type(self, data_type, value):
        if not value:
            return value
        if data_type == "float":
            new_value = float(value)
        elif data_type == "long":
            new_value = long(value)
        elif data_type == "integer":
            new_value = int(value)
        else:
            new_value = value
        return new_value


class ValuesTable(tables.DataTable):
    name = tables.Column("name", verbose_name=_("Name"))
    value = tables.Column("value", verbose_name=_("Value"),
                          form_field=forms.CharField(required=False),
                          update_action=UpdateCell)

    class Meta(object):
        name = "values"
        verbose_name = _("Configuration Group Values")
        table_actions = [ApplyChanges, DiscardChanges,
                         AddParameter, DeleteParameter]
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
