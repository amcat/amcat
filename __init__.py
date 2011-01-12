"""AmCAT python libraries

Main organisation:
 - L{amcat.tools} contains a number of auxilliary modules, especially the L{toolkit<amcat.tools.toolkit>}
 - L{amcat.db} contains the Database Abstraction Layer
 - L{amcat.tools.cachable} contains L{Cachable<amcat.tools.cachable.Cachable>}, the main class to connect to the database and query, update, and cache values
 - L{amcat.model} contains the model layer, most classes in this package inherit from L{Cachable<amcat.tools.cachable.Cachable>} for database connection
 - L{amcat.query} contains the query engine
 - L{amcat.test} contains unit tests and the runnable superclass in L{amcattest<amcat.test.amcattest>}
"""
