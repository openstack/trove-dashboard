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

from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import workflows
from oslo_log import log as logging

from trove_dashboard import api
from trove_dashboard.content.databases \
    import tables as project_tables

LOG = logging.getLogger(__name__)


class BackupStrategyDetailsAction(workflows.Action):
    instance = forms.ChoiceField(label=_("Database Instance"),
                                 required=False,
                                 initial=None)
    swift_container = forms.CharField(max_length=256,
                                      widget=forms.TextInput(),
                                      label=_("Swift Container Name"),
                                      help_text=_(
                                          "User defined swift container name.")
                                      )

    class Meta(object):
        name = _("Details")
        help_text_template = \
            "project/backup_strategies/_backup_strategy_help.html"

    def populate_instance_choices(self, request, context):
        LOG.info("Obtaining list of instances.")
        try:
            instances = api.trove.instance_list(request)
        except Exception:
            instances = []
            msg = _("Unable to list database instances to backup.")
            exceptions.handle(request, msg)
        choises = [(None, "")]
        for i in instances:
            if i.status in project_tables.ACTIVE_STATES:
                choises.append((i.id, i.name))
        return choises


class SetBackupStrategyDetails(workflows.Step):
    action_class = BackupStrategyDetailsAction
    contributes = ["instance", "swift_container"]


class CreateBackupStrategy(workflows.Workflow):
    slug = "create_backup_strategy"
    name = _("Backup Strategy")
    finalize_button_name = _("Create Backup Strategy")
    success_message = _("Backup strategy created")
    failure_message = _('Unable to create backup strategy')
    success_url = "horizon:project:backup_strategies:index"
    default_steps = [SetBackupStrategyDetails]

    def handle(self, request, context):
        try:
            LOG.info("Creating backup strategy")
            api.trove.backup_strategy_create(request,
                                             context['instance'],
                                             context['swift_container'])
            return True
        except Exception:
            LOG.exception("Exception while creating backup strategy")
            msg = _('Error creating backup strategy.')
            exceptions.handle(request, msg)
            return False
