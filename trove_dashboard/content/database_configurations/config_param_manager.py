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


from django.core import cache
from django.utils.translation import ugettext_lazy as _

from trove_dashboard import api

from oslo_serialization import jsonutils


def get(request, configuration_group_id):
    if not has_config(configuration_group_id):
        manager = ConfigParamManager(configuration_group_id)
        manager.configuration_get(request)
        cache.cache.set(configuration_group_id, manager)

    return cache.cache.get(configuration_group_id)


def delete(configuration_group_id):
    cache.cache.delete(configuration_group_id)


def update(configuration_group_id, manager):
    cache.cache.set(configuration_group_id, manager)


def has_config(configuration_group_id):
    if cache.cache.get(configuration_group_id):
        return True
    else:
        return False


def dict_has_changes(original, other):
    if len(other) != len(original):
        return True

    diffs = (set(original.keys()) - set(other.keys()))
    if len(diffs).__nonzero__():
        return True

    for key in original:
        if original[key] != other[key]:
            return True

    return False


class ConfigParamManager(object):

    original_configuration_values = None
    configuration = None

    def __init__(self, configuration_id):
        self.configuration_id = configuration_id

    def configuration_get(self, request):
        if self.configuration is None:
            configuration = api.trove.configuration_get(
                request, self.configuration_id)
            # need to make one that can be cached
            self.configuration = Configuration(
                self.configuration_id,
                configuration.name,
                configuration.description,
                configuration.datastore_name,
                configuration.datastore_version_name,
                configuration.created,
                configuration.updated)
            self.configuration.values = dict.copy(configuration.values)
            self.original_configuration_values = dict.copy(
                self.configuration.values)

        return self.get_configuration()

    def get_configuration(self):
        return self.configuration

    def create_config_value(self, name, value):
        return ConfigParam(self.configuration_id, name, value)

    def get_param(self, name):
        for key_name in self.configuration.values:
            if key_name == name:
                return self.create_config_value(
                    key_name, self.configuration.values[key_name])
        return None

    def update_param(self, name, value):
        self.configuration.values[name] = value
        update(self.configuration_id, self)

    def delete_param(self, name):
        del self.configuration.values[name]
        update(self.configuration_id, self)

    def add_param(self, name, value):
        self.update_param(name, value)

    def to_json(self):
        return jsonutils.dumps(self.configuration.values)

    def has_changes(self):
        return dict_has_changes(self.original_configuration_values,
                                self.configuration.values)


class ConfigParam(object):
    def __init__(self, configuration_id, name, value):
        self.configuration_id = configuration_id
        self.name = name
        self.value = value


class Configuration(object):
    def __init__(self, id, name, description, datastore_name,
                 datastore_version_name, created, updated):
        self.id = id
        self.name = name
        self.description = description
        self.datastore_name = datastore_name
        self.datastore_version_name = datastore_version_name
        self.created = created
        self.updated = updated


def validate_config_param_value(config_param, value):
    if (config_param.type in (u"boolean", u"float", u"integer", u"long")):
        if config_param.type == u"boolean":
            if (value.lower() not in ("true", "false")):
                return _('Value must be "true" or "false".')
        else:
            try:
                float(value)
            except ValueError:
                return _('Value must be a number.')

            min = getattr(config_param, "min", None)
            max = getattr(config_param, "max", None)
            try:
                val = adjust_type(config_param.type, value)
            except ValueError:
                return (_('Value must be of type %s.') % config_param.type)

            if min is not None and max is not None:
                if val < min or val > max:
                    return (_('Value must be a number '
                              'between %(min)s and %(max)s.') %
                            {"min": min, "max": max})
            elif min is not None:
                if val < min:
                    return _('Value must be a number greater '
                             'than or equal to %s.') % min
            elif max is not None:
                if val > max:
                    return _('Value must be a number '
                             'less than or equal to %s.') % max
    return None


def find_parameter(name, config_params):
    for param in config_params:
        if param.name == name:
            return param
    return None


def adjust_type(data_type, value):
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
