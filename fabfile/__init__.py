import os

from fabric.api import env, task
from fabric.api import put, sudo, run
from fabric.operations import local as lrun

if env.ssh_config_path and os.path.isfile(os.path.expanduser(env.ssh_config_path)):
    env.use_ssh_config = True

env.shell = "/bin/bash -c"
env.local_code_root = os.path.join(os.path.dirname(__file__), "..")
env.templates_dir = os.path.join(os.path.dirname(__file__), "templates")
env.resources_dir = os.path.join(os.path.dirname(__file__), "resources")
env.disable_known_hosts = True

import apache
import ssh
import project
import git
import ubuntu
import deploy
import config
import apns
import dev

@task
def test_connection():
    """Tries various simple fabric operations to test the connection to the server."""

    run("echo testing echo...")
    run("echo $LANG")
    run("echo $LC_ALL")
    sudo("echo testing sudo echo...")
    lrun("touch /tmp/test-file")
    put("/tmp/test-file", "/tmp/")
