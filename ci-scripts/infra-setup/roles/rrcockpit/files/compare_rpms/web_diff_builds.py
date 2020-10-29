import os

import requests
from cachecontrol import CacheControl
from diff_tripleo_builds import diff_builds
from flask import Flask, render_template
from forms import WebDiffBuilds
from prettytable import PrettyTable

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY') or 'you-will-never-guess'

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


@app.route('/web_diff_builds', methods=['GET', 'POST'])
def web_diff_builds():
    form = WebDiffBuilds()
    if form.validate_on_submit():
        return result(form.diff_type.data,
                      form.control_baseurl.data,
                      form.test_baseurl.data,
                      form.undercloud_only.data)
    return render_template('web_diff_builds.html',
                           title='Diff Builds Results',
                           form=form)


def display_packages_table(node,
                           column_list,
                           package_diff,
                           extra_package_data=False):
    """ print a table with rows showing the
    rpm package name, version and optionally,
    realease.
    """
    t = PrettyTable()
    t.field_names = column_list
    t.left_padding_width = 1
    t.format = True

    if node == "error: node_mismatch":
        t.add_row([node, "error",
                   package_diff['control'],
                   package_diff['test']
                   ])
    else:
        for package_name in list(package_diff.keys()):
            t.add_row([node, package_name,
                       package_diff[package_name][0][1],
                       package_diff[package_name][1][1]
                       ])
    return t.get_html_string(sortby="Package_Name")


@app.route('/result')
def result(diff_type, control_url, test_url, undercloud_only):

    undercloud_only = bool(undercloud_only)
    if diff_type == "ci_installed":
        all_available = False
        ignore_packages = {}
        core_results = diff.execute_installed_package_diff(cached_sess,
                                                           control_url,
                                                           test_url,
                                                           all_available,
                                                           ignore_packages,
                                                           undercloud_only
                                                           )
        full_package_diff = core_results[0]
        column_list = core_results[1]

    elif diff_type == "all_available":
        all_available = True
        ignore_packages = {}
        core_results = diff.execute_repoquery_diff(cached_sess,
                                                   control_url,
                                                   test_url,
                                                   all_available,
                                                   ignore_packages
                                                   )
        full_package_diff = core_results[0]
        column_list = core_results[1]

    elif diff_type == "diff_compose":
        all_available = False
        ignore_packages = {}
        core_results = diff.execute_compose_diff(cached_sess,
                                                 control_url,
                                                 test_url,
                                                 all_available,
                                                 ignore_packages
                                                 )
        full_package_diff = core_results[0]
        column_list = core_results[1]

    result = ""
    for k in full_package_diff.keys():
        result += "<br>"
        result += display_packages_table(k,
                                         column_list,
                                         full_package_diff[k],
                                         extra_package_data=False
                                         )

    return render_template('result.html',
                           result=result,
                           d_type=diff_type,
                           c_url=control_url,
                           t_url=test_url,
                           title='Result')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port="8585", debug=True)
