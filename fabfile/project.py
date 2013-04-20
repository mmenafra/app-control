from fabric.api import task, env, cd, run, put, sudo, settings, prefix, get
from fabric.operations import local
from fabric.contrib.console import confirm
from artichoke.helpers import prompt
from templates import render_to_file, render_to_remote_file

import os
import sys
import re

import mysql
import apns


@task
def generate_supervisor_conf():
    """Generates the supervisor configuration to run the server as a deamon"""

    tmp_file = "/tmp/supervisor.conf"
    target_file = os.path.join(env.config.ApiServer.document_root, "local", "conf")

    run("mkdir -p %s" % target_file)
    render_to_file("supervisor.conf", tmp_file)

    put(tmp_file, target_file)
    print "supervisor config file generated at %s" % target_file

@task
def test(module="api", verbose=1):
    """Runs the django test suite."""

    verbose = int(verbose)
    if verbose == 1:
        grep_filter = '| sed -re"s/\\\\\\n/\\n/g" | sed -re\'s:\\\\":":g\''
    else:
        grep_filter = "| grep '\(Assertion\)\|\(\.\.\.\.\)\|\(Ran\)'"

    manage("test %s --failfast 2>&1 %s " % (module, grep_filter))

@task
def manage(command):
    """manage:<command>. Just like 'python manage.py <command>'"""

    python_bin = os.path.join(env.config.ApiServer.document_root, "env", "bin", "python")

    with prefix('export LC_ALL=en_US.UTF-8'):
        with prefix('export LANG=en_US.UTF-8'):
            with cd(env.config.ApiServer.document_root):
                return run("%s manage.py %s" % (python_bin, command))

@task
def create_dbuser():
    """Creates the django application database."""

    db = mysql.get_db_config()
    if db.engine == "mysql":
        mysql.create_user(db.name, db.user, db.password, env.config.MySQL.root_password)
    elif db.engine == "sqlite3":
        pass
    else:
        raise Exception("Database engine %s not supported." % db.engine)


@task
def drop_dbuser(db_root_pass=None):
    """Deletes the django application user from the database."""

    db = mysql.get_db_config()
    if db.engine == "mysql":
        mysql.drop_user(db.user, env.config.MySQL.root_password)
    elif db.engine == "sqlite3":
        pass
    else:
        raise Exception("Database engine %s not supported." % db.engine)


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


@task
def drop_db():
    """Deletes the django application database."""

    db = mysql.get_db_config()
    if db.engine == "mysql":
        mysql.drop_db(db.name, "root", env.config.MySQL.root_password)
    elif db.engine == "sqlite3":
        if os.path.exists(db.name, env.config.MySQL.root_password):
            run("rm -rf %s" % db.name)
    else:
        raise Exception("Database engine %s not supported." % db.engine)


@task
def flush_db():
    """Resets the django application databse.
    Removing and recreating all tables and initial data."""

    db = mysql.get_db_config()

    if db.engine == 'sqlite3':
        if os.path.exists(db.name):
            run("rm %s -rf" % db.name)
    elif db.engine == 'mysql':
        mysql.flush_db(
            db.name, mysql_user=db.user,
            mysql_pass=db.password,
            mysql_host=db.host
        )
    else:
        raise Exception("Database engine %s not supported." % db.engine)

    manage("syncdb")
    migrate()
    manage("loadbasedata")

    if db.engine == 'sqlite3':
        run("chmod 777 %s" % db.name)


@task
def syncdb():
    """Shortcut to python manage.py syncdb"""

    python_bin = os.path.join(env.config.ApiServer.document_root, "env", "bin", "python")
    with cd(env.config.ApiServer.document_root):
        cmd = "echo 'no' | %s manage.py syncdb" % python_bin
        run(cmd)

@task
def migrate():
    """Executes south migrations to update the DB."""

    manage("migrate")
    #result = manage("schemamigration api --auto")

@task
def update():
    """Updates the project server code and executes migrations."""
    with settings(warn_only=True):
        if env.host == 'prod':
            if not confirm("Are you sure you want to deploy code to Production?", default=False):
               sys.exit(1)
            
            result = backup_db()

            if not result:
                msg = "Could not backup db. Continue?"
                if not prompt(msg):
                    print "Aborting..."
                    sys.exit(1)
                    
    with cd(env.config.ApiServer.document_root):
        run("git fetch origin")
        run("git checkout %s" % env.config.branch)
        run("git pull origin %s" % env.config.branch)
        run("./env/bin/pip install --requirement ./scripts/requirements.pip")
        configure_api()
        compile_static()

    sudo("/etc/init.d/celeryd restart")
    sudo("/etc/init.d/memcached restart")
    sudo("supervisorctl stop klooff")
    sudo("supervisorctl start klooff")

