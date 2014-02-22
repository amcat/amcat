from distutils.core import setup
from os import path

here = path.abspath(path.join(path.dirname(path.abspath(__file__))))

requirements = open(path.join(here, "pip_requirements.txt"))
requirements = [x.strip() for x in requirements.readlines()
                if x.strip() and not x.startswith("#")]

# Ugly hack to get the version prior to installation, without having the amcat
# package depend on setup.py.
execfile(path.join(here, "amcat/_version.py"))

package = dict(
    name='amcat',
    version='3.3.001',
    packages=['api', 'api.rest', 'api.rest.resources', 'api.webscripts',
              'amcat', 'amcat.nlp', 'amcat.forms',
              'amcat.tests', 'amcat.contrib',
              'amcat.tools', 'amcat.tools.pysoh', 'amcat.tools.table',
              'amcat.models', 'amcat.models.coding',
              'amcat.scripts', 'amcat.scripts.forms', 'amcat.scripts.tools',
              'amcat.scripts.output', 'amcat.scripts.actions', 'amcat.scripts',
              'amcat.scripts.processors', 'amcat.scripts.maintenance',
              'amcat.scripts.searchscripts', 'amcat.scripts.article_upload',
              'amcat.scraping', 'amcat.scraping.scrapers',
              'amcat.management', 'amcat.management.commands',
              'accounts',
              'settings',
              'annotator', 'annotator.views',
              'navigator', 'navigator.utils', 'navigator.views',
              'navigator.templatetags'],
    url='https://github.com/amcat/amcat',
    license='GNU Affero GPL',
    author='AmCAT Developers',
    author_email='amcat-dev@googlegroups.com',
    description=('System for document management and analysis. '
                 'The purpose of AmCAT is to make it easier to conduct manual '
                 'or automatic analyses of texts for (social) scientific '
                 'purposes. AmCAT can improve the use and standard of content '
                 'analysis in the social sciences and stimulate sharing data '
                 'and analyses.'),
    install_requires=requirements
)

if __name__ == '__main__':
    setup(**package)
