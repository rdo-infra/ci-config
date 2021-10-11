function activate_dlrnapi_venv {
    if [ ! -d $WORKSPACE/dlrnapi_venv ]; then
        if [ ! command -v virtualenv ]; then
            python3 -m venv  --system-site-packages $WORKSPACE/dlrnapi_venv
        else
            virtualenv --system-site-packages $WORKSPACE/dlrnapi_venv
        fi
    fi
    source $WORKSPACE/dlrnapi_venv/bin/activate
    pip install -U dlrnapi_client shyaml
}

function deactivate_dlrnapi_venv {
    # deactivate can fail with unbound variable, so we need +u
    set +u
    [[ $VIRTUAL_ENV = $WORKSPACE/dlrnapi_venv ]] && deactivate
}
