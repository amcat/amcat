import datetime
import functools
import locale
import re
from contextlib import contextmanager
from typing import Hashable, Iterable, Tuple, Union

from django.utils.translation import get_language_info
from iso8601 import iso8601

DEFAULT_DATEPARSER_SETTINGS = {
    'PREFER_DAY_OF_MONTH': 'first',
    "RETURN_AS_TIMEZONE_AWARE": False
}

RE_ISO = re.compile(r'\d{4}-\d{2}-\d{2}')


def _get_language_aliases(language: 'dateparser.languages.Language') -> Iterable[str]:
    yield language.info['name']
    yield language.shortname
    try:
        yield get_language_info(language.shortname)['name_local']
    except KeyError:
        pass


def read_date(datestr: str, language_pool: Iterable[str] = None) -> Union[None, datetime.datetime]:
    """
    Parses a date, and returns the datetime object. If a language pool is given, only the given
    languages will be considered. Otherwise, all languages known to the dateparser library will be used.

    @param datestr: The string containing the date

    @param language_pool:   An iterable of language identifiers. An identifier is case insensitive,
                            and should be one of:
                             - the ISO 639-1 code
                             - the English name
                             - the local name, as known by Django's translation library
    @return: The resulting datetime
    """
    if language_pool is not None:
        language_pool = tuple(language_pool)

    return _read_date(datestr, language_pool)


__language_aliases = None


def _language_aliases():
    global __language_aliases
    if __language_aliases is None:
        import dateparser
        __language_aliases = dict((alias.lower(), l)
                                 for l in dateparser.languages.default_language_loader.get_languages()
                                 for alias in _get_language_aliases(l))
    return __language_aliases


@functools.lru_cache()
def _read_date(datestr: str, language_pool: Tuple[str, ...]):
    try:
        return iso8601.parse_date(datestr, default_timezone=None)
    except iso8601.ParseError:
        pass

    datestr = datestr.replace("Maerz", "März")  # Needed in LN parser?

    if RE_ISO.match(datestr):
        date_order = 'YMD'  # ISO-like but not quite ISO
    else:
        date_order = 'DMY'  # MDY is studid!

    with _temp_locale(locale.LC_TIME):
        language_pool = None if language_pool is None else tuple(language_pool)
        date = _parse_with_language_pool(datestr, language_pool=language_pool, DATE_ORDER=date_order)
    if date is None:
        raise ValueError("Could not parse datestr: {datestr!r}".format(**locals()))
    return date


@functools.lru_cache()
def _get_dateparser(language_pool: Tuple[str, ...], settings: Hashable = None) -> 'dateparser.DateDataParser':
    import dateparser
    from dateparser.languages.detection import AutoDetectLanguage

    settings = dict(settings or ())

    parser = dateparser.DateDataParser(allow_redetect_language=True, settings=settings)

    if language_pool is None:
        return parser
    aliases = _language_aliases()
    language_codes = set(aliases[lang.lower()]
                         for lang in language_pool
                         if lang in aliases)

    if not language_codes:
        # language pool None or empty, fall back to the default language pool.
        return parser

    lang_detector = AutoDetectLanguage(list(language_codes), allow_redetection=True)
    parser.language_detector = lang_detector

    return parser


def _parse_with_language_pool(datestr: str, language_pool: Tuple[str, ...], **settings_kwargs) -> datetime.datetime:
    import dateparser
    settings = tuple(dict(DEFAULT_DATEPARSER_SETTINGS, **settings_kwargs).items())
    dateparser = _get_dateparser(language_pool, settings)
    date = dateparser.get_date_data(datestr)
    if date:
        return date['date_obj']


@contextmanager
def _temp_locale(category, loc=(None, None)):
    _old = locale.getlocale(category)
    try:
        locale.setlocale(category, loc)
        yield
    finally:
        locale.setlocale(category, _old)
