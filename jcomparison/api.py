# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, abort
from perfcomp.jobdiff import JobDiff


app = Flask(__name__)


@app.route('/compare', methods=['GET'])
def compare():
    good = request.args.get('good')
    bad = request.args.get('bad')
    # TODO: add these selections to web page
    ansible_playbooks_diff = request.args.get('ansible', True)
    rpm_diff = request.args.get('rpm', True)
    pip_diff = request.args.get('pip', True)
    if not good or not bad:
        abort(404)
    data = JobDiff(good, bad,
                   ansible_playbooks_diff=ansible_playbooks_diff,
                   rpm_diff_b=rpm_diff,
                   pip_diff_b=pip_diff
                   ).generate()
    return render_template('full.html.j2', **data)


@app.route("/")
def index():
    return render_template('compare.html')


if __name__ == '__main__':
    app.run(host="0.0.0.0")
