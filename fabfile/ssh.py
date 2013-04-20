from fabric.api import task, env, cd, run
from fabric.operations import local
import os


def get_ssh_config(name, host=None, username=None, key_file=None):
    out = []
    out.append("Host %s" % name)

    if host is not None:
        out.append("    HostName %s" % host)
    if username is not None:
        out.append("    User %s" % username)
    if key_file is not None:
        out.append("    IdentityFile %s" % os.path.join("~/.ssh",key_file))

    print "key file is %s" % key_file

    return "\n" + ("\n".join(out))

@task
def add_ssh_config(name, host=None, username=None, key_file=None):
    """<name>,[host],[username],[key_file]. Adds an ssh config to .ssh/config"""

    config_str = get_ssh_config(name, host, username, key_file)

    run("mkdir -p ~/.ssh")
    run('echo "%s" >> ~/.ssh/config' % config_str)

@task
def add_key(username, passphrase="", config_name=""):
    """add_key:<username>,[passphrase],[config_name]. Adds a ssh key
    to a remote user on the remote server.
    If a config_name is provided, a new entry in ~/.ssh config
    will be generated to login to the server using the new key.

    """
    key_file = "_".join([username, env.host]) + "_id_rsa"
    full_key_path = os.path.join(os.path.expanduser("~"), ".ssh", key_file)
    local("ssh-keygen -N '%s' -f %s" % (passphrase, full_key_path))

    with file("%s.pub" % full_key_path) as f:
        key = f.read()
        run("mkdir -p /home/%s/.ssh" % username)
        run("chown %(user)s:%(user)s /home/%(user)s/.ssh -R" % {'user': username})
        with cd(os.path.join("/home", username, ".ssh")):
            run("echo '%s' > authorized_keys" % key)
            run("chmod 644 authorized_keys")
            run("chown %(user)s:%(user)s authorized_keys" % {'user': username})

    if config_name:
        print "saving config %s" % config_name
        config_str = get_ssh_config(config_name, env.host, username,
            key_file)

        with file(os.path.expanduser("~/.ssh/config"), "a") as f:
            f.write(config_str)
        print "file written"
