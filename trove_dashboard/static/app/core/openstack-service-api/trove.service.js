/**
 * Copyright 2016 IBM Corp.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

(function () {
  'use strict';

  /**
   * @ngdoc overview
   * @name horizon.dashboard.project.ngbackups
   * @description Dashboard module for the ngbackups panel.
   */

  angular
    .module('horizon.app.core.openstack-service-api')
    .factory('horizon.app.core.openstack-service-api.trove', TroveAPI);

  TroveAPI.$inject = [
    'horizon.framework.util.http.service',
    'horizon.framework.widgets.toast.service'
  ];

  function TroveAPI(apiService, toastService) {
    var service = {
      getBackups: getBackups
    };

    return service;

  function getBackups() {
    return apiService.get('/api/trove/backups/')
      .error(function() {
        toastService.add('error', gettext('Unable to retrieve the Backups.'));
      });
    }
  }

}());
