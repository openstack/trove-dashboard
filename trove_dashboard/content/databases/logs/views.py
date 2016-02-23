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

from django import http
from django import shortcuts
from django.utils.translation import ugettext_lazy as _
from django.views import generic

from horizon import exceptions
from horizon import messages

from openstack_dashboard import api as dash_api
from trove_dashboard import api

FULL_LOG_VALUE = 0
DEFAULT_LINES = 50


class LogContentsView(generic.TemplateView):
    template_name = 'project/databases/logs/view_log.html'
    preload = False

    def get_context_data(self, **kwargs):
        context = super(LogContentsView, self).get_context_data(**kwargs)
        context["instance_id"] = kwargs['instance_id']
        context["filename"] = kwargs['filename']
        context["publish"] = ''

        try:
            log_length = int(kwargs['lines'])
        except Exception:
            log_length = DEFAULT_LINES

        context["log_length"] = log_length
        context["log_contents"] = get_contents(self.request,
                                               kwargs['instance_id'],
                                               kwargs['filename'],
                                               False,
                                               log_length)
        return context


def get_contents(request, instance_id, filename, publish, lines):
    try:
        log_generator = api.trove.log_tail(request,
                                           instance_id,
                                           filename,
                                           publish,
                                           lines,
                                           dash_api.swift.swift_api(request))
        data = ""
        for log_part in log_generator():
            data += log_part
    except Exception as e:
        data = _('Unable to load {0} log\n{1}').format(filename, e.message)
    return data


def build_response(request, instance_id, filename, tail):
    data = (_('Unable to load {0} log for instance "{1}".')
            .format(filename, instance_id))

    if request.GET.get('publish'):
        publish = True
    else:
        publish = False

    try:
        data = get_contents(request,
                            instance_id,
                            filename,
                            publish,
                            int(tail))
    except Exception:
        exceptions.handle(request, ignore=True)
    return http.HttpResponse(data.encode('utf-8'), content_type='text/plain')


def console(request, instance_id, filename):
    tail = request.GET.get('length')
    if not tail or (tail and not tail.isdigit()):
        msg = _('Log length must be a nonnegative integer.')
        messages.warning(request, msg)
        data = (_('Unable to load {0} log for instance "{1}".')
                .format(filename, instance_id))
        return http.HttpResponse(data.encode('utf-8'),
                                 content_type='text/plain')

    return build_response(request, instance_id, filename, tail)


def full_log(request, instance_id, filename):
    return build_response(request, instance_id, filename, FULL_LOG_VALUE)


def download_log(request, instance_id, filename):
    try:
        publish_value = request.GET.get('publish')
        if publish_value:
            publish = True
        else:
            publish = False

        data = get_contents(request,
                            instance_id,
                            filename,
                            publish,
                            FULL_LOG_VALUE)
        response = http.HttpResponse()
        response.write(data)
        response['Content-Disposition'] = ('attachment; '
                                           'filename="%s.log"' % filename)
        response['Content-Length'] = str(len(response.content))
        return response

    except Exception as e:
        messages.error(request, _('Error downloading log file: %s') % e)
        return shortcuts.redirect(request.build_absolute_uri())
