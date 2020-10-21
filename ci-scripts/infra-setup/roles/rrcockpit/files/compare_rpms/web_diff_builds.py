from flask import Flask, render_template, flash, redirect, session, url_for
from forms import WebDiffBuilds
from diff_tripleo_builds import diff_builds
from cachecontrol import CacheControl
import requests
import os
from prettytable import PrettyTable

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

diff = diff_builds.DiffBuilds()
sess = requests.session()
cached_sess = CacheControl(sess)


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Home')

@app.route('/docs')
def docs():
    return render_template('docs.html', title='Docs')

@app.route('/diff_builds', methods=['GET', 'POST'])
def diff_builds():
    form = WebDiffBuilds()
    if form.validate_on_submit():

        return result(form.diff_type.data, form.control_baseurl.data, form.test_baseurl.data)
    return render_template('diff_builds.html', title='Diff Builds Results', form=form)


@app.route('/result')
def result(diff_type, control_url, test_url):
    all_available = True
    no_diff = False
    full_package_diff = {}
    ignore_packages = {}

    nodes = diff.get_the_nodes(cached_sess, control_url,
                               test_url, all_available)

    control_list = diff.get_repoquery_logs(
        cached_sess, control_url, nodes['control']['undercloud'])
    test_list = diff.get_repoquery_logs(
        cached_sess, test_url, nodes['test']['undercloud'])

    control_list = diff.parse_list(control_list)
    test_list = diff.parse_list(test_list)

    control_list = diff.find_highest_version(control_list)
    test_list = diff.find_highest_version(test_list)

    package_diff = diff.diff_packages(control_list,
                                      test_list,
                                      no_diff,
                                      ignore_packages,
                                      not_found_message="not installed")
    full_package_diff['repo_query'] = package_diff

    column_list = ['Node', 'Package_Name',
                   'Control Package Version', 'Test Package Version']
    result = diff.display_packages_table(
        "repo_query", column_list, full_package_diff['repo_query'], just_return=True)

    return render_template('result.html', result=result, d_type=diff_type, c_url=control_url, t_url=test_url, title='Result')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port="8585")
