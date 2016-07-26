##########################################################################
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
from rpy2.robjects import r
import os

## Set R library path
if not os.path.exists('r_plugins/package_library'):
    os.makedirs('r_plugins/package_library')

r(".libPaths('r_plugins/package_library')") ## set path from which R loads packages and where R stores new packages (install can be called from within R plugins) 

## load functions to get formfields 
r("source('r_plugins/formfield_functions.r')")

## iterate through R plugins
plugins = ['demo_plugin1.r', 'demo_plugin2.r']
for plugin in plugins:
	r('source("r_plugins/%s")' % plugin) ## load the R script
	print(r('formfields')[0]) ## extract the formfield json


