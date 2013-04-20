from fabric.api import task, env, settings, cd, run, sudo, put
from fabric.contrib import files
from templates import render_to_file

from artichoke.helpers import prompt

import git
import project
import sys
import ubuntu
import ssh
import os
import config
import mysql
import redis
import mongodb

@task
def full():
    "Shortcut task for a full application deployment on the remote server."
    #config.set("%s@%s.ini" % (env.user, env.host))
    with settings(warn_only=True):
        result = run("ssh -T git@github.com")
        if "successfully authenticated" not in result:
            git.add_key(env.config.GitHub.username, env.config.GitHub.password)

    install_prerequisites()
    db()
    manage("syncdb")
    api()
    config.save()
    project.crontab()
    project.compile_static()
    celeryd()

@task
def api():
    """Setups a project database using django on the remote server."""
    wsgi_file = os.path.join(env.config.ApiServer.document_root, "django.wsgi")
    repo = "git@github.com:klooff/klooff-server.git"

    if not files.exists(wsgi_file):
        print "Can't file the project code at %s." % env.config.ApiServer.document_root
        query = "Do you want to clone it from github?"
        if prompt(query):
            git.clone(repo, env.config.ApiServer.document_root, env.config.branch)
            run("chmod 777 %s" % os.path.join(env.config.ApiServer.document_root, "media", "user_uploads"))
        else:
            print "Aborting."
            sys.exit(1)

    virtualenv()
    project.configure_api()

@task
def pip_requirements():
    """Installs all pip requirements."""

    with cd(env.config.ApiServer.document_root):
        run("./env/bin/pip install --requirement ./scripts/requirements.pip")

@task
def virtualenv():
    """Intializes the virtual env"""

    virtualenv_dir = os.path.join(env.config.ApiServer.document_root, "env")

    if files.exists(virtualenv_dir):
        print "The virtualenv directory already exists at %s." % virtualenv_dir
        query = "Do you want to delete it and reinitialize it?"
        if prompt(query):
            run("rm -rf %s" % virtualenv_dir)
        else:
            return

    with cd(env.config.ApiServer.document_root):
        run("virtualenv env")

        if files.exists("/usr/lib/x86_64-linux-gnu/libfreetype.so"):
            run("ln -s /usr/lib/x86_64-linux-gnu/libfreetype.so `pwd`/env/lib/")
            run("ln -s /usr/lib/x86_64-linux-gnu/libz.so `pwd`/env/lib/")
            run("ln -s /usr/lib/x86_64-linux-gnu/libjpeg.so `pwd`/env/lib/")
        else:
            run("ln -s /usr/lib/i386-linux-gnu/libfreetype.so `pwd`/env/lib/")
            run("ln -s /usr/lib/i386-linux-gnu/libz.so `pwd`/env/lib/")
            run("ln -s /usr/lib/i386-linux-gnu/libjpeg.so `pwd`/env/lib/")

    pip_requirements()


@task
def db():
    """Setups a project database on the remote server."""

    print "Configuring %s" % env.config.project_name
    project.create_db()
    project.create_dbuser()

@task
def celeryd():
    """Installs the celery daemon"""

    config_tmp_file = "/tmp/celeryd_config"
    config_tmp_file_remote = "/tmp/celeryd_config_remote"
    tmp_file = "/tmp/celeryd"

    render_to_file("celeryd", config_tmp_file)

    put(config_tmp_file, config_tmp_file_remote)
    put(os.path.join(env.resources_dir, "celeryd"), tmp_file)

    sudo("cp %s /etc/init.d/celeryd" % tmp_file)
    sudo("cp %s /etc/default/celeryd" % config_tmp_file_remote)
    sudo("chmod +x /etc/init.d/celeryd")
    sudo("/etc/init.d/celeryd restart")


@task
def install_prerequisites():
    """Install all required prerequisites on the remote machine."""
    prereqs_file = os.path.join(env.resources_dir, "install-prerequisites")
    remote_file = "/tmp/install-prerequisites"

    sudo("rm -f %s" % remote_file)
    redis_conf = os.path.join(env.resources_dir, "redis.conf.tpl")
    remote_redis_conf = "/tmp/redis.conf.tpl"

    put(prereqs_file, remote_file)
    put(redis_conf, remote_redis_conf)
    run("chmod +x %s" % remote_file)
    run(remote_file)

@task
def setup_memdatabase():
    """Installs and sets mongodb and redis"""
    print "set up redis ..."
    redis.setup_redis()
    print "set up mongo ..."
    mongodb.setup_mongodb()
    print "finished setup_memdatabase."

__all__ = [
    'full',
    'api',
    'db',
    'install_prerequisites',
    'celeryd',
    'virtualenv',
    'pip_requirements',
    'setup_memdatabase'
]
