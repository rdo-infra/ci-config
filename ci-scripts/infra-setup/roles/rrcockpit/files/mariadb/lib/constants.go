package lib

var SKIPLIST_URL string = "https://opendev.org/openstack/openstack-tempest-skiplist/raw/branch/master/roles/validate-tempest/vars/tempest_skip.yml"
var ZUUL_WEEKEND_PIPELINE string = "https://review.rdoproject.org/zuul/api/builds?pipeline=openstack-periodic-weekend&limit=150"
var ZUUL_WEEKEND_PIPELINE_SUCCESS string = ZUUL_WEEKEND_PIPELINE + "&result=success"
var TEMPEST_TEST_REGEX string = `\{\d\}\s(setUpClass|tearDownClass\s)?\(?(?P<test>[^\(].*[^\)])(\))?\s\[\d.*\.\d.*\]\s...\s(?P<status>ok|FAILED)`
