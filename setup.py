import setuptools

from os import path
try:
    from pip.req import parse_requirements
except ImportError:
    # We should probably move away from this!
    from pip._internal.req import parse_requirements

try:
    from pip.download import PipSession
except ImportError:
    from pip._internal.download import PipSession
        

here = path.abspath(path.join(path.dirname(path.abspath(__file__))))


requirements_txt = path.join(here, "requirements.txt")
requirements = parse_requirements(requirements_txt, session=PipSession())
requirements = [str(ir.req) for ir in requirements]

# Ugly hack to get the version prior to installation, without having the amcat
# package depend on setup.py.
version = open(path.join(here, "amcat", "_version.py"), mode="r", encoding="ascii")
version = next(filter(lambda s: s.startswith("__version__"), version.readlines()))
version = version.split("=")[-1].strip().strip("'").strip('"')

# Package anything you can find, except for tests
packages = setuptools.find_packages(here, exclude=["*.tests"])

description = """
System for document management and analysis. The purpose of AmCAT is to
make it easier to conduct manual or automatic analyses of texts for (social)
scientific purposes. AmCAT can improve the use and standard of content
analysis in the social sciences and stimulate sharing data and analyses.
"""

def main():
    setuptools.setup(
        name="amcat",
        packages=packages,
        url='https://github.com/amcat/amcat',
        license='GNU Affero GPL',
        author='AmCAT Developers',
        author_email='amcat-dev@googlegroups.com',
        description=(" ".join(description.split("\n"))).strip(),
        install_requires=requirements,
        setup_requires = [
            "setuptools_git >= 0.3",
        ],
        version=version,

        # Fetches package data from git repository
        include_package_data=True,
        exclude_package_data = {'': ['tests/*']}
    )

if __name__ == '__main__':
    main()
