from perfcomp import ansbile_playbook, rpm_diff, pip_diff
from perfcomp.graphs import graph_ansible_playbook


class JobDiff:

    def __init__(self, good, bad, ansible_playbooks_diff, rpm_diff, pip_diff):
        self.good, self.bad = good, bad
        self.ansible_diff = ansible_playbooks_diff
        self.rpm_diff = rpm_diff
        self.pip_diff = pip_diff

    def ansible_playbooks_diff(self):
        data = ansbile_playbook.compare(self.good, self.bad)
        images = {}
        for i in data:
            images[i] = graph_ansible_playbook(data[i], i) if data[i] else None
        return {'ans_data': data, 'images': images}

    def rpm_files_diff(self):
        inline, uniq1, uniq2 = rpm_diff.rpms(self.good, self.bad)
        # sometimes we need to inmprove the diff
        inline, uniq1, uniq2 = rpm_diff.check_packages(inline, uniq1, uniq2)
        inline = [rpm_diff.colorize_diff(i) for i in inline]
        return {
            'inline': inline, "uniq1": uniq1, "uniq2": uniq2,
            'rpms_diff_max_length': max([len(l) for l in (uniq1, uniq2)])
        }

    def pip_files_diff(self):
        inline, uniq1, uniq2 = pip_diff.pip_modules(self.good, self.bad)
        return {
            'pip_inline': inline, "pip_uniq1": uniq1, "pip_uniq2": uniq2,
            'pip_diff_max_length': max([len(l) for l in (uniq1, uniq2)])
        }

    def generate(self):
        data_results = {}
        if self.ansible_diff:
            data_results.update(self.ansible_playbooks_diff())
        if self.rpm_diff:
            data_results.update(self.rpm_files_diff())
        if self.pip_diff:
            data_results.update(self.pip_files_diff())
        return data_results
