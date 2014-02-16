from distutils.core import setup
from os import path

here = path.abspath(path.join(path.dirname(path.abspath(__file__))))

requirements = filter(str.strip, open(path.join(here, "pip_requirements.txt")).readlines())
requirements = [x for x in requirements if x and not x.startswith("#")]

# Ugly hack to get the version prior to installation, without having the amcat
# package depend on setup.py.
execfile(path.join(here, "amcat/_version.py"))

package = dict(
    name='amcat',
    version=__version__,
    packages=['api', 'api.rest', 'api.rest.resources', 'api.webscripts', 'amcat', 'amcat.nlp', 'amcat.forms',
              'amcat.tests', 'amcat.tools', 'amcat.tools.pysoh', 'amcat.tools.table', 'amcat.models',
              'amcat.models.coding', 'amcat.contrib', 'amcat.scripts', 'amcat.scripts.forms', 'amcat.scripts.tools',
              'amcat.scripts.output', 'amcat.scripts.actions', 'amcat.scripts', 'amcat.scripts.processors',
              'amcat.scripts.maintenance', 'amcat.scripts.searchscripts', 'amcat.scripts.article_upload',
              'amcat.scraping', 'amcat.scraping.scrapers', 'amcat.manage',
              'amcat.management', 'amcat.management.commands', 'accounts',
              'settings', 'annotator', 'annotator.views', 'navigator', 'navigator.utils', 'navigator.views',
              'navigator.templatetags'],
    url='https://github.com/amcat/amcat',
    license='GNU Affero GPL',
    author='AmCAT Developers',
    author_email='amcat-dev@googlegroups.com',
    description=('AmCAT is a system for document management and analysis. The purpose of AmCAT is to make it easier '
                 'to conduct manual or automatic analyses of texts for (social) scientific purposes. AmCAT can '
                 'improve the use and standard of content analysis in the social sciences and stimulate sharing data '
                 'and analyses.'),
    install_requires=requirements
)

if __name__ == '__main__':
    from distutils.core import setup
    setup(**package)
