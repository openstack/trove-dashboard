OpenStack Dashboard plugin for Trove project
============================================

.. image:: https://governance.openstack.org/tc/badges/trove-dashboard.svg
    :target: https://governance.openstack.org/tc/reference/tags/index.html


How to use with Horizon on server:
----------------------------------

Use pip to install the package on the server running Horizon. Then either copy
or link the files in trove_dashboard/enabled to
openstack_dashboard/local/enabled. This step will cause the Horizon service to
pick up the trove plugin when it starts.

How to use with devstack:
-------------------------

Add the following to your devstack ``local.conf`` file::

    enable_plugin trove-dashboard https://opendev.org/openstack/trove-dashboard

Here is a full example of devstack ``local.conf`` file that includes the trove plugin::

    [[local|localrc]]
    RECLONE=False
    HOST_IP=<your-host-ip-here>

    enable_plugin trove https://opendev.org/openstack/trove
    enable_plugin trove-dashboard https://opendev.org/openstack/trove-dashboard

    LIBS_FROM_GIT+=,python-troveclient
    DATABASE_PASSWORD=password
    ADMIN_PASSWORD=password
    SERVICE_PASSWORD=password
    SERVICE_TOKEN=password
    RABBIT_PASSWORD=password
    LOGFILE=$DEST/logs/stack.sh.log
    VERBOSE=True
    LOG_COLOR=False
    LOGDAYS=1

    IPV4_ADDRS_SAFE_TO_USE=10.111.0.0/26
    FIXED_RANGE=10.111.0.0/26
    NETWORK_GATEWAY=10.111.0.1
    FLOATING_RANGE=172.30.5.0/24
    PUBLIC_NETWORK_GATEWAY=172.30.5.1

    # Pre-requisites
    ENABLED_SERVICES=rabbit,mysql,key

    # Horizon
    enable_service horizon

    # Nova
    enable_service n-api
    enable_service n-cpu
    enable_service n-cond
    enable_service n-sch
    enable_service n-api-meta
    enable_service placement-api
    enable_service placement-client

    # Glance
    enable_service g-api
    enable_service g-reg

    # Cinder
    enable_service cinder
    enable_service c-api
    enable_service c-vol
    enable_service c-sch

    # Neutron
    enable_service q-svc
    enable_service q-agt
    enable_service q-dhcp
    enable_service q-l3
    enable_service q-meta

    # enable DVR
    Q_PLUGIN=ml2
    Q_ML2_TENANT_NETWORK_TYPE=vxlan
    Q_DVR_MODE=legacy

    # Swift
    ENABLED_SERVICES+=,swift
    SWIFT_HASH=66a3d6b56c1f479c8b4e70ab5c2000f5
    SWIFT_REPLICAS=1


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


Settings
~~~~~~~~

The use of a cross-process cache such as Memcached is required.

Install Memcached itself and a Memcached binding such as python-memcached.

For a single horizon instance use the CACHES setting like the example below.::

    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': '127.0.0.1:11211',
        },
    }

For multiple horizon instances behind a load balancer configure each instance
to use the same cache like the example below.::

    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': [u'10.2.100.133:11211', u'10.2.100.134:11211'']
        },
    }


NOTE:
=====

As of the Mitaka release, the dashboard for trove is now maintained outside of
the Horizon codebase, in this repository.

Links:
------

Trove project: https://opendev.org/openstack/trove/

Trove at wiki.openstack.org: https://wiki.openstack.org/wiki/Trove

Launchpad project: https://launchpad.net/trove-dashboard
