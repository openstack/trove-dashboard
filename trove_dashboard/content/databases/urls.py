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

from django.conf.urls import include
from django.conf.urls import url

from trove_dashboard.content.databases.logs import urls as logs_urls
from trove_dashboard.content.databases import views

BASEINSTANCES = r'^(?P<instance_id>[^/]+)/%s'
INSTANCES = BASEINSTANCES + '$'
USERS = r'^(?P<instance_id>[^/]+)/(?P<user_name>[^/]+)/' \
        r'(?P<user_host>[^/]+)/%s$'


urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^launch$', views.LaunchInstanceView.as_view(), name='launch'),
    url(INSTANCES % '', views.DetailView.as_view(), name='detail'),
    url(INSTANCES % 'resize_volume', views.ResizeVolumeView.as_view(),
        name='resize_volume'),
    url(INSTANCES % 'resize_instance', views.ResizeInstanceView.as_view(),
        name='resize_instance'),
    url(INSTANCES % 'create_user', views.CreateUserView.as_view(),
        name='create_user'),
    url(USERS % 'edit_user', views.EditUserView.as_view(),
        name='edit_user'),
    url(USERS % 'access_detail', views.AccessDetailView.as_view(),
        name='access_detail'),
    url(INSTANCES % 'create_database', views.CreateDatabaseView.as_view(),
        name='create_database'),
    url(INSTANCES % 'promote_to_replica_source',
        views.PromoteToReplicaSourceView.as_view(),
        name='promote_to_replica_source'),
    url(INSTANCES % 'attach_config', views.AttachConfigurationView.as_view(),
        name='attach_config'),
    url(INSTANCES % 'manage_root', views.ManageRootView.as_view(),
        name='manage_root'),
    url(BASEINSTANCES % 'logs/', include(logs_urls, namespace='logs')),
]
