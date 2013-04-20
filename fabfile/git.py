from fabric.api import task, env, run, put, settings, cd
from fabric.operations import local
from artichoke.helpers import read

from webclient import WebClient
import os
import ssh
import sys

@task
def clone(repo, dest, branch='master'):
    with settings(warn_only=True):
        result = run("git clone %s %s" % (repo, dest))
        with cd(dest):
            run("git checkout %s" % branch)
        if result.failed:
            query = "Could not clone the project, do you want to delete the destination path and retry, just retry or abort?"
            options = ["delete", "retry", "abort", "ignore"]

            selected = read(query, options=options)
            if selected == "abort":
                sys.exit(1);
            elif selected == "ignore":
                return
            elif selected == "retry":
                clone(repo, dest, branch)
            elif selected == "delete":
                run ("rm -rf %s" % dest)
                clone(repo, dest, branch)

@task
def add_key(gituser, gitpass):
    """add_key:<githubuser>,<githubpass>. Adds a new key to github.

    """
    run("mkdir -p ~/.ssh")
    
    key_file = "id_rsa.git"

    private_key_file = os.path.join("/tmp/", key_file)
    public_key_file = "%s.pub" % private_key_file

    remote_full_key_path = os.path.join("/home", env.user, ".ssh", key_file)
    ssh.add_ssh_config("github.com", key_file=remote_full_key_path)

    local("rm -rf %s %s" % (private_key_file, public_key_file))
    local("ssh-keygen -t rsa -f %s " % private_key_file)

    with file(public_key_file, "r") as f:
        key = f.read()
        print "====BEGIN PUBLIC KEY====="
        print key
        print "====END PUBLIC KEY======="
        data = {
            'title' : "key for: %s" % env.host,
            'key' : key
        }

    client = WebClient("https://api.github.com", verbose=True)
    client.authenticate(username=gituser, password=gitpass)
    put(private_key_file, "~/.ssh")
    run("chmod 600 %s" % remote_full_key_path)

    client.post("/user/keys", data)

__all__ = [
    'add_key',
]
