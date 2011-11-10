from amcat.tools.logging import amcatlogging
amcatlogging.setup()

from amcat.tools.dot import dot2object
from amcat.tools import djangotoolkit
from django_extensions.management.modelviz import generate_dot

for name, models, stoplist in [
    ('Projects & Authorisation', ('ProjectRole', 'Privilege'), ()),
    ('Articles', ['Sentence'], ('Project',)),
    ('Coding Jobs', ['CodingJobSet', 'AnnotationSchemaField'],('Project','User')),
    ('Annotations', ['AnnotationValue'], ('Project', 'User','Article', 'CodingJobSet', 'AnnotationSchemaField')),
    ]:

    print "<h1>Model graph for %s</h1>" % name

    models = djangotoolkit.get_related_models(models, stoplist)
    modelnames = [m.__name__ for m in models]

    dot = generate_dot(['amcat'], include_models=modelnames)
    dot = dot.replace("digraph name {", "digraph name {\ngraph [rankdir=LR];")
    print dot2object(dot)

