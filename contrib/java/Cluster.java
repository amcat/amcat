/*
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
*/


import biz.aduna.map.cluster.*;
import java.io.*;
import javax.xml.parsers.*;
import java.util.*;

class Cluster {
    public static void main(String[] args) throws Exception {

	if (args.length != 2) {
	    System.err.println("Usage: java Cluster INFILE PNGFILE");
	    System.exit(1);
	}

	String infile = args[0];
	String pngfile = args[1];

	System.err.println("Loading Classification");
	SAXParser p = SAXParserFactory.newInstance().newSAXParser();
	FileInputStream fis = new FileInputStream(infile);
	ClassificationTreeReader r = new ClassificationTreeReader();
	p.parse(fis, r);
	Classification cl = r.getClassificationTree();
	fis.close();

	System.err.println("Creating cluster model");
	ClusterModel m = new DefaultClusterModel(cl.getChildren());

	System.err.println("Creating Cluster Map");
	ClusterMapFactory f = ClusterMapFactory.createFactory();
	ClusterMap map = f.createClusterMap();
	System.err.println("Setting map");
	map.setClusterModel(m);
	System.err.println("Updating");
	map.updateGraph();
	
	System.err.println("Exporting PNG");
	FileOutputStream str = new FileOutputStream(pngfile);
	map.exportPngImage(str);
	str.close();

	System.err.println("Exporting HTML");
	StringWriter wr = new StringWriter();
	Properties props = new Properties();
	props.setProperty("imageFileName", pngfile);
	props.setProperty("fullDocument", "false");
	props.setProperty("title", "Test");
	map.exportImageMap(wr, props);
	System.out.println(wr.toString());

	wr.close();
	
    }
}
