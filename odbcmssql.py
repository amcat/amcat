"""
Wrapper around the odbc module to support normal connect()
calls to connect to SQL Server using ODBC.
"""

import mx.ODBC

def connect(host, un, pwd, database=None):
    if database:
        return mx.ODBC.Windows.DriverConnect(r"Driver={SQL Server};Server=%(host)s;Database=%(database)s;uid=%(un)s;pwd={%(pwd)s};"
                                             % locals())
    else:
        return mx.ODBC.Windows.DriverConnect(r"Driver={SQL Server};Server=%(host)s;uid=%(un)s;pwd={%(pwd)s};"
                                             % locals())
