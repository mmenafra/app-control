from fabric.api import task, sudo

@task
def start(user="www-data", port=11211, max_memory=64):
    """
    start(user=www-data, port=11211, max_memory=64). Starts the memcached server daemon.

    """
    sudo("memcached -d -u %s -p %s -m %s" % (user, port, max_memory))
