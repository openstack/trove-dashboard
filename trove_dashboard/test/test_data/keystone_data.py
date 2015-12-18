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


def data(TEST):

    # Add trove to the keystone data
    TEST.service_catalog.append(
        {"type": "database",
         "name": "Trove",
         "endpoints_links": [],
         "endpoints": [
             {"region": "RegionOne",
              "adminURL": "http://admin.trove.example.com:8779/v1.0",
              "publicURL": "http://public.trove.example.com:8779/v1.0",
              "internalURL": "http://int.trove.example.com:8779/v1.0"}]}
    )
