from fabric.api import task, sudo, settings

@task
def apt(cmd):
    """apt:<cmd>. Just like: $ sudo apt-get <cmd>

    """
    sudo("apt-get %s" % cmd)

@task
def new_user(admin_username, admin_password):
    """new_user:<name>,<password>. Adds a new user to the server.

    """
    # Create the admin group and add it to the sudoers file
    with settings(warn_only=True):
        admin_group = 'admin'
        sudo('addgroup {group}'.format(group=admin_group))
        sudo('echo "%{group} ALL=(ALL) ALL" >> /etc/sudoers'.format(
            group=admin_group))

    # Create the new admin user (default group=username); add to admin group
    sudo('adduser {username} --disabled-password --gecos ""'.format(
        username=admin_username))
    sudo('adduser {username} {group}'.format(
        username=admin_username,
        group=admin_group))

    # Set the password for the new admin user
    sudo('echo "{username}:{password}" | chpasswd'.format(
        username=admin_username,
        password=admin_password))
