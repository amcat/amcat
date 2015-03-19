from amcat.models import PluginType, Plugin
from amcat.tools import amcattest


class TestPlugin(amcattest.AmCATTestCase):

    def test_get_classes(self):
        pt = PluginType.objects.create(class_name="amcat.models.Article")
        p1 = Plugin.objects.create(class_name="amcat.models.ArticleSet", plugin_type=pt)
        p2 = Plugin.objects.create(class_name="amcat.models.Project", plugin_type=pt)

        from amcat.models import ArticleSet, Project
        self.assertEqual(set(pt.get_classes()), {ArticleSet, Project})