from distutils.core import setup
from os import path
from pip.req import parse_requirements
from pip.download import PipSession

here = path.abspath(path.join(path.dirname(path.abspath(__file__))))
requirements = [str(ir.req) for ir in
                parse_requirements(path.join(here, "requirements.txt"), session=PipSession())]

# Ugly hack to get the version prior to installation, without having the amcat
# package depend on setup.py.
execfile(path.join(here, "amcat", "_version.py"))

package = dict(
    name='amcat',
    version=__version__,
    packages=[ #  we could do with less of those
        'navigator.views',
        'navigator',
        'navigator.utils',
        'navigator.templatetags',
        'amcat.tests',
        'amcat.management',
        'amcat.management.commands',
        'amcat.scripts.output',
        'amcat.scripts.tools',
        'amcat.scripts',
        'amcat.scripts.forms',
        'amcat.scripts.actions',
        'amcat.scripts.searchscripts',
        'amcat.scripts.article_upload',
        'amcat.tools',
        'amcat.tools.table',
        'amcat.manage',
        'amcat',
        'amcat.forms',
        'amcat.contrib.plugins',
        'amcat.contrib',
        'amcat.models',
        'amcat.models.coding',
        'accounts',
        'settings',
        'api.rest.viewsets',
        'api.rest.viewsets.coding',
        'api.rest',
        'api.rest.resources',
        'api.webscripts',
        'api',
        'annotator.views',
        'annotator',
        ],
    package_data={"amcat.models": ["*.json"],
                  "amcat.scripts.article_upload": ["test_files/*.txt",
                                                   "test_files/*.xml",
                                                   "test_files/bzk/*",
                                                   "test_files/lexisnexis/*"],
                  "amcat.tools": ["sql/*.sql"],
                  "navigator" : ["static/js/*.js",
                                 "statis/js/jqplot/*.js",
                                 "statis/js/jqplot/plugins/*.js",
                                 "static/css/*.css",
                                 "templates/project/*.html",
                                 "templates/*.html",
                                 "static/fonts/*",
                                 ],
                  "annotator" : ["static/js/annotator/*.js",
                                 "templates/annotator/*.html",
                                 ],
                  "api" : ["templates/api/*.js",
                           "templates/api/*.html",
                           "templates/api/webscripts/*.html",
                           ],
                  "accounts" : ["templates/accounts/*.html"],
                  },
    url='https://github.com/amcat/amcat',
    license='GNU Affero GPL',
    author='AmCAT Developers',
    author_email='amcat-dev@googlegroups.com',
    description=('System for document management and analysis. '
                 'The purpose of AmCAT is to make it easier to conduct '
                 'manual or automatic analyses of texts for (social) '
                 'scientific purposes. AmCAT can improve the use and standard'
                 'of content analysis in the social sciences and stimulate '
                 'sharing data and analyses.'),
    install_requires = requirements,
    )
if __name__ == '__main__':
    setup(**package)
