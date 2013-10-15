Plugins are modular pieces of code which inherit from special classes, indicating
their type. As of now, only "NLP" and "Article Upload" plugins are supported, but
more types might be added in the future.

== Adding plugins ==
You can add modules to this directory and run:

  ./manage.py sync_plugins

to add them to the database. The module will be searched for classes inheriting
from one of the classes (see Types). One module can hold more than one plugin.

You can also add plugins manually by creating a Plugin entry in the database. It
does not need to be (sym)linked in this directory:

 >>> from amcat.models import Plugin, PluginType
 >>> Plugin.objects.create(
        label="Test", class_name="my_module.UploadScript",
        plugin_type=PluginType.objects.get(label="Article Uploading")
     )
 >>>

When an ImportError occurs while running sync_plugins, you'll be asked whether
the plugin can be removed. Make sure your modules are accessible when running
manage.py.

== Types ==
Article upload:    amcat.scripts.article_upload.upload.UploadScript
NLP preprocessing: amcat.nlp.analysisscript.AnalysisScript