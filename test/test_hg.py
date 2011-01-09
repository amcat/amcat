from amcat.test import amcattest
from amcat.tools import hg

class TestHG(amcattest.AmcatTestCase):
    def test_getrepo(self):
        for input, output in (
            ("/home/wva", None),
            ("/home/wva/lib/amcat", "/home/wva/lib/amcat"),
            ("/home/wva/lib/amcat/tools/toolkit.py", "/home/wva/lib/amcat"),
            ("/home/wva/lib/amcat/test", "/home/wva/lib/amcat"),
            ):
            self.assertEqual(output, hg.getRepo(input))

    def test_getstatus(self):
        for input, output in (
            ("/home/wva/lib/amcat/tools/toolkit.py", "CM"),
            ("/home/wva/lib/amcat/tools/toolkit.pyc", "I"),
            ("/home/wva/lib/amcat/thisfiledoesnotexist.py", [None]),
            ("/home/wva/thisfiledoesnotexist.py", [None]),
            ):
            self.assertTrue(hg.getStatus(input) in output)

    def test_getrepostatus(self):
        repodict = dict(hg.getRepoStatus("/home/wva/lib/amcat"))
        self.assertTrue(repodict['tools/toolkit.py'] in "CM")
    
if __name__ == '__main__':
    amcattest.main()
