from jinja2 import Environment, BaseLoader, TemplateNotFound
from fabric.api import env, put
import os

class FileLoader(BaseLoader):

    def __init__(self, path='/'):
        self.path = path

    def get_source(self, environment, template):
        path = os.path.join(self.path, template)

        if not os.path.exists(path):
            raise TemplateNotFound(template)
        mtime = os.path.getmtime(path)
        with file(path) as f:
            source = f.read().decode('utf-8')

        return source, path, lambda: mtime == os.path.getmtime(path)

env.templates = Environment(loader=FileLoader(path=env.templates_dir))

def render(template_filename, context):

    template = env.templates.get_template(template_filename)
    return template.render(context)

def render_to_file(template_filename, output_file, context=None):
    context = context or {}
    context.update({'env': env})

    rendered = render(template_filename, context)

    with file(output_file, "w") as f:
        f.write(rendered)
        f.flush()

    return output_file

def render_to_remote_file(template_filename, output_file, context=None):
    local_tmp = "/tmp/_template"

    render_to_file(template_filename, local_tmp, context)
    put(local_tmp, output_file)

