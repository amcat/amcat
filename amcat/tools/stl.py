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

import re, struct
from amcat.tools import toolkit


def safeint(x):
    try:
        return int(x)
    except Exception, e:
        toolkit.warn("Exception on int(%r): %s" % (x, e))

def STLtoText(txt):
    body = ""
    GSI = txt[0:1024]
    GSI = {'CPN': safeint(GSI[0:3]), 'DFC': GSI[3:11], 'DSC': safeint(GSI[11]), 'CCT': safeint(GSI[12:14]), 'LC': safeint(GSI[14:16]), 'OPT': GSI[16:48], 'OET': GSI[48:80], 'TPT': GSI[80:112], 'TET': GSI[112:144], 'TN': GSI[144:176], 'TCD': GSI[176:207], 'SLR': GSI[208:224], 'CD': (safeint(GSI[224:226]), safeint(GSI[226:228]), safeint(GSI[228:230])), 'RD': (safeint(GSI[230:232]), safeint(GSI[232:234]), safeint(GSI[234:236])), 'RN': GSI[236:238], 'TNB': safeint(GSI[238:243]), 'TNS': safeint(GSI[243:248]), 'TNG': safeint(GSI[248:251]), 'MNC': safeint(GSI[251:253]), 'MNR': safeint(GSI[253:255]), 'TCS': bool(safeint(GSI[255])), 'TCP': (safeint(GSI[256:258]), safeint(GSI[258:260]), safeint(GSI[260:262]), safeint(GSI[262:264])), 'TCF': (safeint(GSI[264:266]), safeint(GSI[266:268]), safeint(GSI[268:270]), safeint(GSI[270:272])), 'TND': safeint(GSI[272]), 'DSN': safeint(GSI[273]), 'CO': GSI[274:277], 'PUB': GSI[277:309], 'EN': GSI[309:341], 'ECD': GSI[341:373], 'UDA': GSI[448:1024]}
    for i in range(0, GSI['TNB']):
        tmp = txt[1024+128*i:1152+128*i]
        TTI = {}
        TTI['SGN'] = struct.unpack('B', tmp[0])[0]
        TTI['SN'] = struct.unpack('BB', tmp[1:3])
        TTI['SN'] = TTI['SN'][0]*256+TTI['SN'][1]
        TTI['EBN'] = struct.unpack('B', tmp[3])[0]
        TTI['CS'] = struct.unpack('B', tmp[4])[0]
        TTI['TCI'] = struct.unpack('BBBB', tmp[5:9]) #H,M,S,Frame
        TTI['TCO'] = struct.unpack('BBBB', tmp[9:13]) #H,M,S,Frame
        TTI['VP'] = struct.unpack('B', tmp[13])[0]
        TTI['JC'] = struct.unpack('B', tmp[14])[0]
        TTI['CF'] = bool(struct.unpack('B', tmp[15]))
        TTI['TF'] = tmp[16:128]
        #STL['TTI'].append(TTI)
        tmp = re.sub(r'[\x00-\x1f|\x80-\x9f]+', '', TTI['TF'])
        tmp = re.sub(r'\W{2,}', ' ', tmp)
        if TTI['EBN'] == 255:
            tmp = tmp + '\n'
        elif TTI['EBN'] == 254:
            #This is a comment, show it that way
            tmp = "Comment-subtitle: %s" % tmp
        body = body + tmp
    return body
