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

from django.conf.urls import url

from trove_dashboard.content.databases.logs import views

LOGS = r'^(?P<filename>[^/]+)/%s$'

urlpatterns = [
    url(LOGS % 'console', views.console, name='console'),
    url(LOGS % 'download_log', views.download_log, name='download_log'),
    url(LOGS % 'full_log', views.full_log, name='full_log'),
    url(LOGS % 'log_contents',
        views.LogContentsView.as_view(), name='log_contents'),
]
