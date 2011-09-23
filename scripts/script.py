"""
Interface definition and general functionality for amcat Scripts.

A Script is a generic "pluggable" functional element that can be
called from e.g. the Django site, as a standalone web interface, or as
a command line script.

Three subclasses of Script are also defined:
SearchScript takes no input and returns a Table or ArticleList;
Processor takes a Table or ArticleList as input and has flexible
output; and ArticleImporter takes a string as input and has a
(sequence of) (not yet saved) Articles as output. These subclasses
can be moved to more suitable locations in the future
"""

class Script(object):
    """
    'Abstract' class representing a modular piece of
    functionality. Scripts have three key parameters, specified as class variables:
    - input_type: a class representing the type of input expected by the script, such as
      None, unicode, Table, or ArticleList. The command line equivalent would be 
      a (deserialized) stdin stream
    - options: a Django form of required and optional options. The CLI equivalent
      are the command line options and arguments. Can be None
    - output_type: a class representing the output that the script will produce. 
    """

    input_type = None
    options = None
    output_type = None

    def __init__(self, options_form):
        """Default __init__ validates and stores the options form"""
        self.options_form = options_form
        
    
    def run(self, input=None):
        """Run is invoked with the input, which should be of type input_type,
        and should return a result of type output_type or raise an exception"""
        pass
