# Copyright 2016 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.views import generic

from trove_dashboard.api import trove

from openstack_dashboard.api.rest import urls
from openstack_dashboard.api.rest import utils as rest_utils


@urls.register
class Backup(generic.View):
    """API for retrieving information about a single backup.
    """
    url_regex = r'trove_dashboard/backups/(?P<backup_name>[^/]+)$'

    @rest_utils.ajax()
    def get(self, request, backup_id):
        """Get a specific backup.
        """
        return trove.backup_get(request, backup_id).to_dict()


@urls.register
class Backups(generic.View):
    """API for backups.
    """
    url_regex = r'trove/backups/$'

    @rest_utils.ajax()
    def get(self, request):
        """Get a list of the Backups.

        The returned result is an object with property 'items' and each
        item under this is a backup.
        """
        result = trove.backup_list(request)
        backups = []
        for b in result:
            instance = trove.instance_get(request, b.instance_id)
            backups.append({'id': b.id,
                            'name': b.name,
                            'datastore': b.datastore.get('type'),
                            'datastoreversion': b.datastore.get('version'),
                            'created': b.created,
                            'database': instance.name,
                            'incremental': bool(b.parent_id),
                            'status': b.status
                            })
        return backups

    @rest_utils.ajax(data_required=True)
    def delete(self, request):
        """Delete one or more backup by name.

        Returns HTTP 204 (no content) on successful deletion.
        """
        for backup_id in request.DATA:
            trove.backup_delete(request, backup_id)

    @rest_utils.ajax(data_required=True)
    def create(self, request):
        """Create a new backup.

        Returns the new backup object on success.
        """
        new_backup = trove.backup_create(request, **request.DATA)
        return rest_utils.CreatedResponse(
            '/api/messaging/backups/%s' % new_backup.name,
            new_backup.to_dict())
