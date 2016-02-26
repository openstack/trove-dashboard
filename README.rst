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
::

    ./run_tests.sh

Editing Code
------------

Apache
~~~~~~

Make a change to trove-dashboard then goto to the horizon directory and
compress the code with django and then restart apache.::

    # rsync code to /opt/stack/trove-dashboard
    # copy or link files from trove-dashboard/enabled/* to horizon/openstack_dashboard/local/enabled/
    cd /opt/stack/horizon
    python manage.py compress
    python manage.py collectstatic --noinput
    sudo service apache2 restart


Django
~~~~~~

You can also speed up development time using the django test server instead of
apache.::

    /opt/stack/horizon/run_tests.sh --runserver

If you set COMPRESS_ENABLED and COMPRESS_OFFLINE to False in local_settings.py
that allows you to bypass the compress and collectstatic as well.

NOTE:
=====

As of the Mitaka release, the dashboard for trove is now maintained outside of
the Horizon codebase, in this repository.

Links:
------

Trove project: https://git.openstack.org/openstack/trove

Trove at wiki.openstack.org: https://wiki.openstack.org/wiki/Trove

Launchpad project: https://launchpad.net/trove
