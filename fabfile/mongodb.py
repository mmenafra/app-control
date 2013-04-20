from fabric.api import task, env, cd, run, put, sudo, settings, prefix, get
from fabric.operations import local
from artichoke.helpers import prompt
from templates import render_to_file, render_to_remote_file

import os
import sys
import re

@task
def setup_mongodb():
    """Generates the necesary configuration for MongoDB"""
    sudo("apt-key %s" % "adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10")
    sudo("mkdir -p /etc/apt/sources.list.d/ /data/db")
    sudo("echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' > /etc/apt/sources.list.d/10gen.list")
    sudo("apt-get update")
    sudo("apt-get %s" % "install mongodb-10gen")


__all__ = [
    'setup_mongodb'
]
