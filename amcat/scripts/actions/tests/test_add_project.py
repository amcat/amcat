from amcat.scripts.actions.add_project import AddProject
from amcat.tools import amcattest


class TestAddProject(amcattest.AmCATTestCase):
    def test_add(self):
        u = amcattest.create_test_user()
        p = AddProject(owner=u.id, name='test', description='test',insert_user=u.id).run()
        #self.assertEqual(p.insert_user, current_user()) # current_user() doesn't exist anymore
        self.assertEqual(p.owner, u)

    def test_get_form(self):
        u = amcattest.create_test_user()
        #f = AddProject.get_empty_form()
        #self.assertEqual(f.fields['owner'].initial, current_user().id) # current_user() doesn't exist anymore

        f = AddProject.get_empty_form(user=u)
        self.assertEqual(f.fields['owner'].initial, u.id)