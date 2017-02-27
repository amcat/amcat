import amcat.scripts
from amcat.scripts.article_upload.upload import UploadScript
from amcat.scripts.article_upload.upload_plugin import UploadPlugin, get_upload_plugin, get_upload_plugins, PluginError
from amcat.tools import amcattest


class TestUploadPlugin(amcattest.AmCATTestCase):
    def setUp(self):
        from amcat.scripts.article_upload import upload
        self.pre_plugins = amcat.scripts.article_upload.upload_plugin._registered_plugins.copy()
        amcat.scripts.article_upload.upload_plugin._registered_plugins.clear()

    def tearDown(self):
        from amcat.scripts.article_upload import upload
        amcat.scripts.article_upload.upload_plugin._registered_plugins = self.pre_plugins.copy()

    def test_plugin_registration(self):
        @UploadPlugin(name="PluginName", label="My UploadPlugin")
        class MyTestPlugin(UploadScript):
            pass
        plugin = get_upload_plugin("PluginName")
        self.assertEqual(plugin.name, "PluginName")
        self.assertEqual(plugin.label, "My UploadPlugin")
        self.assertEqual(plugin.script_cls, MyTestPlugin)

    def test_plugin_defaults(self):
        @UploadPlugin()
        class MyTestPlugin(UploadScript):
            pass

        self.assertIn(MyTestPlugin.__name__, get_upload_plugins())
        plugin = get_upload_plugin(MyTestPlugin.__name__)

        # Name and label default to class.__name__
        self.assertEqual(plugin.name, MyTestPlugin.__name__)
        self.assertEqual(plugin.label, MyTestPlugin.__name__)

    def test_plugin_uniqueness(self):
        with self.assertRaises(PluginError):
            @UploadPlugin()
            class DuplicatePlugin(UploadScript):
                pass

            @UploadPlugin()
            class DuplicatePlugin(UploadScript):
                pass

    def test_plugin_names(self):
        @UploadPlugin(name="A")
        class MyTestPlugin(UploadScript):
            pass
        plugin_a = get_upload_plugin('A')
        plugin_cls_a = MyTestPlugin

        @UploadPlugin(name="B")
        class MyTestPlugin(UploadScript):
            pass
        plugin_b = get_upload_plugin('B')
        plugin_cls_b = MyTestPlugin

        self.assertEqual(plugin_a.name, plugin_a.label)
        self.assertEqual(plugin_b.name, plugin_b.label)
        self.assertEqual(plugin_a.script_cls, plugin_cls_a)
        self.assertEqual(plugin_b.script_cls, plugin_cls_b)
