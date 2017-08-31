from amcat.scripts.actions.add_project import AddProject
from amcat.tools import amcattest


class TestAddProject(amcattest.AmCATTestCase):
    def test_add(self):
        u = amcattest.create_test_user()
        p = AddProject(owner=u.id, name='test', description='test',insert_user=u.id).run()
        #self.assertEqual(p.insert_user, current_user()) # current_user() doesn't exist anymore
        self.assertEqual(p.owner, u)
