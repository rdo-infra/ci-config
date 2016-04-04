pushd puppet-dlrn
mkdir .bundled_gems
export GEM_HOME=.bundled_gems
bundle install
bundle exec rake lint && bundle exec rake spec
output=$?
rm -rf .bundled_gems
exit $output
