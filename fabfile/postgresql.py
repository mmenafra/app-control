from fabric.api import task, env, cd, run, put, sudo, settings, prefix, get
from fabric.operations import local
from artichoke.helpers import prompt
from templates import render_to_file, render_to_remote_file

import os
import sys
import re


@task
def setup_postgresql():
    """Generates the necesary configuration for postgresql"""

    sudo("apt-get %s" % "install postgresql-8.4")
    sudo("apt-get %s" % "install postgresql-server-dev-8.4")

    sudo("/etc/init.d/postgresql-8.4 restart")

@task
def create_user(user, password, root_pass):
    """create_user:<user>,<password>,<root_pass>. Creates new DB user
    with the specified password."""

    pass

@task
def create_db():
    """Creates the django application database."""

    db = mysql.get_db_config()
    if db.engine == "mysql":
        mysql.create_db(db.name, env.config.MySQL.root_password, owner=db.user)
    elif db.engine == "sqlite3":
        run("touch %s" % env.config.Database.name)
    else:
        raise Exception("Database engine %s not supported." % db.engine)
    

__all__ = [
    "setup_postgresql", 
    "create_user", 
    "create_db"
]
