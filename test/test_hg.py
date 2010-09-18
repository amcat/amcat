import hg, unittest

class TestHG(unittest.TestCase):
    def test_getrepo(self):
        for input, output in (
            ("/home/wva", None),
            ("/home/wva/libpy", "/home/wva/libpy"),
            ("/home/wva/libpy/toolkit.py", "/home/wva/libpy"),
            ("/home/wva/libpy/test", "/home/wva/libpy"),
            ("/home/wva/libpy/test/test.py", "/home/wva/libpy"),
            ):
            self.assertEqual(output, hg.getRepo(input))

    def test_getstatus(self):
        for input, output in (
            ("/home/wva/libpy/toolkit.py", "CM"),
            ("/home/wva/libpy/toolkit.pyc", "I"),
            ("/home/wva/libpy/thisfiledoesnotexist.py", [None]),
            ("/home/wva/thisfiledoesnotexist.py", [None]),
            ):
            self.assertTrue(hg.getStatus(input) in output)

    def test_getrepostatus(self):
        repodict = dict(hg.getRepoStatus("/home/wva/libpy"))
        self.assertTrue(repodict['toolkit.py'] in "CM")
    
if __name__ == '__main__':
    unittest.main()
