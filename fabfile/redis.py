from fabric.api import task, env, cd, run, put, sudo, settings, prefix, get
from fabric.operations import local
from artichoke.helpers import prompt
from templates import render_to_file, render_to_remote_file

import os
import sys
import re

@task
def setup_redis():
    """Generates the necesary configuration for Redis"""
    run("wget http://redis.googlecode.com/files/redis-2.4.14.tar.gz")
    run("tar -xzf redis-2.4.14.tar.gz")
    with cd('redis-2.4.14'):
        sudo("mkdir -p /opt/redis")
        sudo("mkdir -p /var/redis/6379")
        sudo("make PREFIX=/opt/redis install")
        sudo("cp /opt/redis/bin/* /usr/local/bin")
        sudo("mkdir -p /etc/redis")
        sudo("cp utils/redis_init_script /etc/init.d/redis_6379")
    redis_conf = os.path.join(env.resources_dir, "redis_memdatabase.conf.tpl")
    remote_redis_conf = "/etc/redis/6379.conf"
    put(redis_conf, remote_redis_conf, use_sudo=True)
    sudo("rm -rf redis-2.4.14")
    sudo("rm -rf redis-2.4.14.tar.gz")
    sudo("/etc/init.d/redis_6379 start")

__all__ = [
    'setup_redis'
]
