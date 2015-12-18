OpenStack Dashboard plugin for Trove project
============================================

How to use with Horizon on server:
----------------------------------

Use pip to install the package on the server running Horizon. Then either copy
or link the files in trove_dashboard/enabled to
openstack_dashboard/local/enabled. This step will cause the Horizon service to
pick up the trove plugin when it starts.

How to use with devstack:
-------------------------

Add the following to your devstack ``local.conf`` file::

enable_plugin trove-dashboard git://git.openstack.org/openstack/trove-dashboard


To run unit tests:
------------------

./run_tests.sh

NOTE:
=====

As of the Mitaka release, the dashboard for trove is now maintained
outside of the Horizon codebase, in this repository.

Links:
------

Trove project: https://git.openstack.org/openstack/trove

Trove at wiki.openstack.org: https://wiki.openstack.org/wiki/Trove

Launchpad project: https://launchpad.net/trove
