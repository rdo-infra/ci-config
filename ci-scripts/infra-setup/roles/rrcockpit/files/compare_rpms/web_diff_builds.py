import logging
import os

import requests
from cachecontrol import CacheControl
from diff_tripleo_builds import diff_builds
from flask import Flask, render_template
from forms import WebDiffBuilds
from prettytable import PrettyTable

app = Flask(__name__, static_url_path='')
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY') or 'you-will-never-guess'

diff = diff_builds.DiffBuilds()
sess = requests.session()
cached_sess = CacheControl(sess)

# To-DO consider:
# https://pypi.org/project/PyLog2html/
debug_format = '%(asctime)s %(levelname)-8s %(message)s'
logging.basicConfig(level=logging.INFO,
                    format=debug_format,
                    datefmt='%m-%d %H:%M',
                    filename='static/info.log',
                    filemode='w')


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Home')


@app.route('/info')
def send_to_info():
    return app.send_static_file('info.log')


@app.route('/debug')
def send_to_debug():
    return app.send_static_file('debug.log')


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
    elif node == "exception_caught":
        t.add_row([node, "error",
                   package_diff[0][0],
                   package_diff[0][1]
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
    error = {}
    column_list = ['ERROR:', 'Exception', 'sorry', 'Package_Name']
    try:
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

    except Exception as e:
        exception_caught = ['error', "{}, {}".format(str(e), ("check "
                            "the debug log"))]
        error['exception_caught'] = [exception_caught]
        full_package_diff = error

    result = ""
    for key in full_package_diff:
        if len(full_package_diff[key]) == 0:
            full_package_diff[key] = {'no_diff': [["No Diff Found",
                                                  "No Diff Found"],
                                                  ["No Diff Found",
                                                  "No Diff Found"]]}
        result += "<br>"
        result += display_packages_table(key,
                                         column_list,
                                         full_package_diff[key],
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
