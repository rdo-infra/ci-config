import argparse
import base64
import json
import logging
import os
import re
import subprocess
import time

import requests
from podman import ApiConnection, errors, images

logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger(__name__)


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zuul-api", help="Zuul api endpoint",
                        default="https://review.rdoproject.org/zuul/api/")
    parser.add_argument("--pull-registry", help="Registry to pull images from",
                        default="trunk.registry.rdoproject.org")
    parser.add_argument("--push-registry", help="Registry to push images to",
                        default="quay.io/tripleoci")
    parser.add_argument("--release", help="Release of images",
                        default="tripleomaster")
    parser.add_argument("--podman-uri", help="URI for podman",
                        default=("unix://localhost/run/user/1000/podman/"
                                 "podman.sock"))
    parser.add_argument("--job", help="Name of the job to collect the list of"
                        "the containers",
                        default="periodic-tripleo-ci-build-containers-ubi-8-"
                                "push")
    parser.add_argument("--image-tag", help="Tag to be pulled for the image",
                        default="current-tripleo")
    parser.add_argument("--prune", help="Should remove actual images before"
                        "pull new ones", action="store_true", default=False)
    parser.add_argument("--push", help="Push images to push registry",
                        action="store_true", default=False)
    parser.add_argument("--pull", help="Pull images from registry",
                        action="store_true", default=False)
    parser.add_argument("--username", help="Username to push", required=True)
    parser.add_argument("--password", help="Password to push", required=True)
    parser.add_argument("--container", help="Container to pull or push")
    args = parser.parse_args()
    return args


def push_image(api, args, image, **kwargs):
    try:
        image_id = image["Id"][:12]
        image_name = get_image_name(image)
        LOG.debug("Pushing image {} to {}".format(image_name,
                                                  args.push_registry))
        kwargs["destination"] = "{}/{}".format(args.push_registry, image_name)
        path = api.join("/images/{}/push".format(api.quote(image_id)), kwargs)

        auth = encode_username_password(args.username, args.password)

        header = {"X-Registry-Auth": auth}
        response = api.request("POST", path, headers=header)
        return json.loads(response.read())
    except errors.NotFoundError as e:
        images._report_not_found(e, e.response)
    except json.decoder.JSONDecodeError:
        pass


def get_process():
    process = os.popen("ps aux | grep -i 'podman system' | grep -v 'grep' "
                       "| awk '{ print $2 }'").read(
                            ).strip().split('\n')
    LOG.debug("Podman process {}".format(process))
    return process


def encode_username_password(username, password):
    user_pass = ('{ "username": "%s", "password": "%s" }' %
                 (username, password))
    user_pass = user_pass.encode("ascii")
    user_pass = base64.b64encode(user_pass)
    return user_pass.decode("ascii")


def pull_image(api, args, image, **kwargs):
    try:
        LOG.debug("Pulling image {}".format(image))

        reference = "{}/{}/{}".format(args.pull_registry, args.release, image)
        kwargs["reference"] = reference
        response = api.request("POST", api.join("/images/pull", kwargs))
        return json.loads(response.read())
    except errors.NotFoundError as e:
        images._report_not_found(e, e.response)
    except json.decoder.JSONDecodeError:
        pass


def remove_image(api, image, **kwargs):
    if not image:
        return
    try:
        LOG.info("Removing image {}".format(image))
        url = "/images/{}".format(api.quote(image))
        response = api.request("DELETE", url)
        return json.loads(response.read())
    except errors.NotFoundError as e:
        images._report_not_found(e, e.response)


def get_jobs_url(args):
    zuul_job_url = "{}/builds?job_name={}".format(args.zuul_api, args.job)
    resp = requests.get(zuul_job_url)
    if resp.status_code == 200:
        return [r["log_url"] for r in resp.json() if r["result"] == "SUCCESS"]
    return []


def read_containers_built(url):
    built_log = "{}{}".format(url, "logs/containers-successfully-built.log")
    response = requests.get(built_log)
    result = []
    #  exp = r"([a-zA-Z-]+)\s+(\w+)[\w\s]+"
    exp = r"(?<=\/)\w+\/(.*?)(?=\s+)\s+(\w+)"

    if response.status_code == 200:
        lines = response.text.split('\n')
        for line in lines:
            res = re.search(exp, line)
            if res:
                result.append(res.group(1, 2))
    return result


def get_image_name(image):
    full_name = image["RepoTags"][0]
    if 'tripleo' in full_name:
        name = full_name[full_name.rfind('/') + 1:]
        return name
    return None


if __name__ == "__main__":

    args = get_parser()
    LOG.setLevel(logging.DEBUG)

    pid = None
    if get_process()[0] == '':
        LOG.debug("Initializing podman service REST API")
        pid = subprocess.Popen(["podman", "system", "service", "--time=0"])
        time.sleep(3)

    with ApiConnection(args.podman_uri) as api:
        if args.prune:
            images_list = images.list_images(api)
            for image in images_list:
                name = get_image_name(image)
                if args.container:
                    if args.container == name:
                        remove_image(api, name)
                        break
                else:
                    remove_image(api, name)

        if args.pull:
            if args.container:
                pull_image(api, args, args.container)
            else:
                url = get_jobs_url(args)[0]
                containers = read_containers_built(url)
                for container in containers:
                    container_name = "{}:{}".format(container[0],
                                                    args.image_tag)
                    pull_image(api, args, container_name)

        if args.push:
            images_list = images.list_images(api)
            for image in images_list:
                if args.container:
                    image_name = get_image_name(image)
                    if args.container == image_name:
                        push_image(api, args, image)
                        break
                else:
                    push_image(api, args, image)
    if pid:
        LOG.debug("Destroying podman service")
        pid.terminate()
