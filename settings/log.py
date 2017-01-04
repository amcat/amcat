###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################
from settings import get_amcat_config

amcat_config = get_amcat_config()

try:
    import colorlog
except ImportError:
    use_colorlog = False
else:
    use_colorlog = True

LOG_LEVEL = amcat_config["logs"].get("LEVEL")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': "[%(asctime)s %(levelname)s %(name)s:%(lineno)s] %(message)s",
            'datefmt': "%Y-%m-%d %H:%M:%S"
        },
    },
    'handlers': {
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'color' if use_colorlog else 'standard'
        },
    },
    'loggers': {
        'urllib3': {  # avoid annoying 'starting new connection' messages
                      'handlers': ['console'],
                      'propagate': True,
                      'level': 'WARN',
        },
        'elasticsearch': {  # avoid annoying 'starting new connection' messages
                            'handlers': ['console'],
                            'propagate': True,
                            'level': 'WARN',
        },
        '': {
            'handlers': ["console"],
            'level': LOG_LEVEL,
        },
    }
}

if use_colorlog:
    LOGGING["formatters"]["color"] = {
        '()': 'colorlog.ColoredFormatter',
        'format': "%(log_color)s[%(asctime)s %(levelname)s %(name)s:%(lineno)s] %(message)s",
        'log_colors': {
            'DEBUG': 'bold_black',
            'INFO': 'white',
            'WARNING': 'yellow',
            'ERROR': 'bold_red',
            'CRITICAL': 'bold_red',
        },
    }

if amcat_config["logs"].getboolean("queries"):
    LOGGING['loggers']['django.db'] = {}

if amcat_config["logs"].getboolean("logstash"):
    LOGGING['handlers']['logstash'] =  {
        'level': 'INFO',
        'class': 'logstash.LogstashHandler',
        'host': amcat_config["logs"].get("logstash_host"),
        'port': amcat_config["logs"].get("logstash_port"),
        'version': 1, 
        'message_type': 'logstash',
    }
    LOGGING['loggers']['amcat.usage'] = {
        'handlers': ['logstash'],
        'level': 'INFO',
    }
        
if not amcat_config["base"].getboolean("debug") and amcat_config["logs"].get("file"):
    # Add file log handler
    LOG_FILE = amcat_config["logs"].get("file")
    LOGGING['handlers']['logfile'] = {
        'level': LOG_LEVEL,
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': LOG_FILE,
        'maxBytes': 2 * 1024 * 1024,
        'backupCount': 2,
        'formatter': 'color' if use_colorlog else 'standard',
    }
    LOGGING['loggers']['']['handlers'] += ['logfile']

    # Make sure all exceptions are logged to the logfile
    LOGGING['loggers'].update({
        'django.request': {
            'handlers': ['logfile'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['logfile'],
            'level': 'ERROR',
            'propagate': True,
        }
    })


if amcat_config["logs"].getboolean("console"):
    LOGGING['loggers']['']['handlers'] += ['console']
