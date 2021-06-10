from datetime import datetime

import requests
from bs4 import BeautifulSoup
from rich import print
from rich.console import Console
from rich.table import Table

console = Console()


def find_date_of_delorean_repo(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    for tag in soup.find_all('tr'):
        if tag.find('a', href='delorean.repo'):
            return tag.find_all('td')[2].text.strip()


def last_promotion_date(url):
    date_string = find_date_of_delorean_repo(url)
    return datetime.strptime(date_string, '%Y-%m-%d %H:%M')


def days_behind_promotion(url):
    delta = datetime.now() - last_promotion_date(url)
    return delta.days


def new_content_available(url1, url2):
    return requests.get(url1).text != requests.get(url2).text


def a(base_url, distro, releases):
    print(f"[yellow]{distro}[/yellow] based releases")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Release", style="dim", width=30)
    table.add_column("Days behind promotion", style="dim", width=30)
    table.add_column("New content available?", style="dim", width=30)
    for release in releases:
        url = base_url + distro + '-' + release + "/current-tripleo/"
        url1 = "{}{}-{}/current-tripleo/delorean.repo.md5".format(base_url,
                                                                  distro,
                                                                  release)
        url2 = "{}{}-{}/tripleo-ci-testing/delorean.repo.md5".format(base_url,
                                                                     distro,
                                                                     release)
        days = str(days_behind_promotion(url))
        new_content = str(new_content_available(url1, url2))
        table.add_row(release, days, new_content)
    print(table)


def days_behind_promotion_for_every_release():
    base_url = "https://trunk.rdoproject.org/"
    distro = 'centos8'
    upstream_releases = ['master', 'wallaby', 'victoria', 'ussuri', 'train']
    a(base_url, distro, upstream_releases)

    distro = 'centos7'
    old_upstream_releases = ['train', 'stein', 'queens']
    a(base_url, distro, old_upstream_releases)

    base_url = "http://osp-trunk.hosted.upshift.rdu2.redhat.com/"
    distro = 'rhel8'
    downstream_releases = ['osp16-2', 'osp17']
    a(base_url, distro, downstream_releases)


def main():
    days_behind_promotion_for_every_release()


if __name__ == '__main__':
    main()