@task
def crontab():
    """Deploys the crontab to the remote server"""
    if env.host != 'local':
        output = "/tmp/crontab"
        local_crontab_file = render_to_file("crontab", output)

        put(local_crontab_file, '/tmp/crontab')
        run('crontab /tmp/crontab')

@task
def update_certificates():
    "Updates the apns and ssl certificates."

    local_certs_dir = os.path.join(env.local_code_root, env.config.ApiServer.certificates_dir)
    remote_certs_dir = os.path.join(env.config.ApiServer.document_root, "local")

    local_copy = os.path.join("/tmp/certs")
    local("rm -rf %s" % local_copy)
    local("cp -r %s %s" % (local_certs_dir, local_copy))

    run("mkdir -p %s" % remote_certs_dir)
    with cd(remote_certs_dir):
        run("rm -rf certs")

    put(local_copy, remote_certs_dir)

@task
def configure_api():
    """Setups all the API Server configuration.
    Including nginx, django settings, crontab."""

    #Certificates
    update_certificates()

    #setup nginx with gunicorn and supervisor
    remote_local_dir = os.path.join(env.config.ApiServer.document_root, "local")

    bin_dir = os.path.join(remote_local_dir, "bin")
    conf_dir = os.path.join(remote_local_dir, "conf")
    log_dir = os.path.join(remote_local_dir, "log")

    #run("rm -rf %s %s %s" % (bin_dir, conf_dir, log_dir))
    run("mkdir -p %s" % bin_dir)
    run("mkdir -p %s" % conf_dir)
    run("mkdir -p %s" % log_dir)

    run("touch %s" % os.path.join(remote_local_dir, "__init__.py"))
    generate_local_settings()

    remote_nginx_conf = os.path.join(remote_local_dir, "conf", "nginx-server.conf")
    remote_supervisor_conf = os.path.join(remote_local_dir, "conf", "supervisor.conf")
    remote_newrelic_conf = os.path.join(remote_local_dir, "conf", "newrelic.conf")

    remote_runserver = os.path.join(remote_local_dir, "bin", "runserver")

    render_to_remote_file("runserver", remote_runserver)
    render_to_remote_file("supervisor.conf", remote_supervisor_conf)
    render_to_remote_file("nginx-server.conf", remote_nginx_conf)
    render_to_remote_file("newrelic.conf", remote_newrelic_conf)

    run("chmod +x %s" % remote_runserver)

    sudo(
        "rm -rf /etc/nginx/sites-available/klooff /etc/nginx/sites-enabled/klooff "
        "/etc/supervisor/conf.d/klooff.conf")
    sudo("ln -s %s /etc/nginx/sites-available/klooff" % remote_nginx_conf)
    sudo("ln -s /etc/nginx/sites-available/klooff /etc/nginx/sites-enabled/klooff")
    print remote_supervisor_conf
    sudo("ln -s %s /etc/supervisor/conf.d/klooff.conf" % remote_supervisor_conf)

    sudo("supervisorctl stop klooff")
    sudo("supervisorctl start klooff")
    sudo("/etc/init.d/supervisor stop")
    with settings(warn_only=True):
        sudo("unlink /var/run/supervisor.sock")
    sudo("/etc/init.d/supervisor start")
    sudo("/etc/init.d/nginx restart")

    #and configure django
    apns.restart()
    #manage("syncdb")
    migrate()
    crontab()

@task
def generate_local_settings():
    """Generates the local_settings.py file from the config ini file"""

    run("mkdir -p %s" % os.path.join(env.config.ApiServer.document_root, "local"))

    tmp_file = "/tmp/local_settings.py"
    with file(tmp_file, "w") as settings_file:
        db = mysql.get_db_config()
        certificates_dir = os.path.join(env.config.ApiServer.document_root, "local", "certs")

        settings_file.write("DEBUG = %s\n" % (env.config.build == "development"))
        settings_file.write("DATABASES = %s\n" % repr(db.get_dict("default")))
        settings_file.write("STATIC_URL = %s\n" % repr(env.config.Django.static_url))
        settings_file.write("UPLOAD_ROOT_PATH = %s\n" % repr(os.path.join(env.config.ApiServer.document_root, 'media')))
        settings_file.write("CERTIFICATES_DIR = %s\n" % repr(certificates_dir))
        #settings_file.write("RAVEN_CONFIG = {\n\t'register_signals': True,\n\t'dsn' : %s,\n}\n" % repr(env.config.Sentry.dsn))

        settings_file.write("DEPLOYMENT_NAME = %s\n" % repr(env.config.name))
        settings_file.write("WEB_HOSTNAME = %s\n" % repr(env.config.WebServer.hostname))

        settings_file.write("CELERY_REDIS_HOST = %s\n" % repr(env.config.Celery.celery_redis_host))
        settings_file.write("REDIS_READER_HOST = %s\n" % repr(env.config.Redis.redis_reader_host))
        settings_file.write("REDIS_WRITER_HOST = %s\n" % repr(env.config.Redis.redis_writer_host))
        settings_file.write("REDIS_PORT = %s\n" % repr(env.config.Redis.redis_port))
        settings_file.write("SESSION_REDIS_HOST = %s\n" % repr(env.config.Session.session_redis_host))
        settings_file.write("MONGO_HOST = %s\n" % repr(env.config.Mongodb.mongo_host))

    put(tmp_file, os.path.join(env.config.ApiServer.document_root, "local", "settings.py"))

