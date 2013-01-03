from django.utils import unittest

from amcat.models.user import create_user
from amcat.models.user import User, Affiliation
from amcat.models.language import Language
from amcat.models.project import Project
from amcat.models import authorisation

from amcatnavigator.utils import auth
from amcatnavigator.utils import misc

import datetime
import time

class DummyRequest(object):
    pass

class TestCase(unittest.TestCase):
    def create_users(self):
        """
        For every role-object with projectlevel == False, create a user with
        that name and assign it to this object. I.e.:

            self.(super)admin --> user with (super)admin rights
            self.read_write --> user with read/write role

        """
        try:
            nl = Language.objects.get(label='NL')
        except Language.DoesNotExist:
            nl = Language(label='NL'); nl.save()

        try:
            af = Affiliation.objects.get(name='VU')
        except Affiliation.DoesNotExist:
            af = Affiliation(name='VU'); af.save()


        users = [r.label for r in authorisation.Role.objects.filter(projectlevel=False)]
        init_users = bool(User.objects.all())

        for label, user in [(u, u.replace('/', '_')) for u in users]:
            u = User.objects.get(username=user) if init_users else None

            if u is None:
                u = create_user(user, "Test", user, "{}@test.com".format(user),
                    af, nl, authorisation.Role.objects.get(label=label, projectlevel=False)
                )

            setattr(self, user, u)

        adminaff = Affiliation(name="admin"); adminaff.save()

        self.superadmin.affiliation = adminaff
        self.superadmin.is_superuser = True
        self.admin.affiliation = adminaff
        self.superadmin.save(); self.admin.save()

    def setUp(self):
        self.create_users()

    def create_request(self, user):
        req = DummyRequest()
        req.user = user

        return req


class TestCheckPerm(TestCase):
    def setUp(self):
        super(TestCheckPerm, self).setUp()

        self.project = Project()
        self.project.name = 'test'
        self.project.description = 'test_project'
        self.project.owner = self.admin
        self.project.insert_user = self.admin
        self.project.guest_role = authorisation.Role.objects.get(label="reader", projectlevel=True)

        self.project.save()

        authorisation.ProjectRole(project=self.project,
                                  user=self.reader,
                                  role=authorisation.Role.objects.get(label="read/write", projectlevel=True)).save()

    def tearDown(self):
        self.project.delete()

    def test_privilege(self):
        adreq = self.create_request(self.superadmin)
        rereq = self.create_request(self.reader)

        @auth.check_perm("view_users")
        def view(request):
            pass

        self.assertEquals(None, view(adreq))
        self.assertEquals(550, view(rereq).status_code)

    def test_non_string_as_arg(self):
        for typ in [None, [], (), 45, AssertionError]:
            self.assertRaises(AssertionError, lambda: auth.check_perm("view_users", arg=typ))

        self.assertIsNotNone(auth.check_perm("view_users", arg='bla'))

    def test_non_existing_privilege(self):
        req = self.create_request(self.admin)

        # add_articles doesn't exist globally
        @auth.check_perm("add_articles")
        def view(request):
            pass

        self.assertRaises(authorisation.Privilege.DoesNotExist, view, req)

    def test_onproject_and_arg(self):
        non_member_req = self.create_request(self.read_write)
        member_req = self.create_request(self.reader)

        @auth.check_perm("add_articles", True)
        def view1(request, id):
            pass

        @auth.check_perm("add_articles", True, 'pid')
        def view2(request, pid):
            pass

        self.assertEquals(None, view1(member_req, id=self.project.id))
        self.assertEquals(550, view1(non_member_req, id=self.project.id).status_code)
        self.assertRaises(Exception, lambda: view1(member_req, pid=self.project.id))

        self.assertEquals(None, view2(member_req, pid=self.project.id))
        self.assertRaises(Exception, lambda: view2(member_req, id=self.project.id))

    def test_argument_passing(self):
        req = self.create_request(self.superadmin)

        @auth.check_perm("view_users")
        def view1(request, a, b, c=None, d=5):
            return (a, b, c, d)

        a, b, c, d = 1, 2, 3, 4

        self.assertEquals((a,b,c,d), view1(req, a, b, c, d))
        self.assertEquals((a,b,c,d), view1(req, a, b, c=c, d=d))
        self.assertEquals((a,b,c,d), view1(req, a, b=b, c=c, d=d))


class TestCheck(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestCheck, self).__init__(*args, **kwargs)


    ####  ACTUAL TESTS ####
    def test_defaults(self):
        req = self.create_request(self.admin)

        @auth.check(User)
        def view(request, user):
            return user

        @auth.check(User)
        def view2(request, user="bla"):
            return user

        self.assertRaises(KeyError, view, (req, 1))
        self.assertRaises(TypeError, lambda:view(req, id=self.admin))
        self.assertEquals(self.admin, view(req, id=self.admin.id))

        # Check whether the user object gets passed to first keyword
        # argument if non-kw arguments are missing (as doc claims).
        self.assertEquals(self.admin, view2(req, id=self.admin.id))

    def test_nonexistent(self):
        req = self.create_request(self.admin)

        @auth.check(User)
        def view(request, user):
            pass

        self.assertEquals(404, view(req, id=123918).status_code)
        self.assertEquals(None, view(req, id=self.admin.id))


    def test_permission_check(self):
        sadmin_req = self.create_request(self.superadmin)
        coder_req = self.create_request(self.reader)

        @auth.check(User, action='update')
        def view(request, user):
            pass

        # Users can edit own details
        self.assertEquals(None, view(sadmin_req, id=self.superadmin.id))
        self.assertEquals(None, view(coder_req, id=self.reader.id))

        # Admin can edit coders' details
        self.assertEquals(None, view(sadmin_req, id=self.reader.id))

        # Coder can't update admin's details
        self.assertEquals(550, view(coder_req, id=self.superadmin.id).status_code)

    def test_multiple_arguments(self):
        req = self.create_request(self.admin)

        @auth.check(authorisation.ProjectRole, args=['project', 'user', 'role'])
        def view(request, project_role):
            return project_role

        self.assertRaises(KeyError, view, req, id=2)

        pr = Project(name="test")
        pr.description = "bla"
        pr.owner = self.admin
        pr.insert_user = self.admin
        pr.guest_role = authorisation.Role.objects.get(label="reader", projectlevel=False)
        pr.save()

        pj = authorisation.ProjectRole(user=self.admin, project=pr)
        pj.role = authorisation.Role.objects.get(label="reader", projectlevel=True)
        pj.save()

        self.assertEquals(pj, view(req, project=pr.id, user=self.admin.id, role=pj.role.id))

    def test_empty_arguments(self):
        req = self.create_request(self.admin)

        @auth.check(User)
        def view(request, user=None):
            return user

        self.assertEquals(None, view(req))
        self.assertEquals(self.admin, view(req, id=self.admin.id))

    def test_args_map(self):
        req = self.create_request(self.admin)

        @auth.check(User, args='user_id', args_map={'user_id' : 'id'})
        def view(request, user):
            return user

        self.assertEquals(req.user, view(req, user_id=req.user.id))


class TestCache(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestCache, self).__init__(*args, **kwargs)

    def test_cache(self):

        @misc.cache_function(1)
        def get_time():
            return datetime.datetime.now()

        t = get_time()
        self.assertEquals(t, get_time())

        time.sleep(1)

        self.assertNotEquals(t, get_time())



