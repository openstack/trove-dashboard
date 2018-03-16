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

import binascii
import six


def hexlify(text):
    """Hexlify raw text, return hexlified text."""
    if six.PY3:
        text = text.encode('utf-8')

    hexlified = binascii.hexlify(text)

    if six.PY3:
        hexlified = hexlified.decode('utf-8')

    return hexlified


def unhexlify(text):
    """Unhexlify raw text, return unhexlified text."""
    unhexlified = binascii.unhexlify(text)

    if six.PY3:
        unhexlified = unhexlified.decode('utf-8')

    return unhexlified
