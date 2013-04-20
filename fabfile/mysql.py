from fabric.api import run, task, env
from time import gmtime, strftime
import os

class DbConfig:

    def __init__(self, name, engine, user, password, host, port):
        self.name = name
        self.engine = engine.split(".")[-1]
        self.user = user
        self.password = password
        self.host = host
        self.port = port

    def get_dict(self, config_name):
        return {
            config_name: {
                "ENGINE": "django.db.backends.%s" % self.engine,
                "NAME": self.name,
                "HOST": self.host,
                "USER": self.user,
                "PASSWORD": self.password,
                "PORT": self.port,
                "OPTIONS": {'init_command': 'SET storage_engine=INNODB,character_set_connection=utf8,collation_connection=utf8_unicode_ci,character_set_client=utf8,collation_database=utf8_unicode_ci'}
            }
        }


def get_db_config(config=None):
    config = config or env.config

    out = DbConfig(
        name=config.Database.name,
        engine=config.Database.engine,
        user=config.Database.user,
        password=config.Database.password,
        host=config.Database.host,
        port=config.Database.port
    )
    return out

@task
def db_info():
    """Prints the current database configuration."""

    db = get_db_config()
    print db.get_dict('default')

@task
def query(sql, db="", mysql_user='root', mysql_pass="", mysql_host="localhost"):
    """query:<sql>,[db],[mysql_user]: Executes the given query on the mysql server."""

    if type(sql) is list:
        sql = " ".join(sql)

    cmd = 'mysql -h%s --user=%s --password=%s -e "%s" %s'
    cmd %= (mysql_host, mysql_user, mysql_pass, sql, db)

    run(cmd)

def stdin(filename, mysql_user, mysql_pass, mysql_database, mysql_host="localhost"):
    cmd = 'mysql -h%s --user=%s --password=%s %s < %s'
    cmd %= (mysql_host, mysql_user, mysql_pass, mysql_database, filename)

    run(cmd)

@task
def dump_db(dump_dir, name, mysql_user, mysql_pass, mysql_hostname='localhost'):
    """dump_db:<dump_dir>,<name>,<mysql_user>,<mysql_pass>. Dumps the specified db
    to the given directory"""

    # generating dump file name
    run("mkdir -p %s" % dump_dir)
    dump_name = strftime("%Y-%m-%d %H:%M:%S", gmtime())
    dump_name = os.path.join(dump_dir, "%s.sql" % dump_name)

    # dump into dump_dir/<dump_name>
    cmd = "mysqldump -h%s -u%s -p%s %s> '%s'"
    cmd %= (mysql_hostname, mysql_user, mysql_pass, name, dump_name)
    run(cmd)

    # compressing dump
    compressed_name = "%s.gz" % dump_name
    run("gzip '%s'" % dump_name)

    # removing raw dump
    run("rm -f '%s'" % dump_name)
    print "Dump saved on %s" %compressed_name
    return compressed_name

@task
def create_user(dbname, user, password, root_pass):
    """create_user:<user>,<password>,<root_pass>. Creates new DB user
    with the specified password."""

    sql = []
    sql.append("GRANT ALL ON %s.* TO '%s'@'localhost' IDENTIFIED BY '%s';" % (dbname, user, password))
    query(sql=sql, db=dbname, mysql_user="root", mysql_pass=root_pass)

@task
def grant_db(name, owner, root_pass):
    """grant_db:<name>,<owner>,<root_pass>. Grants full access to a user
    on the specified database."""

    sql = []
    sql.append("GRANT USAGE ON %s.* TO '%s'@'localhost';" % (name, owner))
    sql.append("GRANT ALL ON %s.* TO '$dbuser'@'localhost' WITH GRANT OPTION;" % name)
    sql.append("FLUSH PRIVILEGES;")
    query(sql=sql, db="mysql", mysql_user="root", mysql_pass=root_pass)

@task
def create_db(name, root_pass, owner=None):
    """create_db:<name>,<root_pass>,[owner]. Creates a new database."""

    sql = []
    sql.append("CREATE DATABASE %s DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_unicode_ci;" % name)
    query(sql=sql, db="mysql", mysql_user="root", mysql_pass=root_pass)
    if owner is not None:
        grant_db(name, owner, root_pass)

@task
def drop_db(name, mysql_user='root', mysql_pass=""):
    """drop_db:<name>,<root_pass>. Deletes the specified database."""

    sql = []
    sql.append("DROP DATABASE IF EXISTS %s;" % name)
    query(sql=sql, db="mysql", mysql_user=mysql_user, mysql_pass=mysql_pass)

@task
def drop_user(user, root_pass):
    """drop_user:<user>,<root_pass>. Deletes the specified db user."""

    if user == "":
        raise Exception("Must provide a valid username")

    sql = []
    sql.append("GRANT USAGE ON *.* TO '%s'@'localhost';" % (user))
    sql.append("DROP USER %s@localhost;" % user)
    sql.append("FLUSH PRIVILEGES;")
    query(sql=sql, db="mysql", mysql_user="root", mysql_pass=root_pass)

@task
def flush_db(name, mysql_user, mysql_pass, mysql_host="localhost"):
    """flush_db:<name>,<mysql_user>,<mysql_pass>. Deletes all tables
    on the specified database."""

    foreign_checks = "SET FOREIGN_KEY_CHECKS = %s; "
    enable_foreign_checks = foreign_checks % 1
    disable_foreign_checks = foreign_checks % 0
    cmd = "(echo \"%s\"; (mysqldump -h%s -u%s -p%s --add-drop-table --no-data %s | grep ^DROP); echo \"%s\"; ) | mysql -h%s -u%s -p%s %s"
    cmd %= (
        disable_foreign_checks,
        mysql_host, mysql_user, mysql_pass, name,
        enable_foreign_checks,
        mysql_host, mysql_user, mysql_pass, name,
    )
    run(cmd)
