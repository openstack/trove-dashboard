# plugin.sh - DevStack plugin.sh dispatch script trove-dashboard

TROVE_DASHBOARD_DIR=$(cd $(dirname $BASH_SOURCE)/.. && pwd)

function install_trove_dashboard {
    sudo pip install --upgrade ${TROVE_DASHBOARD_DIR}

    cp -a ${TROVE_DASHBOARD_DIR}/trove_dashboard/enabled/* ${DEST}/horizon/openstack_dashboard/enabled/
    python ${DEST}/horizon/manage.py collectstatic --noinput
    python ${DEST}/horizon/manage.py compress --force
}

# check for service enabled
if is_service_enabled trove-dashboard; then

    if [[ "$1" == "stack" && "$2" == "pre-install"  ]]; then
        # Set up system services
        # no-op
        :

    elif [[ "$1" == "stack" && "$2" == "install"  ]]; then
        # Perform installation of service source
        # no-op
        :

    elif [[ "$1" == "stack" && "$2" == "post-config"  ]]; then
        # Configure after the other layer 1 and 2 services have been configured
        echo_summary "Installing Trove UI"
        install_trove_dashboard

    elif [[ "$1" == "stack" && "$2" == "extra"  ]]; then
        # no-op
        :
    fi

    if [[ "$1" == "unstack"  ]]; then
        # no-op
        :
    fi

    if [[ "$1" == "clean"  ]]; then
        # Remove state and transient data
        # Remember clean.sh first calls unstack.sh
        # no-op
        :
    fi
fi
