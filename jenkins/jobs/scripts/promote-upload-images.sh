mkdir -p stable
rsync -av rdo@artifacts.ci.centos.org::rdo/images/$RDO_VERSION_DIR/delorean/$LOCATION/testing/ stable/
rsync -av stable/ rdo@artifacts.ci.centos.org::rdo/images/$RDO_VERSION_DIR/delorean/$LOCATION/stable/
rm -rf stable