from perfcomp.graphlib import make_bar


def graph_ansible_playbook(*args, **kwargs):
    chart = make_bar(*args, **kwargs)
    return chart
