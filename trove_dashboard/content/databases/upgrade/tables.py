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

from horizon import tables

from trove_dashboard.content import databases


class UpgradeInstanceAction(tables.LinkAction):
    name = "upgrade_instance_action"
    verbose_name = _("Upgrade Instance")
    url = "horizon:project:databases:upgrade:upgrade_instance"
    classes = ("ajax-modal",)
    policy_rules = (("database", "instance:update"),)

    def allowed(self, request, instance):
        if instance.status not in databases.tables.ACTIVE_STATES:
            return False

        return True

    def get_link_url(self, datum):
        instance_id = self.table.get_object_id(datum)
        return reverse(self.url, args=[instance_id])
