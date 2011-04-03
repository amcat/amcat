#!/bin/env python
# -*- coding: utf-8 -*-
"""
:mod:`treetaggerwrapper` -- Python wrapper for TreeTagger
=========================================================

:author: Laurent Pointal <laurent.pointal@limsi.fr> <laurent.pointal@laposte.net>
:organization: CNRS - LIMSI
:copyright: CNRS - 2004-2009
:license: GNU-GPL Version 3 or greater
:version: $Id$

For TreeTagger, see `Helmut Schmid TreeTagger site`_.

.. _Helmut Schmid TreeTagger site: http://www.ims.uni-stuttgart.de/projekte/corplex/TreeTagger/DecisionTreeTagger.html

For this module, see:

* `Project page`_
* `Source documentation`_
* `Source repository`_
* `Recent source`_

  You can also retrieve the latest version of this module with the svn command::

      svn export https://subversion.cru.fr/ttpw/trunk/treetaggerwrapper/treetaggerwrapper.py

.. _Project page: http://laurent.pointal.org/python/projets/treetaggerwrapper
.. _Source documentation: http://www.limsi.fr/Individu/pointal/python/treetaggerwrapper-doc/
.. _Source repository: https://sourcesup.cru.fr/scm/?group_id=647
.. _Recent source: http://www.limsi.fr/Individu/pointal/python/treetaggerwrapper.py

This wrapper tool is intended to be used in larger projects, where multiple
chunk of texts must be processed via TreeTagger (else you may simply use the
base TreeTagger installation as an external command).

Installation
------------

Simply put the module in a directory listed in the Python path.


You should set up an environment variable :envvar:`TAGDIR` to reference the
TreeTagger software installation directory (the one with :file:`bin`, :file:`lib`
and :file:`cmd` subdirectories).
If you dont set up such a variable, you can give a `TAGDIR` named argument
when building a :class:`TreeTagger` object to provide this information.

..
    To build the documentation with epydoc:

    epydoc --html -o treetaggerwrapper-doc --docformat epytext --name treetaggerwrapper treetaggerwrapper.py

    (but currently epydoc doesnt understand all Sphinx extensions to reStructuredText)

Usage
-----

Example::

    >>> import treetaggerwrapper
    >>> #1) build a TreeTagger wrapper:
    >>> tagger = treetaggerwrapper.TreeTagger(TAGLANG='en',TAGDIR='~/TreeTagger')
    >>> #2) tag your text.
    >>> tags = tagger.TagText("This is a very short text to tag.")
    >>> #3) use the tags list... (list of string output from TreeTagger).
    >>> print tags
    ['This\tDT\tthis',
     'is\tVBZ\tbe',
     'a\tDT\ta',
     'very\tRB\tvery',
     'short\tJJ\tshort',
     'text\tNN\ttext',
     'to\tTO\tto',
     'tag\tVB\ttag',
     '.\tSENT\t.']
    >>> # Note: in output strings, fields are separated with tab chars.

The module can be used as a command line tool too, for more information
ask for module help::

    python treetaggerwrapper.py --help


Processing
----------

Encoding
~~~~~~~~

By default files and `str` strings are considered to be using latin1 encoding.

- You can specify the encoding when using the script as a command-line tool,
   with the :option:`-e` param (see online help).

- When using the script as an embedded tool into a larger project, you can use
  different parameter types as :meth:`TreeTagger.TagText` `text` parameter.

  - You can use unicode strings, and :meth:`TagText` will return list of unicode
    strings. If you fill'in TagText with a list of strings and dont provide
    and `encoding` parameter, TagText will also return unicode strings
    (same if you set `encoding` to `unicode` or `"unicode"`.
  - You can use `str` strings and specify an alternate `encoding` (and an alternate
    `errors` detection), and TagText() will automatically convert input from this
    encoding and output to this encoding.


This module does two main things
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Manage preprocessing of text in place of external Perl scripts as in
  base TreeTagger installation, thus avoid starting Perl each time a chunk
  of text must be tagged.
- Keep alive a pipe connected to TreeTagger process, and use that pipe
  to send data and retrieve tags, thus avoid starting TreeTagger each
  time.

Use of pipes avoid writing/reading temporary files on disk too.

Other things done by this module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Can number lines into XML tags (to identify lines after TreeTagger
  processing).
- Can mark whitespaces with XML tags.
- By default replace non-talk parts like URLs, emails, IP addresses,
  DNS names (can be turned off). Replaced by a 'replaced-xxx' string
  followed by an XML tag containing the replaced text as attribute.
- Acronyms like U.S.A. are systematically written with a final dot,
  even if it is missing in original file.


In normal mode, all journal outputs are done via Python standard logging system,
standard output is only used if a) you run the module in pipe mode (ie.
results goes to stdout), or b) you set DEBUG or DEBUG_PREPROCESS global
variables and you use the module directly on command line (which make journal
and other traces to be sent to stdout).

For an example of logging use, see :func:`enable_debugging_log` function.

.. note::

    Some non-exported functions and globals can be nice to use in other
    contexts:
    :data:`SGML_tag`, :func:`IsSGMLTag`, :func:`SplitSGML`,
    :data:`Ip_expression`, :data:`DnsHost_expression`,
    :data:`UrlMatch_expression`, :data:`EmailMatch_expression`,
    :func:`PipeWriter`.

Module globals and constants
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. data:: DEBUG(boolean)

    Set to enable debugging code (mainly logs).

.. data:: DEBUG_PREPROCESS(boolean)

    Set to enable preprocessing specific debugging code.

.. data:: RESEXT(string)

    Extension added to result files when using command-line ('ttr').

.. data:: logger(logging.Logger)

    Logger object for this module.

.. data:: STARTOFTEXT(string)

    Tag to identify begin of a text in the data flow.

.. data:: ENDOFTEXT(string)

    Tag to identify end of a text in the data flow.

.. data:: NUMBEROFLINE(string)

    Tag to identify line numbers from source text.

.. data:: TAGSPACE(string)

    Tag to identify spaces in output.

.. data:: TAGTAB(string)

    Tag to identify horizontal tabulations in output.

.. data:: TAGLF(string)

    Tag to identify line feeds in output.

.. data:: TAGCR(string)

    Tag to identify carriage returns in output.

.. data:: TAGVT(string)

    Tag to identify vertical tabulations in output.

.. data:: TAGFF(string)

    Tag to identify form feeds in output.

.. data:: TREETAGGER_ENCODING(string)

    In/out encoding for TreeTagger (latin1).

.. data:: TREETAGGER_INENCERR(str)

    Management of encoding errors fot TT input (replace).

.. data:: TREETAGGER_OUTENCERR(str)

    Management of decoding errors of TT output (replace).

.. data:: USER_ENCODING(str)

    Default input and output for files and strings with no
    encoding specified (latin1).

.. data:: DEFAULT_ENCERRORS(str)

    Error processing for user data encoding/decoding (strict).

.. data:: alonemarks(string)

    String containing chars which must be kept alone (this string
    is used in regular expressions inside square brackets parts).

.. data:: g_langsupport(dict)

    Dictionnary with data for each usable langage.

    g_langsupport[langage] ==> dict of data

.. data:: SGML_name(string)

    Regular expression string for XML names.

.. data:: SGML_tag(string)

    Regular expression string to match XML tags.

.. data:: SGML_tag_re(re.SRE_Pattern)

    Regular expression object to match XML tags.

.. data:: Ip_expression(string)

    Regular expression string to match IP addresses.

.. data:: IpMatch_re(re.SRE_Pattern)

    Regular expression object to match IP addresses.

.. data:: DnsHost_expression(string)

    Regular expression string to match DNS names.

.. data:: DnsHostMatch_re(re.SRE_Pattern)

    Regular expression object to match DNS names.

.. data:: UrlMatch_expression(string)

    Regular expression string to match URLs.

.. data:: UrlMatch_re(re.SRE_Pattern)

    Regular expression object to match URLs.

.. data:: EmailMatch_expression(string)

    Regular expression string to match email addresses.

.. data:: EmailMatch_re(re.SRE_Pattern)

    Regular expression object to match email addresses.

Module exceptions, class and functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
# To allow use of epydoc documentation generation with reStructuredText markup.
__docformat__ = "restructuredtext en"

# Note: I use re.VERBOSE option everywhere to allow spaces and comments into
#       regular expressions (more readable). And (?:...) allow to have
#       semantic groups of things in the expression but no submatch group
#       corresponding in the match object.
#==============================================================================
__all__ = ["TreeTaggerError","TreeTagger"]
import os
import string
import logging
import threading
import glob
import re
import sys
import getopt
import codecs
import subprocess
import shlex
import time

DEBUG = 0
DEBUG_PREPROCESS = 0

# Extension added for result files.
RESEXT = "ttr"

# We dont print for errors/warnings, we use Python logging system.
logger = logging.getLogger("TreeTagger")

# A tag to identify begin/end of a text in the data flow.
# (avoid to restart TreeTagger process each time)
STARTOFTEXT = "<This-is-the-start-of-the-text />"
ENDOFTEXT = "<This-is-the-end-of-the-text />"
# A tag to identify line numbers from source text.
NUMBEROFLINE = "<This-is-line-number num=\"%d\" />"
# And tags to identify location of whitespaces in source text.
TAGSPACE = "<This-is-a-space />"
TAGTAB = "<This-is-a-tab />"
TAGLF = "<This-is-a-lf />"
TAGCR = "<This-is-a-cr />"
TAGVT = "<This-is-a-vt />"
TAGFF = "<This-is-a-ff />"

# Encodings.
# For TreeTagger, this is latin1 (source: Helmut Schmid).
TREETAGGER_ENCODING = "latin1"
# Default management of TT input when encoding.
TREETAGGER_INENCERR = "replace"
# Default management of TT output when decoding.
TREETAGGER_OUTENCERR = "replace"

# Default input and output for files and strings with no ecoding specified.
USER_ENCODING = "latin1"
# Default error processing for encoding - use Python stanndard: strict.
# May be modified with options.
DEFAULT_ENCERRORS = "strict"

#==============================================================================
# Langage support.
# Dictionnary g_langsupport is indexed by langage code (en, fr, de...).
# Each langage code has a dictionnary as value, with corresponding entries:
#   tagparfile: name of the TreeTagger langage file in TreeTagger lib dir.
#   abbrevfile: name of the abbreviations text file in TreeTagger lib dir.
#   pchar: characters which have to be cut off at the beginning of a word.
#          must be usable into a [] regular expression part.
#   fchar: characters which have to be cut off at the end of a word.
#          must be usable into a [] regular expression part.
#   pclictic: character sequences which have to be cut off at the beginning
#               of a word.
#   fclictic: character sequences which have to be cut off at the end of
#               a word.
#   number: representation of numbers in the langage.
#          must be a full regular expression for numbers.
#   dummysentence: a langage valid sentence (sent to ensure that TreeTagger
#          push remaining data). Sentence must only contain words and spaces
#          (even spaces between punctuation as string is simply splitted
#          on whitespaces before being sent to TreeTagger.
#   replurlexp: regular expression subtitution string for URLs.
#   replemailexp: regular expression subtitution string for emails.
#   replipexp: regular expression subtitution string for IP addresses.
#   repldnsexp: regular expression subtitution string for DNS names.
# Chars alonemarks:
#         !?¿;,*¤@°:%|¦/()[]{}<>«»´`¨&~=#±£¥$©®"
# must have spaces around them to make them tokens.
# Notes: they may be in pchar or fchar too, to identify punctuation after
#        a fchar.
#        \202 is a special ,
#        \226 \227 are special -
alonemarks = u"!?¿;,\202*¤@°:%|¦/()[\]{}<>«»´`¨&~=#±\226"+\
             u"\227£¥$©®\""
g_langsupport = {
    "en": { "binfile-win": "tree-tagger.exe",
            "binfile-lin": "tree-tagger",
            "binfile-darwin": "tree-tagger",
            "tagparfile": "english.par",
            "abbrevfile": "english-abbreviations",
            "pchar"     : alonemarks+ur"'",
            "fchar"     : alonemarks+ur"'",
            "pclictic"  : ur"",
            "fclictic"  : ur"'(s|re|ve|d|m|em|ll)|n't",
            "number"    : ur"""(
                            [-+]?[0-9]+(?:\.[0-9]*)?(?:[eE][-+]?[0-9]+)?
                                |
                            [-+]?\.[0-9]+(?:[eE][-+]?[0-9]+)?
                              )""",
            "dummysentence": u"This is a dummy sentence to ensure data push .",
            "replurlexp": ur' replaced-url <repurl text="\1" />',
            "replemailexp": ur' replaced-email <repemail text="\1" />',
            "replipexp" : ur' replaced-ip <repip text="\1" />',
            "repldnsexp" : ur' replaced-dns <repdns text="\1" />'
          },
    "fr": { "binfile-win": "tree-tagger.exe",
            "binfile-lin": "tree-tagger",
            "binfile-darwin": "tree-tagger",
            "tagparfile": "french-utf8.par",
            "abbrevfile": "french-abbreviations-utf8",
            "pchar"     : alonemarks+ur"'",
            "fchar"     : alonemarks+ur"'",
            "pclictic"  : ur"[dcjlmnstDCJLNMST]'|[Qq]u'|[Jj]usqu'|[Ll]orsqu'",
            "fclictic"  : ur"'-t-elles|-t-ils|-t-on|-ce|-elles|-ils|-je|-la|"+\
                          ur"-les|-leur|-lui|-mêmes|-m'|-moi|-on|-toi|-tu|-t'|"+\
                          ur"-vous|-en|-y|-ci|-là",
            "number"    : ur"""(
                            [-+]?[0-9]+(?:[.,][0-9]*)?(?:[eE][-+]?[0-9]+)?
                                |
                            [-+]?[.,][0-9]+(?:[eE][-+]?[0-9]+)?
                               )""",
            "dummysentence": u"Cela est une phrase inutile pour assurer la "+\
                          u"transmission des données .",
            "replurlexp": ur' url-remplacée <repurl text="\1" />',
            "replemailexp": ur' email-remplacé <repemail text="\1" />',
            "replipexp" : ur' ip-remplacée <repdip text="\1" />',
            "repldnsexp" : ur' dns-remplacé <repdns text="\1" />'
          },
    "de": { "binfile-win": "tree-tagger.exe",
            "binfile-lin": "tree-tagger",
            "binfile-darwin": "tree-tagger",
            "tagparfile": "german.par",
            "abbrevfile": "german-abbreviations",
            "pchar"     : alonemarks+ur"'",
            "fchar"     : alonemarks+ur"'",
            "pclictic"  : ur"",
            "fclictic"  : ur"'(s|re|ve|d|m|em|ll)|n't",
            "number"    : ur"""(
                            [-+]?[0-9]+(?:\.[0-9]*)?(?:[eE][-+]?[0-9]+)?
                                |
                            [-+]?\.[0-9]+(?:[eE][-+]?[0-9]+)?
                              )""",
            "dummysentence": u"Das ist ein Testsatz um das Stossen der "+\
                            u"Daten sicherzustellen .",
            "replurlexp": ur' replaced-url <repurl text="\1" />',
            "replemailexp": ur' replaced-email <repemail text="\1" />',
            "replipexp" : ur' replaced-ip <repip text="\1" />',
            "repldnsexp" : ur' replaced-dns <repdns text="\1" />'
          },
    "es": { "binfile-win": "tree-tagger.exe",
            "binfile-lin": "tree-tagger",
            "binfile-darwin": "tree-tagger",
            "tagparfile": "spanish.par",
            "abbrevfile": "spanish-abbreviations",
            "pchar"     : alonemarks+ur"'",
            "fchar"     : alonemarks+ur"'",
            "pclictic"  : ur"",
            "fclictic"  : ur"",
            "number"    : ur"""(
                             [-+]?[0-9]+(?:[.,][0-9]*)?(?:[eE][-+]?[0-9]+)?
                                |
                            [-+]?[.,][0-9]+(?:[eE][-+]?[0-9]+)?
                               )""",
             "dummysentence": u"Quiero darle las gracias a usted y explicar un malentendido.",
            "replurlexp": ur' sustituir-url <repurl text="\1" />',
            "replemailexp": ur' sustituir-email <repemail text="\1" />',
            "replipexp" : ur' sustituir-ip <repdip text="\1" />',
            "repldnsexp" : ur' sustituir-dns <repdns text="\1" />'
           },
    }

# We consider following rules to apply whatever be the langage.
# ... is an ellipsis, put spaces around before splitting on spaces
# (make it a token)
ellipfind_re = re.compile(ur"(\.\.\.)",
                          re.IGNORECASE|re.VERBOSE)
ellipfind_subst = ur" ... "
# A regexp to put spaces if missing after alone marks.
punct1find_re = re.compile(ur"(["+alonemarks+"])([^ ])",
                           re.IGNORECASE|re.VERBOSE)
punct1find_subst = ur"\1 \2"
# A regexp to put spaces if missing before alone marks.
punct2find_re = re.compile(ur"([^ ])([["+alonemarks+"])",
                           re.IGNORECASE|re.VERBOSE)
punct2find_subst = ur"\1 \2"
# A regexp to identify acronyms like U.S.A. or U.S.A (written to force
# at least two chars in the acronym, and the final dot optionnal).
acronymexpr_re = re.compile(ur"^[a-zÀ-ÿ]+(\.[a-zÀ-ÿ])+\.?$",
                           re.IGNORECASE|re.VERBOSE)

#==============================================================================
class TreeTaggerError (Exception) :
    """For exceptions generated directly by TreeTagger class code.
    """
    pass


#==============================================================================
def PipeWriter(pipe,text,flushsequence,encoding=TREETAGGER_ENCODING,
                                        errors=TREETAGGER_INENCERR) :
    r"""Write a text to a pipe and manage pre-post data to ensure flushing.

    For internal use.

    If text is composed of str strings, they are written as-is (ie. assume
    ad-hoc encoding is providen by caller). If it is composed of unicode
    strings, then they are converted to the specified encoding.

    :param  pipe: the Popen pipe on what to write the text.
    :type   pipe: Popen object (file-like with write and flush methods)
    :param  text: the text to write.
    :type   text: string or list of strings
    :param  flushsequence: lines of tokens to ensure flush by TreeTagger.
    :type   flushsequence: string (with \n between tokens)
    :param  encoding: encoding of texts written on the pipe.
    :type   encoding: str
    :param  errors: how to manage encoding errors: strict/ignore/replace,
                    default to strict as Python standard.
    :type  errors: str
    """
    try :
        # Warn the user of possible bad usage.
        if not text :
            logger.warning("Requested to tag an empty text.")
            # We continue to unlock the thread waiting for the ENDOFTEXT on
            # TreeTagger output.

        logger.info("Writing starting part to pipe.")
        # Note: STARTOFTEXT is a str - no encoding (basic ASCII).
        pipe.write(STARTOFTEXT+"\n")

        logger.info("Writing data to pipe.")

        if text :
            if isinstance(text,basestring) :
                # Typically if called without pre-processing.
                if isinstance(text,unicode) :
                    text = text.encode(encoding,errors)
                pipe.write(text)
                if text[-1] != '\n' : pipe.write("\n")
            else :
                # Typically when we have done pre-processing.
                for line in text :
                    if isinstance(line,unicode) :
                        line = line.encode(encoding,errors)
                    pipe.write(line)
                    pipe.write("\n")

        logger.info("Writing ending and flushing part to pipe.")
        # Note: ENDOFTEXT is a str - no encoding (basic ASCII).
        if isinstance(flushsequence,unicode) :
            flushsequence = flushsequence.encode(encoding,errors)
        pipe.write(ENDOFTEXT+"\n.\n"+flushsequence+"\n")
        pipe.flush()
        logger.info("Finished writing data to pipe. Pipe flushed.")
    except :
        logger.error("Failure during pipe writing.",exc_info=True)


#==============================================================================
class TreeTagger (object) :
    """Wrap TreeTagger binary to optimize its usage on multiple texts.

    The two main methods you may use are the L{__init__()} initializer,
    and the L{TagText()} method to process your data and get TreeTagger
    output results.

    :ivar   lang: langage supported by this tagger ('en', 'fr', 'de', 'es).
    :type   lang: string
    :ivar   langsupport: dictionnary of langage specific values (ref. to
                        g_langsupport[lang] dictionnary).
    :type   langsupport: dict
    :ivar   tagdir: path to directory of installation of TreeTagger.
                    Set via TAGDIR env. var or construction param.
    :type   tagdir: string
    :ivar   tagbindir: path to binary dir into TreeTagger dir.
    :type   tagbindir: string
    :ivar   tagcmddir: path to commands dir into TreeTagger dir.
    :type   tagcmddir: string
    :ivar   taglibdir: path to libraries dir into TreeTagger dir.
    :type   taglibdir: string
    :ivar   tagbin: path to TreeTagger binary file (used to launch process).
    :type   tagbin: string
    :ivar   tagopt: command line options for TreeTagger.
    :type   tagopt: string
    :ivar   tagparfile: path to TreeTagger library file.
    :type   tagparfile: string
    :ivar   abbrevfile: path to abbreviations file.
    :type   abbrevfile: string
    :ivar   taginencoding: encoding to use for TreeTagger input encoding.
    :type   taginencoding: str
    :ivar   tagoutencoding: encoding to use for TreeTagger output decoding.
    :type   tagoutencoding: str
    :ivar   taginencerr: management of encoding errors for TreeTagger input.
    :type   taginencerr: str
    :ivar   tagoutencerr: management of encoding errors for TreeTagger output.
    :type   tagoutencerr: str
    :ivar   abbterms: dictionnary of abbreviation terms for fast lookup.
                    Filled when reading abbreviations file.
    :type   abbterms: dict  [ form ] ==> term
    :ivar   pchar: characters which have to be cut off at the beginning of
                a word.
                Filled from g_langsupport dict.
    :type   pchar: string
    :ivar   pchar_re: regular expression object to cut-off such chars.
    :type   pchar_re: SRE_Pattern
    :ivar   fchar: characters which have to be cut off at the end of a word.
                Filled from g_langsupport dict.
    :type   fchar: string
    :ivar   fchar_re: regular expression object to cut-off such chars.
    :type   fchar_re: SRE_Pattern
    :ivar   pclictic: character sequences which have to be cut off at the
                    beginning of a word.
                    Filled from g_langsupport dict.
    :type   pclictic: string
    :ivar   pclictic_re: regular expression object to cut-off pclictic
                        sequences.
    :type   pclictic_re: SRE_Pattern
    :ivar   fclictic: character sequences which have to be cut off at the end
                    of a word.
                    Filled from g_langsupport dict.
    :type   fclictic: string
    :ivar   fclictic_re: regular expression object to cut-off fclictic
                        sequences.
    :type   fclictic_re: SRE_Pattern
    :ivar   number: regular expression of number recognition for the langage.
                    Filled from g_langsupport dict.
    :type   number: string
    :ivar   number_re: regular expression object to identify numbers.
    :type   number_re: SRE_Pattern
    :ivar   dummysequence: just a small but complete sentence in the langage.
                        Filled from g_langsupport dict.
    :type   dummysequence: string
    :ivar   replurlexp: regular expression subtitution string for URLs.
    :type   replurlexp: string
    :ivar   replemailexp: regular expression subtitution string for emails.
    :type   replemailexp: string
    :ivar   replipexp: regular expression subtitution string for IP addresses.
    :type   replipexp: string
    :ivar   repldnsexp: regular expression subtitution string for DNS names.
    :type   repldnsexp: string
    :ivar   tagpopen: TreeTagger process control tool.
    :type   tagpopen: Popen
    :ivar   taginput: pipe to write to TreeTagger input. Set whe opening pipe.
    :type   taginput: write stream
    :ivar   tagoutput: pipe to read from TreeTagger input. Set whe opening
                    pipe.
    :type   tagoutput: read stream
    """
    #--------------------------------------------------------------------------
    def __init__ (self,**kargs) :
        """
        Construction of a wrapper for a TreeTagger process.

        You can specify several parameters at construction time.
        These parameters can be set via environment variables too.
        Most of them have default values.

        :keyword TAGLANG: langage code for texts ('en','fr',...)
                          (default to 'en').
        :type   TAGLANG: string
        :keyword  TAGDIR: path to TreeTagger installation directory
                          (optionnal but highly recommended).
        :type   TAGDIR: string
        :keyword  TAGOPT: options for TreeTagger
                          (default to '-token -lemma -sgml -quiet').
        :type   TAGOPT: string
        :keyword  TAGPARFILE: parameter file for TreeTagger.
                              (default available for supported langages).
                              Use value None to force use of default if
                              environment variable define a value you dont wants
                              to use.
        :type   TAGPARFILE: string
        :keyword  TAGABBREV: abbreviation file for preprocessing.
                             (default available for supported langages).
        :type   TAGABBREV: string
        :keyword TAGINENC: encoding to use for TreeTagger input, default
                           to latin1.
        :type TAGINENC:    str
        :keyword TAGOUTENC: encoding to use for TreeTagger output, default
                            to latin1
        :type TAGOUTENC:    str
        :keyword TAGINENCERR: management of encoding errors for TreeTagger
                              input, strict or ignore or replace -
                              default to replace.
        :type TAGINENCERR:    str
        :keyword TAGOUTENCERR: management of encoding errors for TreeTagger
                               output, strict or ignore or replace -
                               default to replace.
        :type TAGOUTENCERR:    str
        """
        # Get data in different place, setup context for preprocessing and
        # processing.
        self.SetLangage(kargs)
        self.SetTagger(kargs)
        self.SetPreprocessor(kargs)
        # Note: TreeTagger process is started later, when really needed.

    #-------------------------------------------------------------------------
    def SetLangage(self,kargs) :
        """Set langage for tagger.

        Internal use.
        """
        #----- Find langage to tag.
        if kargs.has_key("TAGLANG") :
            self.lang = kargs["TAGLANG"]
        elif os.environ.has_key("TAGLANG") :
            self.lang = os.environ["TAGLANG"]
        else :
            self.lang = "en"
        self.lang = self.lang[:2].lower()
        if not g_langsupport.has_key(self.lang) :
            logger.error("Langage %s not supported.",self.lang)
            raise TreeTaggerError,"Unsupported langage code: "+self.lang
        logger.info("lang=%s",self.lang)
        self.langsupport = g_langsupport[self.lang]

    #-------------------------------------------------------------------------
    def SetTagger(self,kargs) :
        """Set tagger paths, files, and options.

        Internal use.
        """
        #----- Find TreeTagger directory.
        if kargs.has_key("TAGDIR") :
            self.tagdir = kargs["TAGDIR"]
        elif os.environ.has_key("TAGDIR") :
            self.tagdir = os.environ["TAGDIR"]
        else :
            logger.error("Cant locate TreeTagger directory via TAGDIR.")
            raise TreeTaggerError,"Cant locate TreeTagger directory via TAGDIR."
        self.tagdir = os.path.abspath(self.tagdir)
        if not os.path.isdir(self.tagdir) :
            logger.error("Bad TreeTagger directory: %s",self.tagdir)
            raise TreeTaggerError,"Bad TreeTagger directory: "+self.tagdir
        logger.info("tagdir=%s",self.tagdir)

        #----- Set subdirectories.
        self.tagbindir = os.path.join(self.tagdir,"bin")
        self.tagcmddir = os.path.join(self.tagdir,"cmd")
        self.taglibdir = os.path.join(self.tagdir,"lib")

        #----- Set binary by platform.
        if sys.platform == "win32" :
            self.tagbin = os.path.join(self.tagbindir,self.langsupport["binfile-win"])
        elif sys.platform == "linux2" :
            self.tagbin =os.path.join(self.tagbindir,self.langsupport["binfile-lin"])
        elif sys.platform == "darwin" :
            self.tagbin =os.path.join(self.tagbindir,self.langsupport ["binfile-darwin"])
        else :
            logger.error("TreeTagger binary name undefined for platform %s",
                                                                sys.platform)
            raise TreeTaggerError,"TreeTagger binary name undefined "+\
                                  "for platform "+sys.platform
        if not os.path.isfile(self.tagbin) :
            logger.error("TreeTagger binary invalid: %s", self.tagbin)
            raise TreeTaggerError,"TreeTagger binary invalid: " + self.tagbin
        logger.info("tagbin=%s",self.tagbin)

        #----- Find options.
        if kargs.has_key("TAGOPT") :
            self.tagopt = kargs["TAGOPT"]
        elif os.environ.has_key("TAGOPT") :
            self.tagopt = os.environ["TAGOPT"]
        else :
            self.tagopt = "-token -lemma -sgml -quiet"
        if self.tagopt.find("-sgml") == -1 :
            self.tagopt = "-sgml "+self.tagopt
            self.removesgml = True
        else :
            self.removesgml = False
        logger.info("tagopt=%s",self.tagopt)

        #----- Find parameter file.
        if kargs.has_key("TAGPARFILE") :
            self.tagparfile = kargs["TAGPARFILE"]
        elif os.environ.has_key("TAGPARFILE") :
            self.tagparfile = os.environ["TAGPARFILE"]
        else :
            self.tagparfile = None
        # Not in previous else to manage None parameter in kargs.
        if self.tagparfile is None :
            self.tagparfile = self.langsupport["tagparfile"]
        # If its directly a visible file, then use it, else try to locate
        # it in TreeTagger library directory.
        maybefile = os.path.abspath(self.tagparfile)
        if os.path.isfile(maybefile) :
            self.tagparfile = maybefile
        else :
            maybefile = os.path.join(self.taglibdir,self.tagparfile)
            if os.path.isfile(maybefile) :
                self.tagparfile = maybefile
            else :
                logger.error("TreeTagger parameter file invalid: %s",
                                                        self.tagparfile)
                raise TreeTaggerError,"TreeTagger parameter file invalid: "+\
                                      self.tagparfile
        logger.info("tagparfile=%s",self.tagparfile)

        #----- Store encoding/decoding parameters.
        if kargs.has_key("TAGINENC") :
            self.taginencoding = kargs["TAGINENC"]
        elif os.environ.has_key("TAGINENC") :
            self.taginencoding = os.environ["TAGINENC"]
        else :
            self.taginencoding = TREETAGGER_ENCODING
        if kargs.has_key("TAGOUTENC") :
            self.tagoutencoding = kargs["TAGOUTENC"]
        elif os.environ.has_key("TAGOUTENC") :
            self.tagoutencoding = os.environ["TAGOUTENC"]
        else :
            self.tagoutencoding = TREETAGGER_ENCODING
        if kargs.has_key("TAGINENCERR") :
            self.taginencerr = kargs["TAGINENCERR"]
        elif os.environ.has_key("TAGINENCERR") :
            self.taginencerr = os.environ["TAGINENCERR"]
        else :
            self.taginencerr = TREETAGGER_INENCERR
        if kargs.has_key("TAGOUTENCERR") :
            self.tagoutencerr = kargs["TAGOUTENCERR"]
        elif os.environ.has_key("TAGOUTENCERR") :
            self.tagoutencerr = os.environ["TAGOUTENCERR"]
        else :
            self.tagoutencerr = TREETAGGER_OUTENCERR

        logger.info("taginencoding=%s",self.taginencoding)
        logger.info("tagoutencoding=%s",self.tagoutencoding)
        logger.info("taginencerr=%s",self.taginencerr)
        logger.info("tagoutencerr=%s",self.tagoutencerr)

        # TreeTagger is started later (when needed).
        self.tagpopen = None
        self.taginput = None
        self.tagoutput = None

    #-------------------------------------------------------------------------
    def SetPreprocessor(self,kargs) :
        """Set preprocessing files, and options.

        Internal use.
        """
        #----- Find abbreviations file.
        if kargs.has_key("TAGABBREV") :
            self.abbrevfile = kargs["TAGABBREV"]
        elif os.environ.has_key("TAGABBREV") :
            self.abbrevfile = os.environ["TAGABBREV"]
        else :
            self.abbrevfile = None
        # Not in previous else to manage None parameter in kargs.
        if self.abbrevfile is None :
            self.abbrevfile = self.langsupport["abbrevfile"]
        # If its directly a visible file, then use it, else try to locate
        # it in TreeTagger library directory.
        maybefile = os.path.abspath(self.abbrevfile)
        if os.path.isfile(maybefile) :
            self.abbrevfile = maybefile
        else :
            maybefile = os.path.join(self.taglibdir,self.abbrevfile)
            if os.path.isfile(maybefile) :
                self.abbrevfile = maybefile
            else :
                logger.error("Abbreviation file invalid: %s",self.abbrevfile)
                raise TreeTaggerError,"Abbreviation file invalid: "+\
                                      self.abbrevfile
        logger.info("abbrevfile=%s",self.abbrevfile)

        #----- Read file containing list of abbrevitations.
        self.abbterms = {}
        try :
            f = open(self.abbrevfile,"rU")
            try :
                for line in f :
                    line = line.strip() # Remove blanks after and before.
                    if not line : continue  # Ignore empty lines
                    if line[0]=='#' : continue  # Ignore comment lines.
                    self.abbterms[line.lower()] = line  # Store as a dict keys.
            finally :
                f.close()
            logger.info("Read %d abbreviations from file: %s",
                                len(self.abbterms),self.abbrevfile)
        except :
            logger.error("Failure to read abbreviations file: %s",\
                                self.abbrevfile,exc_info=True)
            raise

        #----- Prefix chars at begining of string.
        self.pchar = self.langsupport["pchar"]
        if self.pchar :
            self.pchar_re = re.compile("^(["+self.pchar+"])(.*)$",
                                        re.IGNORECASE|re.VERBOSE)
        else :
            self.pchar_re = None

        #----- Suffix chars at end of string.
        self.fchar = self.langsupport["fchar"]
        if self.fchar :
            self.fchar_re = re.compile("^(.*)(["+self.fchar+"])$",
                                        re.IGNORECASE|re.VERBOSE)
            self.fcharandperiod_re = re.compile("(.*)(["+self.fchar+".])\\.$")
        else :
            self.fchar_re = None
            self.fcharandperiod_re = None

        #----- Character sequences to cut-off at begining of words.
        self.pclictic = self.langsupport["pclictic"]
        if self.pclictic :
            self.pclictic_re = re.compile("^("+self.pclictic+")(.*)",
                                            re.IGNORECASE|re.VERBOSE)
        else:
            self.pclictic_re = None

        #----- Character sequences to cut-off at end of words.
        self.fclictic = self.langsupport["fclictic"]
        if self.fclictic :
            self.fclictic_re = re.compile("(.*)("+self.fclictic+")$",
                                            re.IGNORECASE|re.VERBOSE)
        else :
            self.fclictic_re = None

        #----- Numbers recognition.
        self.number = self.langsupport["number"]
        self.number_re = re.compile(self.number,re.IGNORECASE|re.VERBOSE)

        #----- Dummy string to flush
        sentence = self.langsupport["dummysentence"]
        self.dummysequence = "\n".join(sentence.split())

        #----- Replacement string for
        self.replurlexp = self.langsupport["replurlexp"]
        self.replemailexp = self.langsupport["replemailexp"]
        self.replipexp = self.langsupport["replipexp"]
        self.repldnsexp = self.langsupport["repldnsexp"]

    #--------------------------------------------------------------------------
    def StartProcess(self) :
        """Start TreeTagger processing chain.

        Internal use.
        """
        #----- Start the TreeTagger.
        tagcmdlist = [ self.tagbin ]
        tagcmdlist.extend(shlex.split(self.tagopt))
        tagcmdlist.append(self.tagparfile)
        try :
            #self.taginput,self.tagoutput = os.popen2(tagcmd)
            self.tagpopen = subprocess.Popen(
                            tagcmdlist,     # Use a list of params in place of a string.
                            bufsize=0,      # Not buffered to retrieve data asap from TreeTagger
                            executable=self.tagbin, # As we have it, specify it
                            stdin=subprocess.PIPE,  # Get a pipe to write input data to TreeTagger process
                            stdout=subprocess.PIPE, # Get a pipe to read processing results from TreeTagger
                            #stderr=None,     unused
                            #preexec_fn=None, unused
                            #close_fds=False, And cannot be set to true and use pipes simultaneously on windows
                            #shell=False,     We specify full path to treetagger binary, no reason to use shell
                            #cwd=None,        Normally files are specified with full path, so dont set cwd
                            #env=None,        Let inherit from current environment
                            #universal_newlines=False,  Keep no universal newlines, manage myself
                            #startupinfo=None, unused
                            #creationflags=0   unused
                            )
            self.taginput,self.tagoutput = self.tagpopen.stdin,self.tagpopen.stdout
            logger.info("Started TreeTagger from command: %r",tagcmdlist)
        except :
            logger.error("Failure to start TreeTagger with: %r",\
                                tagcmd,exc_info=True)
            raise

    #--------------------------------------------------------------------------
    def __del__ (self) :
        """Wrapper to be deleted.

        Cut links with TreeTagger process.
        """
        if self.taginput :
            self.taginput.close()
            self.taginput = None
        if self.tagoutput :
            self.tagoutput.close()
            self.tagoutput = None
        if self.tagpopen :
            self.tagpopen = None
            # There are terminate() and kill() methods, but only from Python 2.6.

    #--------------------------------------------------------------------------
    def TagText(self,text,numlines=False,tagonly=False,
                prepronly=False,tagblanks=False,notagurl=False,
                notagemail=False,notagip=False,notagdns=False,
                encoding=None,errors=DEFAULT_ENCERRORS) :
        """Tag a text and return corresponding lines.

        This is normally the method you use on this class. Other methods
        are only helpers of this one.

        :param  text: the text to tag.
        :type   text: string   /   [ string ]
        :param  numlines: indicator to keep line numbering information in
                          data flow (done via SGML tags) (default to False).
        :type   numlines: boolean
        :param  tagonly: indicator to only do TreeTagger tagging processing
                         on input (default to False).
        :type   tagonly: boolesn
        :param  prepronly: indicator to only do preprocessing of text without
                           tagging (default to False).
        :type   prepronly: boolean
        :param  tagblanks: indicator to keep blanks characters information in
                           data flow (done via SGML tags) (default to False).
        :type   tagblanks: boolean
        :param  notagurl: indicator to not do URL replacement (default to False).
        :type   notagurl: boolean
        :param  notagemail: indicator to not do email address replacement
                            (default to False).
        :type   notagemail: boolean
        :param  notagip: indicator to not do IP address replacement (default
                         to False).
        :type   notagip: boolean
        :param  notagdns: indicator to not do DNS names replacement (default
                          to False).
        :type   notagdns: boolean
        :param encoding: encoding of input data (default to latin1 for C{str}
                         text and unicode for C{unicode} text), usable values
                         are standard encodings + C{"unicode"} and C{unicode}
                         type.
                         Mandatory if text is a C{list} or C{tuple} of
                         strings.
        :type encoding: C{str}
        :param errors: indicator how to manage encoding/decoding errors for
                       your data, can be strict / replace / ignore (default
                       to strict).
        :type errors: C{str}
        :return: List of output lines from the tagger, unicode or str
                 strings.
        :rtype:  [ string ]
        """
        # Check for incompatible options.
        if (tagblanks or numlines) and self.removesgml :
            logger.error("Line numbering/blanks tagging need use of -sgml "+\
                         "option for TreeTagger.")
            raise TreeTaggerError,"Line numbering/blanks tagging need use "+\
                                  "of -sgml option for TreeTagger."

        # Manage encoding.
        use_unicode = isinstance(text,unicode) or (encoding in(unicode,"unicode"))

        if (isinstance(text,list) or isinstance(text,tuple)) and encoding is None :
            raise TreeTaggerError,"Must provide an encoding to TagText when using list/tuple as input."
        if encoding is None : encoding = USER_ENCODING

        if isinstance(text,basestring) : text = [ text ]
        for i,t in enumerate(text) :
            if not isinstance(t,unicode) :
                text[i] = t.decode(encoding,errors)

        # Preprocess text (prepare for TreeTagger).
        if not tagonly :
            logger.debug("Pre-processing text.")
            lines = self.PrepareText(text,tagblanks=tagblanks,numlines=numlines,
                                notagurl=notagurl,notagemail=notagemail,
                                notagip=notagip,notagdns=notagdns)
        else :
            # Katie Bell bug fix (2008-06-01)
            #lines = text[0].split()
            # Adapted to support list of lines.
            # And do split on end of lines, not on spaces (ie if we dont prepare the
            # text, we can consider that it has been prepared elsewhere by caller,
            # and that there is only one token item by line for TreeTagger).
            lines = []
            for l in text :
                lines.extend(l.splitlines())

        if prepronly :
            if not use_unicode :
                lines = [ l.encode(encoding,errors) for l in lines ]
            return lines

        # TreeTagger process is started at first need.
        if self.taginput is None :
            self.StartProcess()

        # Send text to TreeTagger, get result.
        logger.debug("Tagging text.")
        t = threading.Thread(target=PipeWriter,args=(self.taginput,
                                        lines,self.dummysequence,
                                        self.taginencoding,self.taginencerr))
        t.start()
        time.sleep(1) # Leave thread and tagger time to start communicating.

        result = []
        intext = False
        while True :
            line = self.tagoutput.readline()
            if DEBUG : logger.debug("Read from TreeTagger: %r",line)
            if not line :
                # We process too much quickly, leave time for tagger and writer
                # thread to worl.
                time.sleep(0.1)

            line = line.decode(self.tagoutencoding,self.tagoutencerr)
            line = line.strip()
            if line == STARTOFTEXT :
                intext = True
                continue
            if line == ENDOFTEXT :  # The flag we sent to identify texts.
                intext = False
                break
            if intext and line :
                if not (self.removesgml and IsSGMLTag(line)) :
                    result.append(line)

        # Synchronize to avoid possible problems.
        t.join()

        if not use_unicode :
            result = [ l.encode(encoding,errors) for l in result ]

        return result

    #--------------------------------------------------------------------------
    def PrepareText(self,text,tagblanks,numlines,notagurl,\
                notagemail,notagip,notagdns) :
        """Prepare a text for processing by TreeTagger.

        :param  text: the text to split into base elements.
        :type   text: unicode   /   [ unicode ]
        :param  tagblanks: transform blanks chars into SGML tags.
        :type   tagblanks: boolean
        :param  numlines: indicator to pur tag for line numbering.
        :type   numlines: boolean
        :param  notagurl: indicator to not do URL replacement (default to False).
        :type   notagurl: boolean
        :param  notagemail: indicator to not do email address replacement
                            (default to False).
        :type   notagemail: boolean
        :param  notagip: indicator to not do IP address replacement (default
                         to False).
        :type   notagip: boolean
        :param  notagdns: indicator to not do DNS names replacement (default
                          to False).
        :type   notagdns: boolean
        :return: List of lines to process as TreeTagger input (no \\n at end of line).
        :rtype: [ unicode ]
        """
        logger.debug("Preparing text for tagger (tagblanks=%d, "\
                    "numlines=%d).",tagblanks,numlines)

        # If necessary, add line numbering SGML tags (which will
        # be passed out as is by TreeTagger and which could be
        # used to identify lines in the flow of tags).
        if numlines :
            logger.debug("Numbering lines.")
            if isinstance(text,basestring) :
                lines = text.splitlines()
            else :
                lines = text
            newlines = []
            for num,line in enumerate(lines) :
                newlines.append(NUMBEROFLINE%(num+1,))
                newlines.append(line)
            s = " ".join(newlines)
            # Remove temporary storage.
            del lines
            del newlines
            logger.debug("Inserted line numbers as SGML tags between lines.")
        else :
            if not isinstance(text,basestring) :
                s = " ".join(text)
            else :
                s = text

        # First, we split the text between SGML tags and non SGML
        # part tags.
        logger.debug("Identifying SGML tags.")
        parts = SplitSGML(s)
        logger.debug("Splitted between SGML tags and others.")

        newparts = []
        if tagblanks:
            # If requested, replace internal blanks by other SGML tags.
            logger.debug("Replacing blanks by corresponding SGML tags.")
            for part in parts :
                if IsSGMLTag(part) :
                    newparts.append(part)
                else :
                    part = BlankToTag(part)
                    newparts.extend(SplitSGML(part))
        else :
            # Else, replace cr, lf, vt, ff, and tab characters with blanks.
            logger.debug("Replacing blanks by spaces.")
            for part in parts :
                newparts.append(BlankToSpace(part))
        parts = newparts
        logger.debug("Blanks replacement done.")

        if not notagurl :
            logger.debug("Replacing URLs.")
            newparts = []
            for part in parts :
                if IsSGMLTag(part) :
                    newparts.append(part)
                else :
                    part = UrlMatch_re.sub(self.replurlexp,part)
                    newparts.extend(SplitSGML(part))
            parts = newparts
            logger.debug("URLs replacement done.")

        if not notagemail :
            logger.debug("Replacing Emails.")
            newparts = []
            for part in parts :
                if IsSGMLTag(part) :
                    newparts.append(part)
                else :
                    part = EmailMatch_re.sub(self.replemailexp,part)
                    newparts.extend(SplitSGML(part))
            parts = newparts
            logger.debug("Emails replacement done.")

        if not notagip :
            logger.debug("Replacing IP addresses.")
            newparts = []
            for part in parts :
                if IsSGMLTag(part) :
                    newparts.append(part)
                else :
                    part = IpMatch_re.sub(self.replipexp,part)
                    newparts.extend(SplitSGML(part))
            parts = newparts
            logger.debug("IP adresses replacement done.")

        if not notagdns :
            logger.debug("Replacing DNS names.")
            newparts = []
            for part in parts :
                if IsSGMLTag(part) :
                    newparts.append(part)
                else :
                    part = DnsHostMatch_re.sub(self.repldnsexp,part)
                    newparts.extend(SplitSGML(part))
            parts = newparts
            logger.debug("DNS names replacement done.")

        # Process part by part, some parts wille be SGML tags, other dont.
        logger.debug("Splittint parts of text.")
        newparts = []
        for part in parts :
            if IsSGMLTag(part) :
                # TreeTagger process by line... a tag cannot be on multiple
                # lines (in case it occured in source text).
                part = part.replace("\n"," ")
                if DEBUG_PREPROCESS : logger.debug("Seen TAG: %r",part)
                newparts.append(part)
            else :
                # This is another part which need more analysis.
                newparts.extend(self.PreparePart(part))
        parts = newparts

        logger.debug("Text preprocessed, parts splitted by line.")

        return parts

    #--------------------------------------------------------------------------
    def PreparePart(self,text) :
        """Prepare a basic text.

        Prepare non-SGML text parts.

        :param  text: unicode text of part to process.
        :type   text: unicode
        :return: List of lines to process as TreeTagger input.
        :rtype: [ unicode ]
        """
        # May occur when recursively calling after splitting on dot, if there
        # are two consecutive dots.
        if not text : return []

        text = u" "+text+" "

        # Put blanks before and after '...' (extract ellipsis).
        text = ellipfind_re.sub(ellipfind_subst,text)

        # Put space between punctuation ;!?:, and following text if space missing.
        text = punct1find_re.sub(punct1find_subst,text)

        # Put space between text and punctuation ;!?:, if space missing.
        text = punct2find_re.sub(punct2find_subst,text)


        # Here some script put blanks after dots (while processing : and , too).
        # This break recognition of texts like U.S.A later.

        # Cut on whitespace, and find subpart by subpart.
        # We put prefix subparts in the prefix list, and suffix subparts in the
        # suffix list, at the end prefix + part + suffix are added to newparts.
        parts = text.split()
        newparts = []
        for part in parts :
            if DEBUG_PREPROCESS : logger.debug("Processing part: %r",part)
            # For single characters or ellipsis, no more processing.
            if len(part)==1 or part == "..." :
                newparts.append(part)
                continue
            prefix = []
            suffix = []
            # Separate punctuation and parentheses from words.
            while True :
                finished = True         # Exit at end if no match.
                # cut off preceding punctuation
                if self.pchar_re != None :
                    matchobj = self.pchar_re.match(part)
                    if matchobj != None :
                        if DEBUG_PREPROCESS :
                            logger.debug("Splitting preceding punct: %r",matchobj.group(1))
                        prefix.append(matchobj.group(1))    # First pchar.
                        part = matchobj.group(2)            # Rest of text.
                        finished = False
                # cut off trailing punctuation
                if self.fchar_re != None :
                    matchobj = self.fchar_re.match(part)
                    if matchobj != None :
                        if DEBUG_PREPROCESS :
                            logger.debug("Splitting following punct: %r",matchobj.group(2))
                        suffix.insert(0,matchobj.group(2))
                        part = matchobj.group(1)
                        finished = False
                # cut off trailing periods if punctuation precedes
                if self.fcharandperiod_re != None :
                    matchobj = self.fcharandperiod_re.match(part)
                    if matchobj != None :
                        if DEBUG_PREPROCESS :
                            logger.debug("Splitting dot after following punct: .")
                        suffix.insert(0,".")                        # Last dot.
                        part = matchobj.group(1)+matchobj.group(2)  # Other.
                        finished = False
                # Exit while loop if no match in regular expressions.
                if finished : break

            # Process with the dot problem...
            # Look for acronyms of the form U.S.A. or U.S.A
            if acronymexpr_re.match(part) :
                if DEBUG_PREPROCESS : logger.debug("Found acronym: %r",part)
                # Force final dot to have homogeneous acronyms.
                if part[-1] != '.' : part += '.'
                newparts.extend(prefix)
                newparts.append(part)
                newparts.extend(suffix)
                continue

            # identify numbers.
            matchobj = self.number_re.match(part)
            if matchobj!=None :
                # If there is only a dot after the number which is not
                # recognized, then split it and take the number.
                if matchobj.group()==part[:-1] and part[-1]=="." :
                    part = part[:-1]    # Validate next if... process number.
                    suffix.insert(0,".")
                if matchobj.group()==part : # Its a *full* number.
                    if DEBUG_PREPROCESS : logger.debug("Found number: %r",part)
                    newparts.extend(prefix)
                    newparts.append(part)
                    newparts.extend(suffix)
                    continue

            # Remove possible trailing dots.
            while part and part[-1]=='.' :
                if DEBUG_PREPROCESS : logger.debug("Found trailing dot: .")
                suffix.insert(0,".")
                part = part[:-1]

            # handle explicitly listed tokens
            if self.abbterms.has_key(part.lower()) :
                if DEBUG_PREPROCESS : logger.debug("Found explicit token: %r",part)
                newparts.extend(prefix)
                newparts.append(part)
                newparts.extend(suffix)
                continue

            # If still has dot, split around dot, and process subpart by subpart
            # (call this method recursively).
            # 2004-08-30 - LP
            # As now DNS names and so on are pre-processed, there should no
            # longer be things like www.limsi.fr, remaining dots may be parts
            # of names as in J.S.Bach.
            # So commented the code out (keep it here).
            #if "." in part :
            #    if DEBUG_PREPROCESS :
            #        print "Splitting around remaining dots:",part
            #    newparts.extend(prefix)
            #    subparts = part.split(".")
            #    for index,subpart in enumerate(subparts) :
            #        newparts.extend(self.PreparePart(subpart))
            #        if index+1<len(subparts) :
            #            newparts.append(".")
            #    newparts.extend(suffix)
            #    continue

            # cut off clictics
            if self.pclictic_re != None :
                retry = True
                while retry :
                    matchobj = self.pclictic_re.match(part)
                    if matchobj != None :
                        if DEBUG_PREPROCESS :
                            logger.debug("Splitting begin clictic: %r %r",matchobj.group(1),\
                                                             matchobj.group(2))
                        prefix.append(matchobj.group(1))
                        part = matchobj.group(2)
                    else :
                        retry = False

            if self.fclictic_re != None :
                retry = True
                while retry :
                    matchobj = self.fclictic_re.match(part)
                    if matchobj != None :
                        if DEBUG_PREPROCESS :
                            logger.debug("Splitting end clictic: %r %r",matchobj.group(1),\
                                                           matchobj.group(2))
                        suffix.append(matchobj.group(2))
                        part = matchobj.group(1)
                    else :
                        retry = False

            newparts.extend(prefix)
            newparts.append(part)
            newparts.extend(suffix)

        return newparts


#==============================================================================
# XML names syntax:
SGML_name = ur"[_A-Za-zÀ-ÿ][-_\.:A-Za-zÀ-ÿ0-9]*"
# XML tags (as group, with parenthesis !!!).
SGML_tag = r"""
        (
        <!-- .*? -->                # XML/SGML comment
            |                           # -- OR --
        <[!?/]?"""+SGML_name+"""    # Start of tag/directive
            [^>]*                   # +Process all up to the first >
            >                       # +End of tag/directive
        )"""
SGML_tag_re = re.compile(SGML_tag,re.IGNORECASE|re.VERBOSE|re.DOTALL)
def IsSGMLTag(text) :
    """Test if a text is - completly - a SGML tag.

    :param  text: the text to test.
    :type  text: string
    :return: True if its an SGML tag.
    :rtype: boolean
    """
    return SGML_tag_re.match(text)


#==============================================================================
def SplitSGML(text) :
    """Split a text between SGML-tags and non-SGML-tags parts.

    :param  text: the text to split.
    :type  text: string
    :return: List of parts in their apparition order.
    :rtype: list of string.
    """
    # Simply split on XML tags recognized by regular expression.
    return SGML_tag_re.split(text)


#==============================================================================
BlankToTag_tags = [(u' ',TAGSPACE),(u'\t',TAGTAB),(u'\n',TAGLF),
                   (u'\r',TAGCR),(u'\v',TAGVT),(u'\f',TAGFF)]
def BlankToTag(text) :
    """Replace blanks characters by corresponding SGML tags.

    :param  text: the text to transform from blanks.
    :type  text: string
    :return: Text with replacement done.
    :rtype: string.
    """
    for c,r in BlankToTag_tags :
        text = text.replace(c,r)
    return text


#==============================================================================
def maketransU(s1, s2, todel=u""):
    """Build translation table for use with unicode.translate().

    :param s1: string of characters to replace.
    :type s1: unicode
    :param s2: string of replacement characters (same order as in s1).
    :type s2: unicode
    :param todel: string of characters to remove.
    :type todel: unicode
    :return: translation table with character code -> character code.
    :rtype: dict
    """
    # We go unicode internally - ensure callers are ok with that.
    assert (isinstance(s1,unicode))
    assert (isinstance(s2,unicode))
    trans_tab = dict( zip( map(ord, s1), map(ord, s2) ) )
    trans_tab.update( (ord(c),None) for c in todel )
    return trans_tab

#BlankToSpace_table = string.maketrans (u"\r\n\t\v\f",u"     ")
BlankToSpace_table = maketransU (u"\r\n\t\v\f",u"     ")
def BlankToSpace(text) :
    """Replace blanks characters by real spaces.

    May be good to prepare for regular expressions & Co based on whitespaces.

    :param  text: the text to clean from blanks.
    :type  text: string
    :return: List of parts in their apparition order.
    :rtype: [ string ]
    """
    return text.translate(BlankToSpace_table)


#==============================================================================
# Not perfect, but work mostly.
# From http://www.faqs.org/rfcs/rfc1884.html
# Ip_expression = r"""
#     (?:                         # ----- Classic dotted IP V4 address -----
#         (?:[0-9]{1,3}\.){3}[0-9]{1,3}
#     )
#             |
#     (?:                         # ----- IPV6 format. -----
#       (?:[0-9A-F]{1,4}:){1,6}(?::[0-9A-F]{1,4}){1,6}        # :: inside
#                 |
#       (?:[0-9A-F]{1,4}:){1,6}:                              # :: at end
#                 |
#       :(?::[0-9A-F]{1,4}){1,6}                              # :: at begining
#                 |
#       (?:[0-9A-F]{1,4}:){7}[0-9A-F]{1,4}                    # Full IPV6
#                 |
#                 ::                                          # Empty IPV6
#     )
#         (?:(?:\.[0-9]{1,3}){3})?    # Followed by a classic IPV4.
#                                     # (first number matched by previous rule...
#                                     #  which may match hexa number too (bad) )
# """
# 2004-08-30 - LP
# As IP V6 can interfer with :: in copy/past code, and as its (currently)
# not really common, I comment out the IP V6 recognition.
Ip_expression = r"""
    (?:                         # ----- Classic dotted IP V4 address -----
        (?:[0-9]{1,3}\.){3}[0-9]{1,3}
    )
    """
IpMatch_re = re.compile(ur"("+Ip_expression+")",
                re.VERBOSE|re.IGNORECASE)


#==============================================================================
# Yes, I know, should not fix top level domains here... and accept any TLD.
# But this help to avoid mathcing a domain name with just x.y strings.
# If needed, fill a bug with a missing TLD to add.
DnsHost_expression = ur"""
        (?:
            [-a-z0-9]+\.                # Host name
            (?:[-a-z0-9]+\.)*           # Intermediate domains
                                        # And top level domain below

            (?:
            com|edu|gov|int|mil|net|org|            # Common historical TLDs
            biz|info|name|pro|aero|coop|museum|     # Added TLDs
            arts|firm|info|nom|rec|shop|web|        # ICANN tests...
            asia|cat|jobs|mail|mobi|post|tel|
            travel|xxx|
            glue|indy|geek|null|oss|parody|bbs|     # OpenNIC
            localdomain|                            # Default 127.0.0.0
                    # And here the country TLDs
            ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|
            ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|
            ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|
            de|dj|dk|dm|do|dz|
            ec|ee|eg|eh|er|es|et|
            fi|fj|fk|fm|fo|fr|
            ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|
            hk|hm|hn|hr|ht|hu|
            id|ie|il|im|in|io|iq|ir|is|it|
            je|jm|jo|jp|
            ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|
            la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|
            ma|mc|md|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|
            na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|
            om|
            pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|
            qa|
            re|ro|ru|rw|
            sa|sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm|sn|so|sr|st|sv|sy|sz|
            tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|
            ua|ug|uk|um|us|uy|uz|
            va|vc|ve|vg|vi|vn|vu|
            wf|ws|
            ye|yt|yu|
            za|zm|zw
            )
                |
        localhost
        )"""
DnsHostMatch_re = re.compile(ur"("+DnsHost_expression+r")",
        re.VERBOSE|re.IGNORECASE)

#==============================================================================
# See http://www.ietf.org/rfc/rfc1738.txt?number=1738
UrlMatch_expression = ur"""(
                # Scheme part
        (?:ftp|https?|gopher|mailto|news|nntp|telnet|wais|file|prospero):
                # IP Host specification (optionnal)
        (?:// (?:[-a-z0-9_;?&=](?::[-a-z0-9_;?&=]*)?@)?   # User authentication.
             (?:(?:"""+DnsHost_expression+r""")
                        |
                (?:"""+Ip_expression+""")
              )
              (?::[0-9]+)?      # Port specification
        /)?
                # Scheme specific extension.
        (?:[-a-z0-9;/?:@=&\$_.+!*'(~#%,]+)*
        )"""
UrlMatch_re = re.compile(UrlMatch_expression, re.VERBOSE|re.IGNORECASE)


#==============================================================================
EmailMatch_expression = ur"""(
            [-a-z0-9._']+@
            """+DnsHost_expression+r"""
            )"""
EmailMatch_re = re.compile(EmailMatch_expression,re.VERBOSE|re.IGNORECASE)



#==============================================================================
debugging_log_enabled = False
def enable_debugging_log() :
    """Setup logging module output.

    This setup a log file which register logs, and also dump logs to stdout.
    You can just copy/paste and adapt it to make logging write to your own log
    files.
    """
    # If debug is active, we log to a treetaggerwrapper.log file, and to
    # stdout too. If you wants to log for long time process, you may
    # take a look at RotatingFileHandler.
    global logger,debugging_log_enabled

    if debugging_log_enabled : return
    debugging_log_enabled = True

    hdlr = logging.FileHandler('treetaggerwrapper.log')
    hdlr2 = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
                        'T%(thread)d %(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    hdlr2.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.addHandler(hdlr2)
    logger.setLevel(logging.DEBUG)

#==============================================================================
help_string = """treetaggerwrapper.py

Usage:
    python treetaggerwrapper.py [options] input_file

Read data from specified files, process them one by one, sending data to
TreeTagger, and write TreeTagger output to files with ."""+RESEXT+""" extension.

    python treetaggerwrapper.py [options] --pipe < input_stream > output_stream

Read all data from the input stream, then preprocess it, send it to
TreeTagger, and write  TreeTagger output to output stream.

Options:
    -p          preprocess only (no tagger)
    -t          tagger only (no preprocessor)
    -n          number lines of original text as SGML tags
    -b          transform blanks into SGML tags
    -l lang     langage to tag (default to en)
    -d dir      TreeTagger base directory
    -e enc      files encoding to use (default to """+USER_ENCODING+""")

Other options:
    --ttparamfile fic       file to use as TreeTagger parameter file.
    --ttoptions "options"   TreeTagger specific options (cumulated).
    --abbreviations fic     file to use as abbreviations terms.
    --pipe                  use pipe mode on standard input/output (no need of
                            file on command line).
    --encerrors err         management of encoding errors for user data
                            (files...), strict or ignore or replace (default
                            to strict).
    --debug                 enable debugging log file (treetaggerwrapper.log)

Options you should *never* use unless Helmut Schmid modify TreeTagger:
    --ttinencoding enc      encoding to use for TreeTagger input (default
                            to latin1).
    --ttoutencoding enc     encoding to use for TreeTagger output (default
                            to latin1).
    --ttinencerr err        management of encoding errors for TreeTagger
                            input encoding, strict or ignore or replace
                            (default to replace).
    --ttoutencerr err       management of encoding errors for TreeTagger
                            output decoding, strict or ignore or replace
                            (default to replace).

This Python module can be used as a tool for a larger project by creating a
TreeTagger object and using its TagText method.
If you dont wants to have to specify TreeTagger directory each time, you
can setup a TAGDIR environment variable containing TreeTagger installation
directory path.

Note: When numbering lines, you must ensure that SGML/XML tags in your data
file doesn't split around lines (else you will get line numberning tags into
your text tags... with bad result on tags recognition by regular expression).

Written by Laurent Pointal <laurent.pointal@limsi.fr> for CNRS-LIMSI.
Alternate email: <laurent.pointal@laposte.net>
"""
def main(*args) :
    """Test/command line usage code.
    """
    if args and args[0].lower() in ("-h","h","--help","-help","help",
                                    "--aide","-aide","aide","?"):
        print help_string
        sys.exit(0)

    # Set default, then process options.
    numlines=tagonly=prepronly=tagblanks=pipemode=False
    filesencoding = USER_ENCODING
    encerrors = DEFAULT_ENCERRORS
    tagbuildopt = {}
    optlist,args = getopt.getopt(args, 'ptnl:d:be:',["abbreviations=",
                                "ttparamfile=","ttoptions=","pipe",
                                "ttinencoding=","ttoutencoding=",
                                "ttinencerr=","ttoutencerr=",
                                "debug"])
    for opt,val in optlist :
        if opt=="--debug" :
            enable_debugging_log()
        if opt=='-p' :
            prepronly = True
        elif opt=='-t' :
            tagonly = True
        elif opt=='-n' :
            numlines = True
        elif opt=='-l' :
            tagbuildopt["TAGLANG"] = val
        elif opt=='-b' :
            tagblanks = True
        elif opt=='-d' :
            tagbuildopt["TAGDIR"] = val
        elif opt=='-e' :
            filesencoding = val
        elif opt=="--ttparamfile" :
            tagbuildopt["TAGPARFILE"] = val
        elif opt=="--ttoptions" :
            tagbuildopt["TAGOPT"] = tagbuildopt.get("TAGOPT","")+" "+val
        elif opt=="--abbreviations" :
            tagbuildopt["TAGABBREV"] = val
        elif opt=="--pipe" :
            pipemode = True
        elif opt=="--ttinencoding" :
            tagbuildopt["TAGINENC"] = val
        elif opt=="--ttoutencoding" :
            tagbuildopt["TAGOUTENC"] = val
        elif opt=="--ttinencerr" :
            tagbuildopt["TAGINENCERR"] = val
        elif opt=="--ttoutencerr" :
            tagbuildopt["TAGOUTENCERR"] = val

    # Find files to process.
    files = []
    for f in args :
        files.extend(glob.glob(f))

    if pipemode and files :
        enable_debugging_log()
        logger.error("Cannot use pipe mode with files.")
        logger.info("See online help with --help.")
        return -1

    if DEBUG : logger.info("files to process: %r",files)
    logger.info("filesencoding=%s",filesencoding)
    tagger = TreeTagger (**tagbuildopt)

    if pipemode :
        logger.info("Processing with stdin/stdout, reading input.")
        text = sys.stdin.read()
        logger.info("Processing with stdin/stdout, tagging.")
        res = tagger.TagText(text,numlines,tagonly,prepronly,tagblanks)
        logger.info("Processing with stdin/stdout, writing to stdout.")
        sys.stdout.write("\n".join(res))
        logger.info("Processing with stdin/stdout, finished.")
    else :
        for f in files :
            logger.info("Processing with file %s, reading input.",f)
            fread = codecs.open(f,"rU",encoding=filesencoding,errors=encerrors)
            try :
                text = fread.read()
            finally :
                fread.close()
            logger.info("Processing with file %s, tagging.",f)
            # Note: as we provide Unicode, we dont care about encoding in TegText().
            res = tagger.TagText(text,numlines,tagonly,prepronly,tagblanks)
            logger.info("Processing with file %s, writing to %s.%s.",f,f,RESEXT)
            res = u"\n".join(res)
            fwrite = codecs.open(f+"."+RESEXT,"w",encoding=filesencoding,errors=encerrors)
            try :
                fwrite.write(res)
            finally :
                fwrite.close()
            logger.info("Processing with file %s, finished.",f)

    logger.info("treetaggerwrapper.py - process terminate normally.")
    return 0

#==============================================================================
if __name__ == "__main__" :
    if DEBUG : enable_debugging_log()
    sys.exit(main(*(sys.argv[1:])))


