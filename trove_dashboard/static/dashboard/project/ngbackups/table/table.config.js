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

(function() {
  'use strict';

  angular
    .module('horizon.dashboard.project.backups')
    .factory('horizon.dashboard.project.backups.tableConfigService',
      tableConfigService);

  tableConfigService.$inject = [
    'horizon.framework.util.extensible.service'
  ];

  /**
   * @ngdoc service
   * @name horizon.dashboard.project.ngbackups.tableConfigService
   * @description Backup table attributes
   */

  function tableConfigService(extensibleService) {
    var config = {
      selectAll: true,
      expand: true,
      trackId: 'id',
      columns: [{
        id: 'name',
        title: gettext('Name'),
        priority: 1,
        sortDefault: true
      },
      {
        id: 'datastore',
        title: gettext('Datastore'),
        priority: 1,
      },
      {
        id: 'datastoreversion',
        title: gettext('Datastore Version'),
        priority: 1,
      },
      {
        id: 'created',
        title: gettext('Created'),
        priority: 1,
      },
      {
        id: 'database',
        title: gettext('Database'),
        priority: 1,
      },
      {
        id: 'incremental',
        title: gettext('Incremental'),
        filters: ['yesno'],
        priority: 1,
      },
      {
        id: 'status',
        title: gettext('status'),
        priority: 1,
      }]
    };
    extensibleService(config, config.columns);
    return config;
  }
})();