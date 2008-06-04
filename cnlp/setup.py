from distutils.core import setup, Extension

module1 = Extension('cnlp',
                    sources = ['stem.c', 'cnlp.c'])

setup (name = 'C NLP',
       version = '1.0',
       description = 'Reimplementation in C of some common NLP-oriented tasks',
       ext_modules = [module1])
