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

from horizon.test.settings import *  # noqa
from openstack_dashboard.test.settings import *  # noqa

INSTALLED_APPS = list(INSTALLED_APPS)
INSTALLED_APPS.append('trove_dashboard.content.database_backups')
INSTALLED_APPS.append('trove_dashboard.content.database_clusters')
INSTALLED_APPS.append('trove_dashboard.content.database_configurations')
INSTALLED_APPS.append('trove_dashboard.content.databases')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'OPTIONS': {
            'MAX_ENTRIES': 1200,
            'CULL_FREQUENCY': 20
        }
    }
}
