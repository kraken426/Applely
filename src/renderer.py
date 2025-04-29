import os
from jinja2 import Environment, FileSystemLoader

def render_template(template_path, **kwargs):
    templates_dir, template_file = os.path.split(template_path)
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)
    template = env.get_template(template_file)
    content = template.render(**kwargs)
    if content.startswith("Subject:"):
        parts = content.split('\n', 1)
        subject = parts[0].replace("Subject:", "").strip()
        body = parts[1].strip()
    else:
        subject = f"Quick chat, {kwargs.get('first_name', 'there')}?"
        body = content
    return subject, body
