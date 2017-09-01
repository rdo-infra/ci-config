function activate_dlrnapi_venv() {
    if [ ! -d $WORKSPACE/dlrnapi_venv ]; then
        virtualenv --system-site-packages $WORKSPACE/dlrnapi_venv
        pip install dlrnapi_client shyaml
    fi
    source $WORKSPACE/dlrnapi_venv/bin/activate
}

function deactivate_dlrnapi_venv {
    [[ $VIRTUAL_ENV = $WORKSPACE/dlrnapi_venv ]] && deactivate
}
