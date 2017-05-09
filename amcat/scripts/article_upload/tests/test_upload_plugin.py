import amcat.scripts
from amcat.scripts.article_upload.upload import UploadScript
from amcat.scripts.article_upload.upload_plugins import UploadPlugin, get_upload_plugin, get_upload_plugins, PluginError
from amcat.tools import amcattest


class TestUploadPlugin(amcattest.AmCATTestCase):
    def setUp(self):
        from amcat.scripts.article_upload import upload
        self.pre_plugins = amcat.scripts.article_upload.upload_plugins._registered_plugins.copy()
        amcat.scripts.article_upload.upload_plugins._registered_plugins.clear()

    def tearDown(self):
        from amcat.scripts.article_upload import upload
        amcat.scripts.article_upload.upload_plugins._registered_plugins = self.pre_plugins.copy()

    def test_plugin_constructor(self):
        kwargs = dict(name="PluginName", label="My UploadPlugin", default=True)
        plugin = UploadPlugin(**kwargs)
        for k, v in kwargs.items():
            self.assertEqual(getattr(plugin, k), v)

        with self.assertRaises(TypeError):
            # assert that the UploadPlugin constructor raises a TypeError if accidentally used as decorator before
            # being constructed
            # noinspection PyArgumentList
            @UploadPlugin
            class C(UploadScript):
                pass



    def test_plugin_registration(self):
        @UploadPlugin(name="PluginName", label="My UploadPlugin")
        class MyTestPlugin(UploadScript):
            pass

        plugin = get_upload_plugin("PluginName")

        self.assertTrue(hasattr(MyTestPlugin, "plugin_info"))
        self.assertEqual(plugin, MyTestPlugin.plugin_info)
        self.assertEqual(plugin.name, "PluginName")
        self.assertEqual(plugin.label, "My UploadPlugin")
        self.assertEqual(plugin.script_cls, MyTestPlugin)

    def test_name_autoresolve(self):
        # use cls.__name__ if no name is given
        @UploadPlugin()
        class MyPlugin(UploadScript):
            pass

        plugin1 = MyPlugin
        plugin1_expected_name = plugin1.__name__

        # fall back to {cls.__module__}.{cls.__name__} in case of conflict.
        @UploadPlugin()
        class MyPlugin(UploadScript):
            pass

        plugin2 = MyPlugin
        plugin2_expected_name = "{cls.__module__}.{cls.__name__}".format(cls=plugin2)

        self.assertEqual(plugin1.plugin_info.name, plugin1_expected_name)
        self.assertEqual(plugin2.plugin_info.name, plugin2_expected_name)
        self.assertEqual(plugin1.plugin_info.label, plugin1_expected_name)
        self.assertEqual(plugin2.plugin_info.label, plugin2_expected_name)


    def test_plugin_uniqueness(self):
        with self.assertRaises(PluginError):
            @UploadPlugin(name="NonUnique")
            class DuplicatePlugin(UploadScript):
                pass

            @UploadPlugin(name="NonUnique")
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