@task
def backup_db():
    """Backups the server database to the 'local/backup' directory"""

    dump_dir = os.path.join(env.config.ApiServer.document_root, "local", "backup")
    run("mkdir -p %s" % dump_dir)
    return mysql.dump_db(
        dump_dir, env.config.Database.name,
        env.config.Database.user, env.config.Database.password,
        env.config.Database.host
    )

@task
def local_backup_db():
    """Does a backup and copies it to /tmp/backup.sql.gz on local machine"""
    remote_file = backup_db()
    local_file = "/tmp/backup.sql"
    local_file_compressed = "%s.gz" % local_file
    get(remote_file, local_file_compressed)
    return local_file_compressed

@task
def load_from_local_backup_db():
    """Uploads the local backup db from task local_backup_db and puts it on the remote database."""
    # BE SURE THAT VARIABLES local_file_compressed IN local_backup_db AND local_file IN load_from_local_backup_db ARE THE SAME
    local_file = "/tmp/backup.sql.gz"
    remote_file = "/tmp/loaded-backup.sql"
    remote_file_compressed = "%s.gz" % remote_file
    put(local_file, remote_file_compressed)
    run('gunzip %s' % remote_file_compressed)
    mysql.stdin(
            remote_file,
            env.config.Database.user,
            env.config.Database.password,
            env.config.Database.name,
            env.config.Database.host
            )

def delete_files(path, extension):
    """delete_files:<path>,<extension>. Recursively delete all files matching
    the given extension."""

    run("find %s -name *.%s -print0 | xargs -0 rm -rf" % (path, extension))

@task
def compile_static():
    """Collects and compiles all static files."""

    collected_dir = os.path.join(env.config.ApiServer.document_root, "local", "static")
    run("mkdir -p %s" % collected_dir)
    with cd(collected_dir):
        run("rm -rf *")

    manage("collectstatic --noinput")

    #Compile less
    less_files = [
        'css/landing.less',
        'css/viewer.less',
        'css/stats.less',
        'css/stats/style.less',
    ]

    with cd(collected_dir):
        for filename in less_files:
            cmd = "lessc %(input)s %(output)s"
            cmd %= {'input': filename, 'output': filename[:-4] + "css"}
            run(cmd)

    run("coffee --output %(dir)s --compile %(dir)s" % {'dir': collected_dir})

    delete_files(collected_dir, "coffee")
    delete_files(collected_dir, "less")

    media_user_uploads = os.path.join(env.config.ApiServer.document_root, "media", "user_uploads")
    static_user_uploads = os.path.join(env.config.ApiServer.document_root, "local", "static", "user_uploads")
    run("ln -s %s %s" % (media_user_uploads, static_user_uploads))

    print "static files collected to %s" % collected_dir

    return collected_dir

@task
def log(name=None):
    log_dir = os.path.join(env.config.ApiServer.document_root, "local", "log")

    with cd(log_dir):
        if name:
            run("tail -f %s" % name)
        else:
            run("ls -l")

@task
def grep_log(regexp=None,name=None):
    """
    grep_log:regexp,filename
    does grep over a log file. If no log file given, then greps recursively among all log files.
    """
    log_dir = os.path.join(env.config.ApiServer.document_root, "local", "log")

    with cd(log_dir):
        if name:
            return run("grep -e %s %s" % (regexp, name))
        else:
            return run("grep -r -e \"%s\" %s" % (regexp, log_dir))

@task
def recover_media_from_logs():
    """
    This is an awful thing to do, but it works.
    Images uploaded to rackspace but lost in Media objects can be recovered with this method.
    """

    urls = grep_log("Media\([0-9]*\).source","celery_w1.log")
    regexp = re.compile("Media\((?P<media>\d+)\).source = (?P<url>\S+)")

    for mediafile in iter(urls.splitlines()):
        result = regexp.search(mediafile)
        manage('fixmediacloudfiles %s %s' % (result.group('media'), result.group('url')))

__all__ = [
    "flush_db",
    "drop_db",
    "create_db",
    "drop_dbuser",
    "create_dbuser",
    "manage",
    "test",
    "get_db_config",
    "syncdb",
    "migrate",
    'generate_local_settings',
    "update",
    'crontab',
    "configure_api",
    "backup_db",
    "local_backup_db",
    "load_from_local_backup_db",
    "compile_static",
    "update_certificates",
    "log",
    "grep_log",
    "recover_media_from_logs",
    "flush_sentry_db"
]
