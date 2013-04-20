from artichoke import DefaultManager, Config
from artichoke.helpers import read, prompt
from fabric.api import env, task, run
import os

chars = ''.join(chr(c) if chr(c).isupper() or chr(c).islower() else '_' for c in range(256))


class MagicDefaultManager(DefaultManager):

    def __init__(self, env):
        self.env = env

    def SSH__user(self):
        return env.user

    def Global__project_root(self):
        query = "Enter the project code root path"
        default = "/home/%s/%s" % (self.env.user, self.config.project_name)

        return read(query, default=default)

    def Global__python_version(self):
        major, minor, rev = tuple(run("python --version").split(' ')[1].split("."))
        return "%s.%s" % (major, minor)

    def Global__build(self):

        query = "Select deployment mode"
        options = ["development", "production"]
        default = "development"

        return read(query, options=options, default=default)

    def Global__name(self):

        query = "Enter deployment name"

        return read(query)

    def Global__project_name(self):
        query = "Enter the project name"
        return read(query)

    def Global__branch(self):
        query = "Enter the git branch for current project"

        default = "master"

        return read(query, default=default)

    def Database__engine(self):
        query = "Select database engine"
        options = [
            "postgresql_psycopg2", "postgresql",
            "sqlite3", "oracle", "mysql"
        ]

        default = "mysql"

        return read(query, options=options, default=default)

    def Database__config_name(self):
        query = "Select configuration name"
        default = "default"

        return read(query, default=default)

    def Database__name(self):
        name = self.config.project_name.translate(chars)

        if self.config.Database.engine == 'sqlite3':
            query = "Select path to database"
            default = "/tmp/%s.sqlite3" % name
        else:
            query = "Select database name"
            default = name

        return read(query, default=default)

    def Database__user(self):
        if self.config.Database.engine == 'sqlite3':
            return ""

        query = "Select database user"
        default = self.config.project_name.translate(chars).lower()

        return read(query, default=default)

    def Database__password(self):
        if self.config.Database.engine == 'sqlite3':
            return ""

        query = "Select database password"
        default = self.config.project_name.translate(chars).lower()

        return read(query, default=default)

    def Database__host(self):
        if self.config.Database.engine == 'sqlite3':
            return ""

        query = "Select database host"
        default = "localhost"

        return read(query, default=default)

    def Database__port(self):
        if self.config.Database.engine == 'sqlite3':
            return ""

        query = "Select database port"
        default = "use %s default" % self.config.Database.engine

        value = read(query, default=default)
        return "" if value == default else value

    def MySQL__root_password(self):
        query = "Enter MySQL root password"
        return read(query)

    def GitHub__username(self):
        query = "Enter Github username"
        return read(query)

    def GitHub__password(self):
        query = "Enter Github password for user %s" % self.config.GitHub.username
        return read(query)

    def Django__static_url(self):
        if self.config.build == "development":
            return "/static/"
        else:
            if self.config.StaticServer.use_ssl:
                return "https://%s/" % self.config.StaticServer.hostname
            else:
                return "http://%s/" % self.config.StaticServer.hostname

    def StaticServer__document_root(self):
        query = "Enter the document root path for the static server"
        default = "/home/%s/klooff-static" % self.env.user

        return read(query, default=default)

    def StaticServer__hostname(self):
        query = "Enter the static server hostname"
        default = "static.klooff.com"

        return read(query, default=default)

    def ApiServer__hostname(self):
        query = "Enter the api server hostname"
        default = "api.klooff.com"

        return read(query, default=default)

    def ApiServer__ipaddress(self):
        query = "Enter the api server IP address for apache hostname configuration"
        default = "*"

        return read(query, default=default)

    def WebServer__hostname(self):
        query = "Enter the web server hostname"
        default = "www.klooff.com"

        return read(query, default=default)

    def ApiServer__use_ssl(self):
        query = "Use SSL for Api?"

        return prompt(query, default=True)

    def StaticServer__use_ssl(self):
        query = "Use SSL for Static?"

        return prompt(query, default=True)

    def StaticServer__ipaddress(self):
        query = "Enter the static server IP address for apache hostname configuration"
        default = "*"

        return read(query, default=default)

    def ApiServer__certificates_dir(self):
        query = "Enter the certificates directory (relative to klooff-control root)"
        default = os.path.join(self.env.local_code_root, "configs", "certs", "stage")

        return read(query, default)

    def StaticServer__certificates_dir(self):
        query = "Enter the Static ssl certificates directory"
        default = os.path.join(self.config.ApiServer.document_root, "configs", "certs", "static")

        return read(query, default)

    def ApiServer__document_root(self):
        query = "Enter the document root path for the API server"
        default = "/home/%s/klooff-server" % self.env.user

        return read(query, default=default)

    def Sentry__dsn(self):
        query = "Enter the DSN where sentry logs are to be sent"
        default = "http://b97f9ac6f98f48928afeed6a0ef91c0b:f8335b789f4945d59e93fa75aace5e85@localhost:9000/2"

        return read(query, default=default)


class MagicConfig(Config):

    def __init__(self, env, config_file=None):
        Config.__init__(
            self, config_file,
            default_manager=MagicDefaultManager(env)
        )

        self.add_section("Database")
        self.add_section("MySQL")
        self.add_section("GitHub")
        self.add_section("Django")
        self.add_section("StaticServer")
        self.add_section("ApiServer")
        self.add_section("WebServer")
        self.add_section("SSH")
        self.add_section("Sentry")
        self.add_section("Celery")
        self.add_section("Redis")
        self.add_section("Session")
        self.add_section("Mongodb")


def set_config(name):
    if name.endswith(".ini"):
        name = name[:-4]

    env.config_file = os.path.join(
        env.local_code_root,
        "configs",
        "%s.ini" % name)
    env.config = MagicConfig(env, env.config_file)
    env.config.autosave(env.config_file)
    #env.config.name = name

    if env.config.SSH.is_set("user"):
        env.user = env.config.SSH.user
    if env.config.SSH.is_set("password"):
        env.password = env.config.SSH.password
        print "Setting user to ", env.user
    if env.config.SSH.is_set("password"):
        env.password = env.config.SSH.password
    if env.config.SSH.is_set("hostname"):
        env.hosts = [env.config.SSH.hostname]
        print "Setting hosts to ", env.hosts
    if env.config.SSH.is_set("identity_file"):
        env.key_filename = os.path.join(
            env.local_code_root,
            "configs",
            "keys",
            env.config.SSH.identity_file)
        print "Setting identity file to ", env.key_filename


@task
def save():
    """Saves the current config state."""

    env.config.save(env.config_file)


@task
def set(name):
    """Loads a given configuration file from the configs directory"""
    set_config(name)
