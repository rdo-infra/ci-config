#!/usr/bin/env python
import argparse
import time
import requests


class ZuulStats:

    def __init__(self, server):
        self.server = server
        self.tag = None
        self.data = None
        self.get_zuul_stats()

    def get_zuul_stats(self):
        q = requests.get(self.server)
        self.data = q.json()

    def gate_queue(self):
        raise NotImplementedError

    def check_queue(self):
        raise NotImplementedError

    def total_check_jobs(self):
        raise NotImplementedError

    def total_gate_jobs(self):
        raise NotImplementedError

    def print_data(self):
        gate_q_time = self.gate_queue()
        check_q_time = self.check_queue()
        total_gate_jobs = self.total_gate_jobs()
        total_check_jobs = self.total_check_jobs()
        print(",".join(["zuul", "ci=%s" % self.tag]) +
              ' '
              'gate_queue=%s,'
              'check_queue=%s,'
              'total_gate_jobs=%s,'
              'total_check_jobs=%s' %
              (gate_q_time, check_q_time, total_gate_jobs, total_check_jobs)
              )


class ZuulOO(ZuulStats):
    def __init__(self):
        ZuulStats.__init__(self, 'http://zuul.openstack.org/status?json')
        self.tag = 'oo'

    def gate_queue(self):
        gate = self.data['pipelines'][1]
        ooo_num_gate = [k for k, i in enumerate(gate['change_queues'])
                        if i['name'] == 'tripleo'][0]
        q_time = gate['change_queues'][ooo_num_gate][
            'heads'][0][0]['enqueue_time']
        return int((time.time() - q_time/1000)/60)

    def check_queue(self):
        check = self.data['pipelines'][0]
        ooo_repos = [(k, i['name'])
                     for k, i in enumerate(check['change_queues'])
                     if 'tripleo' in i['name']]
        repo = ooo_repos[0][0]
        q_time = check['change_queues'][repo]['heads'][0][0]['enqueue_time']
        return int((time.time() - q_time/1000)/60)

    def total_gate_jobs(self):
        gate = self.data['pipelines'][1]
        ooo_num_gate = [k for k, i in enumerate(gate['change_queues'])
                        if i['name'] == 'tripleo'][0]
        patches = gate['change_queues'][ooo_num_gate]
        return sum([len(i['jobs']) for i in patches['heads'][0]])

    def total_check_jobs(self):
        check = self.data['pipelines'][0]
        ooo_repos = [(k, i['name'])
                     for k, i in enumerate(check['change_queues'])
                     if 'tripleo' in i['name']]
        summary = 0
        for repo_i in ooo_repos:
            repo = check['change_queues'][repo_i[0]]
            patches = repo['heads']
            for p in patches[0]:
                summary += len(p['jobs'])
        return summary


class ZuulRDO(ZuulStats):
    def __init__(self):
        ZuulStats.__init__(self,
                           'https://review.rdoproject.org/zuul/status.json')
        self.tag = 'rdo'

    def gate_queue(self):
        return 0

    def check_queue(self):
        num = [k for k, i in enumerate(self.data['pipelines'])
               if i['name'] == 'openstack-check'][0]
        check = self.data['pipelines'][num]
        ooo_repos = [(k, i['name'])
                     for k, i in enumerate(check['change_queues'])
                     if 'tripleo' in i['name']]
        repo = ooo_repos[0][0]
        q_time = check['change_queues'][repo]['heads'][0][0]['enqueue_time']
        return int((time.time() - q_time/1000)/60)

    def total_gate_jobs(self):
        return 0

    def total_check_jobs(self):
        num = [k for k, i in enumerate(self.data['pipelines'])
               if i['name'] == 'openstack-check'][0]
        check = self.data['pipelines'][num]
        ooo_repos = [(k, i['name'])
                     for k, i in enumerate(check['change_queues'])
                     if 'tripleo' in i['name']]
        summary = 0
        for repo_i in ooo_repos:
            repo = check['change_queues'][repo_i[0]]
            patches = repo['heads']
            for p in patches[0]:
                summary += len(p['jobs'])
        return summary


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('-z', '--zuul-server', dest="zuul", required=True,
                        choices=['rdo', 'oo'], help='URL of Zuul server')
    args = parser.parse_args()
    zuul = args.zuul
    RUNNERS = {
        'rdo': ZuulRDO,
        'oo': ZuulOO,
    }
    stats = RUNNERS[zuul]()
    stats.print_data()


if __name__ == '__main__':
    main()
