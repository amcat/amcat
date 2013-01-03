/**************************************************************************
*          (C) Vrije Universiteit, Amsterdam (the Netherlands)            *
*                                                                         *
* This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     *
*                                                                         *
* AmCAT is free software: you can redistribute it and/or modify it under  *
* the terms of the GNU Affero General Public License as published by the  *
* Free Software Foundation, either version 3 of the License, or (at your  *
* option) any later version.                                              *
*                                                                         *
* AmCAT is distributed in the hope that it will be useful, but WITHOUT    *
* ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   *
* FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     *
* License for more details.                                               *
*                                                                         *
* You should have received a copy of the GNU Affero General Public        *
* License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  *
***************************************************************************/


/**************************************************************************
    This script is only used by the "View Ontologies" page.
    Part of the code is copied from the normal annotator page. -Jouke
    
    NOTE: it is currently completely outdated
***************************************************************************/

var annotator = {};
annotator.ontologyItemsDict = {};

annotator.initOntologyData = function(){
    $.ajax({
        "url": "annotator/loadAutoCompletes/" +  annotator.codingjobid + '-' + annotator.setnr,
        "success": function(json) {
            /*$.each(json.autocompletes, function(i, autocompleteObj){
                if(autocompleteObj.isOntology == true){
                    autocompleteObj['items'] = json.ontologies[autocompleteObj['items-key']]; // get items from ontology obj
                    //console.log('loaded from ontologies: ' + autocompleteObj['items'].length);
                    
                }
            });*/
            
            annotator.ontologies = json.ontologies;
            annotator.initOntologyDetails();
        },
        "error": function(jqXHR, textStatus, errorThrown){
            console.log('error loading autocompletes' + textStatus + errorThrown);
            $('#warning').html('<div class="error">Error loading autocomplete data from <a href="' + this.url + '" target="_blank">' + this.url + '</a></div>');
        },
        "dataType": "json"
    });
}
 

annotator.initOntologyDetails = function(){ 
   $.ajax({
        "url": "annotator/loadOntologyItemMetadata/" +  annotator.codingjobid + '-' + annotator.setnr,
        "success": function(json) {

            annotator.ontologyMetadata = {}; // flat dict of all objects in all ontologies
            $.each(json['ontologies-metadata'], function(i, metadataObj){
                $.each(metadataObj, function(j, obj){
                    annotator.ontologyMetadata[j] = obj;
                });
            });
            
            
            $.each(annotator.ontologies, function(j, ontologyItems){
                annotator.convertOntologyJson(ontologyItems);
            });
            
            var html = ['<h3>Available Ontologies:</h3><ul class="ontologies-list">'];
            for(var ontology in annotator.ontologies){
                html.push('<li><a href="javascript:;" onclick="annotator.createHtmlTree(' + ontology + '); return false">Ontology ' + ontology + ' (' + annotator.ontologies[ontology].length + ' items)</a></li>');
                
            }
            html.push('</ul>');
            $('#ontology-list').html(html.join(''));
            $('#ontology-list').removeClass('loading');
        },
        "error": function(jqXHR, textStatus, errorThrown){
            console.log('error loading metadata ontologies ' + textStatus + errorThrown);
            $('#warning').html('<div class="error">Error loading metadata ontologies data from <a href="' + this.url + '" target="_blank">' + this.url + '</a></div>');
        },
        "dataType": "json"
    });
}




