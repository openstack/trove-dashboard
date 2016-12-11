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

from django.conf.urls import url  # noqa

from trove_dashboard.content.database_configurations \
    import views


CONFIGS = r'^(?P<configuration_id>[^/]+)/%s$'


urlpatterns = [
    url(r'^$',
        views.IndexView.as_view(),
        name='index'),
    url(r'^create$',
        views.CreateConfigurationView.as_view(),
        name='create'),
    url(CONFIGS % '',
        views.DetailView.as_view(),
        name='detail'),
    url(CONFIGS % 'add',
        views.AddParameterView.as_view(),
        name='add')
]
