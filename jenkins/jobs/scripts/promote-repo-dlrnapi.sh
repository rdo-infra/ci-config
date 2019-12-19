set -e
# A properties file crafted from the upstream properties job is required
if [[ -n "${properties}" ]]; then
    curl -s -O "${properties}"
    source "./$(basename ${properties})"
else
    exit 1
fi

# Setup virtualenv for dlrnapi
virtualenv --system-site-packages dlrnapi_venv
source dlrnapi_venv/bin/activate
pip install -U dlrnapi_client shyaml

: ${DLRNAPI_USERNAME:="ciuser"}
: ${PROMOTE_TO:="${promotion_symlink}"}
: ${DLRNAPI_URL:="${delorean_api_url}"}
: ${DLRNAPI_PASSWORD:="${DLRNAPI_PASSWD}"}

for component_url in ${delorean_components_url}; do
    curl -sLo commit.yaml ${component_url}/commit.yaml
    COMMIT_HASH=$(shyaml get-value commits.0.commit_hash < ./commit.yaml)
    DISTRO_HASH=$(shyaml get-value commits.0.distro_hash < ./commit.yaml)

    # Assign label to the specific hash using the DLRN API
    dlrnapi --url $DLRNAPI_URL \
        --username $DLRNAPI_USERNAME \
        repo-promote \
        --commit-hash $COMMIT_HASH \
        --distro-hash $DISTRO_HASH \
        --promote-name $PROMOTE_TO
done