annotator.convertOntologyJson = function(ontologyItems){
    /* takes ontology JSON as input and creates dict with all items, including their parents/childs */
    console.log('ont items', ontologyItems.length);
    for(var i=0; i<ontologyItems.length; i++){
        var item = ontologyItems[i];
        var itemMetadata = annotator.ontologyMetadata[item.value];
        var parentid = itemMetadata ? itemMetadata.parentid : null;
        var roles = itemMetadata ? itemMetadata.roles : null;
        //console.log(parent, itemMetadata, item);
        if(! (item.value in annotator.ontologyItemsDict)){
            annotator.ontologyItemsDict[item.value] = {'objid': item.value, 'label':item.label, 'children':[], 'parentid':parentid, 'roles':roles}
        } else {
            annotator.ontologyItemsDict[item.value].label = item.label;
            annotator.ontologyItemsDict[item.value].parentid = parentid;
            annotator.ontologyItemsDict[item.value].roles = item.roles;
            annotator.ontologyItemsDict[item.value].objid = item.value;
        }
        if(parentid){
            if(parentid in annotator.ontologyItemsDict){
                annotator.ontologyItemsDict[parentid].children.push(item.value)
            } else {
                annotator.ontologyItemsDict[parentid] = {'children':[item.value]}
            }
        }
    }
    
    //console.log(annotator.ontologyItemsDict);
}




annotator.createTreeStructure = function(obj){
    if(!obj){
        console.log('no obj');
        return '';
    }
    //console.log('tree', obj);
    var result = '<li>'
    result += '<a objid="' + obj.objid + '" href="javascript:;">' + obj.label + '</a>'
    if(obj.children && obj.children.length > 0){
        var childHtml = '';
        for(var i=0; i<obj.children.length; i++){
            childHtml += annotator.createTreeStructure(annotator.ontologyItemsDict[obj.children[i]])
        }
        result += '<ul>' + childHtml + '</ul>'
    }
    result += '</li>';
    return result
}

annotator.createHtmlTree = function(ontologyid){
    var objhtml = ['<ul>']
    var flathtml = ['<ul>']
    var ontology = annotator.ontologies[ontologyid];
    ontology.sort(function(a, b){return a.label.localeCompare(b.label);});
    console.log('showing ontology', ontologyid);
    $.each(ontology, function(i, obj2){
        var obj = annotator.ontologyItemsDict[obj2.value];
        
        if(!obj){
            console.log('no obj', obj, obj2, obj2.value);
            obj = {};
        }
        if(!obj.parentid || annotator.ontologyItemsDict[obj.parentid].label == undefined){
            if(obj.children.length == 0){
                flathtml.push('<li><a objid="' + obj.objid + '" href="javascript:;">' + obj.label + '</a>');            
                flathtml.push('</li>');
            } else {
                objhtml.push(annotator.createTreeStructure(obj))
            }
        }
        
    });
    if(objhtml.length == 1){
        objhtml.push('<li>No items found</li>');
    }
    if(flathtml.length == 1){
        flathtml.push('<li>No items found</li>');
    }
    objhtml.push('</ul>')
    flathtml.push('</ul>')
    $('#ontology-tree').html(objhtml.join(''));
    $('#ontology-flat').html(flathtml.join('')); 
         
    $('#ontology-tree a, #ontology-flat a').bind('click', function(e){
         console.log('click' + $(this).attr('objid'));
         var objid = $(this).attr('objid');
         var roles = annotator.ontologyItemsDict[objid].roles;

         var content = [];
        if(roles){
            roles.sort(function(a,b){return (a.start || '').localeCompare(b.start)}); // sort on startdate, also if a.start == null
            content.push('<table cellspacing=3><tr><th>Role</th><th>Start</th><th>End</th></tr>');
            for(var i=0; i<roles.length; i++){
                content.push('<tr><td>')
                content.push(roles[i].role);
                content.push('</td><td>')
                if(roles[i].start) content.push(roles[i].start)
                content.push('</td><td>')
                if(roles[i].end) content.push(roles[i].end);
                content.push('</td></tr>');
            }
            content.push('</table>');
        }
         
         $("#ontology-item").html('<h3>' + $(this).text() + '</h3><p>ID: ' + $(this).attr('objid') + '</p>' + content.join(''));
         $("#ontology-item").show();
         return false;
    });
    
    $('#results').show();
}