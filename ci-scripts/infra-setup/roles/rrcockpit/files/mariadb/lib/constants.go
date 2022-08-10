package lib


var SKIPLIST_URL string = "https://opendev.org/openstack/openstack-tempest-skiplist/raw/branch/master/roles/validate-tempest/vars/tempest_skip.yml"
const ZUUL_URL = "https://review.rdoproject.org/zuul"
const ZUUL_API_URL = ZUUL_URL + "/api/builds"
var ZUUL_WEEKEND_PIPELINE string = ZUUL_API_URL + "?pipeline=openstack-periodic-weekend&limit=150"
var ZUUL_WEEKEND_PIPELINE_SUCCESS string = ZUUL_WEEKEND_PIPELINE + "&result=success"
var TEMPEST_TEST_REGEX string = `\{\d\}\s(setUpClass|tearDownClass\s)?\(?(?P<test>[^\(].*[^\)])(\))?\s\[\d.*\.\d.*\]\s...\s(?P<status>ok|FAILED)`
