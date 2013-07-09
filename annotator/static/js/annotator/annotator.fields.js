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



annotator.fields = {};
annotator.fields.autocompletes = {};
annotator.fields.autocompletes.NUMBER_OF_DROPDOWN_RESULTS = 40; // number of results in autocomplete dropdown list
annotator.fields.autocompletes.EMPTY_CODING_LABEL = '[empty]';
annotator.fields.loadedFromServer = false;
annotator.fields.ontologyItemsDict = {}; // dict containing objids with ontology objects (global, containing all objects from all ontologies), objids should be unique
annotator.fields.ontologyRecentItems = {}; // for each ontology, list of items recently used, for autocomplete


annotator.fields.initFieldData = function(){
    annotator.fields.fields = {}
    annotator.fields.fields['unit'] = {'showAll':true, 'isOntology':false, 'autoOpen':true, 'id':'unit', 'fieldname':'unit'};
    $.ajax({
        "url": annotator.codingjobid + "/fields",
        "success": function(json) {
            var count = 0;
            $.each(json.fields, function(i, fieldObj){
                if(fieldObj.id in annotator.fields.fields){
                    console.debug(fieldObj, 'autcomplete already added');
                    return;
                }
                
                if(! ('items' in fieldObj) && 'items-key' in fieldObj){
                    fieldObj['items'] = json.ontologies[fieldObj['items-key']]; // get items from ontology obj
                    annotator.fields.ontologyRecentItems[fieldObj['items-key']] = [];
                }
                
                // TODO: fix the next two items in the schema, these hacks do not belong here
                if(annotator.unitcodings.isNETcoding == true && fieldObj.fieldname == 'Type'){
                    fieldObj['items'] = $.grep(fieldObj['items'], function(obj, i){ // remove outdated WIL and CON options
                        if(obj.label == 'WIL' || obj.label == 'CON'){
                            return false;
                        }
                        return true;
                    });
                }
                /*if(annotator.unitcodings.isNETcoding == true && fieldObj.fieldname == 'Quality'){ // Add items for Quality
                    fieldObj['noSorting'] = true;
                    fieldObj['items'] = [
                                        {'label':'-1', 'value':'-1'},
                                        {'label':'-0,5', 'value':'-0.5'},
                                        {'label':'0', 'value':'0'},
                                        {'label':'0.5', 'value':'0.5'},
                                        {'label':'1', 'value':'1'}
                                        ];
                }*/
                
                annotator.fields.fields[fieldObj.id] = fieldObj;
                count++;
            });
            console.debug('Loaded ' + count + ' fields');
            
            annotator.fields.ontologies = json.ontologies;
            annotator.fields.loadedFromServer = true;
            
            annotator.fields.convertOntologyJson();

            $( "#loading_fields" ).dialog( "destroy" );
    
        },
        "error": function(jqXHR, textStatus, errorThrown){
            console.debug('error loading fields' + textStatus + errorThrown);
            $('#warning').html('<div class="error">Error loading autocomplete data from <a href="' + this.url + '" target="_blank">' + this.url + '</a></div>');
        },
        "dataType": "json"
    });
}
 



annotator.fields.convertOntologyJson = function(){
    /* takes ontology JSON as input and creates dict with all items, including their parents/childs */
    $.each(annotator.fields.ontologies, function(i, ont){
        $.each(ont, function(j, item){
            annotator.fields.ontologyItemsDict[item.value] = item;
        });
    });
    
    //console.debug(annotator.fields.ontologyItemsDict);
}


annotator.fields.autocompletes.getSearchResults = function(field, term){
    var resultStart = []; // results where term is in the start of label
    var resultRest = []; // results where term can be anywhere in label
    var result = []; // final result
    var items = field.items;
    
    
    var recentLength = 0; // just for debuggin
    
    var maxDropdownLength = annotator.fields.autocompletes.NUMBER_OF_DROPDOWN_RESULTS;
    if(field.id == 'unit'){
        maxDropdownLength = 1000; // make sure all (or at least more) units are visible
    }
    
    // add recent items in front of the result list
    if(term == '' && annotator.fields.ontologyRecentItems[field['items-key']]){
        $.each(annotator.fields.ontologyRecentItems[field['items-key']], function(i, obj){
            result.push(obj);
        });
        recentLength = result.length; 
        result.reverse(); // reverse since last selected items are added last, while they should be displayed first
    }
    
    for(var i=0; i<items.length; i++){
        var index = items[i].label.toLowerCase().indexOf(term)
        if(index > -1){
            if(index == 0){ // match in start of label
                resultStart.push(items[i]);
                if(resultStart.length > maxDropdownLength){
                    break;
                }
            } else {
                if(resultRest.length < maxDropdownLength){
                    resultRest.push(items[i]);
                }
            }
        }
    }

    if(field.noSorting != true){
        resultStart.sort(annotator.sortLabels);
        resultRest.sort(annotator.sortLabels);
    }
    
    for(var i=0; result.length<maxDropdownLength && i<resultStart.length; i++){
        if(!annotator.fields.inArray(resultStart[i], result)){
            result.push(resultStart[i]);
        }
    }
    for(var i=0; result.length<maxDropdownLength && i<resultRest.length; i++){
        if(!annotator.fields.inArray(resultRest[i], result)){
            result.push(resultRest[i]);
        }
    }
    
    if(term == ''){
        // only add emtpy field when searching for empty string
        result.unshift({'value':'', 'label':annotator.fields.autocompletes.EMPTY_CODING_LABEL}) 
    }
    
    return result;
}


annotator.fields.inArray = function(obj, array){
    /* check if obj is in array, using the value property to compare objects */
    var result = false;
    $.each(array, function(i, obj2){
        if(obj.value == obj2.value){
            result = true;
            return false;
        }
    });
    return result;
}


// TODO: implement

annotator.fields.fillOntologyDetailsBox = function(objid, label, inputEl){
    var content = ['<h2>' + label + ' <span class="objid">[' + objid + ']</span></h2>'];
                
    var obj = annotator.fields.ontologyItemsDict[objid];
    
    //console.debug('show', objid, obj);
    
    // currently parent is specific for a function, and children are not implemented (but they still can, for instance in annotator.fields.convertOntologyJson)
    // if(obj.parentid && annotator.fields.ontologyItemsDict[obj.parentid].label){
        // content.push('<h3>Parent</h3>');
        // content.push('<ul>');
        // content.push('<li value="' + obj.parentid + '"><a href="javascript:;" onclick="return false">' + annotator.fields.ontologyItemsDict[obj.parentid].label + '</a></li>');
        // content.push('</ul>');
    // }
    // if(obj.children && obj.children.length > 0){
        // content.push('<h3>Children</h3> <ul>');
        // $.each(obj.children, function(i, id){
            // content.push('<li value="' + id + '"><a href="javascript:;" onclick="return false">' + annotator.fields.ontologyItemsDict[id].label + '</a></li>');
        // });
        // content.push('</ul>');
    // }
    if(obj.functions){
        //obj.functions.sort(function(a,b){return (a.start || '').localeCompare(b.start)}); // sort on startdate, also if a.start == null
        content.push('<table cellspacing="3"><tr><th>Function</th><th>Parent</th><th>Start</th><th>End</th></tr>');
        $.each(obj.functions, function(i, func){
            content.push('<tr><td>')
            content.push(func['function']);
            content.push('</td><td>')
            if(func.parentid in annotator.fields.ontologyItemsDict){
                content.push(annotator.fields.ontologyItemsDict[func.parentid].label); // TODO: make nice safe jQuery html here, this is a security risk
            }
            content.push('</td><td>')
            if(func.from) content.push(func.from)
            content.push('</td><td>')
            if(func.to) content.push(func.to);
            content.push('</td></tr>');
        });
        content.push('</table>');
    }
    
    if(content.length == 1){
        console.debug('no details for', objid);
        $('#autocomplete-details').hide();
        return;
    }
    
    
    $('#autocomplete-details').html( content.join(''));
    $('#autocomplete-details ul').menu();
    $("#autocomplete-details li" ).bind( "click", function(event, ui) {
        console.debug('select');
        inputEl.val( $(this).text() );
        inputEl.next().val( $(this).attr('value') );
        inputEl.focus();
        if(inputEl.parents('#unitcoding-table').length > 0){
            annotator.unitcodings.onchangeSentenceCoding(inputEl);
        }
        if(inputEl.parents('#article-coding').length > 0){
            annotator.articlecodings.onchange(inputEl);
        }
    });
    $('#autocomplete-details').show();
}


annotator.fields.addToRecentItemsList = function(field, value, label){
    var key = field['items-key'];
    annotator.fields.ontologyRecentItems[key] = $.grep(annotator.fields.ontologyRecentItems[key], 
            function(item, i){
                if(item.value == value){
                    return false;
                }
                return true;
    }); // remove duplicates of current item to add
    annotator.fields.ontologyRecentItems[key].push({'value':value, 'label':label})
    console.debug('added to recent', label);
    if(annotator.fields.ontologyRecentItems[key].length > annotator.fields.autocompletes.NUMBER_OF_DROPDOWN_RESULTS){
        annotator.fields.ontologyRecentItems[key].pop(); // remove item to keep list from growing too large
    }
}


annotator.fields.setNETCodings = function(field, value, label){
    if(annotator.unitcodings.isNETcoding == true && field.fieldname == 'Type'){
        if(label == 'IDE'){
            //set object to ideal iff object is not ideal or a child of ideal
            var elName = annotator.unitcodings.findSentenceFieldIdByName('Object');
            console.debug(elName);
            var ontology = annotator.fields.fields[elName.replace(/field_/,'')].items;
            // current value of Object field
            var inputLabel = $('#unitcoding-table .row_selected input[name=' + elName + ']').val(); 
            var idealObj = annotator.fields.findInOntology('ideal', ontology);
            console.assert(idealObj != undefined);
            // check if current value is "ideal" or a child
            var isObjectOrChild = annotator.fields.isObjectOrChild(inputLabel, idealObj, ontology); 
            if(!isObjectOrChild){
                $('#unitcoding-table .row_selected input[name=' + elName + ']').val('ideal');
                console.debug('set object to ideal');
                // TODO flash Object input to indicate a change has been made there
            }
        }
    }
    if(annotator.unitcodings.isNETcoding == true && field.fieldname == 'Subject' && 
                label != annotator.fields.autocompletes.EMPTY_CODING_LABEL){
        // set Type to REA
        var elName = annotator.unitcodings.findSentenceFieldIdByName('Subject');
        var ontology = annotator.fields.fields[elName.replace(/field_/,'')].items;
        var realityObj = annotator.fields.findInOntology('reality', ontology);
        // check if current value is "ideal" or a child
        var isObjectOrChild = annotator.fields.isObjectOrChild(label, realityObj, ontology); 
        if(isObjectOrChild){
            var elNameType = annotator.unitcodings.findSentenceFieldIdByName('Type');
            $('#unitcoding-table .row_selected input[name=' + elNameType + ']').val('REA');
            console.debug('set Type to REA');
            // TODO flash Object input to indicate a change has been made there
        }
    }
}


annotator.fields.autocompletes.setInputValue = function(value, label, inputEl, field){
    /* set the inputEl to a value with label */
    if(label == annotator.fields.autocompletes.EMPTY_CODING_LABEL){
        inputEl.val('');
    } else {
        inputEl.next().val(value); // set value of hidden input
        inputEl.val(label);
        
        if(field.isOntology){
            annotator.fields.addToRecentItemsList(field, value, label);
        }
    }
    if(inputEl.attr('name') == 'unit'){
        annotator.unitcodings.setSentence();
    }
    if(inputEl.parents('#unitcoding-table').length > 0){ // if input is in sentences table
        annotator.unitcodings.onchangeSentenceCoding(inputEl);
        
        annotator.fields.setNETCodings(field, value, label);
    }
    if(inputEl.parents('#article-coding').length > 0){
        annotator.articlecodings.onchange(inputEl);
    }
}


annotator.fields.findInOntology = function(label, ontology){
    /* find label in ontology, return the corresponding item */
    for(var i=0; i<ontology.length; i++){
        var obj = ontology[i];
        if(obj.label == label){
            console.debug('found in ontology', label);
            return obj;
        }
    }
    console.error('not found in ontology', label);
    return null;
}


annotator.fields.isChild = function(obj, objid){
    console.debug('check ischild for', obj, objid);
    if(!obj) return false;
    if(obj.parentid == objid){
        return true;
    }
    if(obj.parentid in annotator.fields.ontologyItemsDict){
        var parent = annotator.fields.ontologyItemsDict[obj.parentid];
        return annotator.fields.isChild(parent, objid);
    }
    return false;
}


annotator.fields.isObjectOrChild = function(inputLabel, obj, ontology){
    // check if inputLabel is the obj or a child of it, in ontology, which should be an array of objects
    if(inputLabel == obj.label){
        console.debug('inputlabel == objlabel');
        return true;
    }
    var inputObj = annotator.fields.findInOntology(inputLabel, ontology);
    if(inputObj && inputObj.value in annotator.fields.ontologyItemsDict){
        var isChild = annotator.fields.isChild(annotator.fields.ontologyItemsDict[inputObj.value], obj.value);
        return isChild;
    }
    return false;
}


annotator.fields.getFieldByInputName = function(inputname){
    var autocompleteid = inputname.replace(/field_/, '');
    var field = annotator.fields.fields[autocompleteid];
    return field;
}


annotator.fields.autocompletes.onFocus = function(){
    if($(this).hasClass('ui-autocomplete-input')){ // already an autocomplete element
        console.log('already an autocomplete'); // should never be called, event should by unbind
        return;
    }
    var inputEl = $(this);
    var field = annotator.fields.getFieldByInputName(inputEl.attr('name'));
    
    if(field == undefined){
        console.debug('field undefined', field.id);
        return;
    }
    
    inputEl.unbind('focus'); // unbind event that calls this function
    
    console.log(field);
    
    if(field.items.length == 0){
        console.log('no field items, ignoring', field.id);
        return;
    }
    
    inputEl.autocomplete({
        source: function(req, resp){
            var term = req.term.toLowerCase();
            var result = annotator.fields.autocompletes.getSearchResults(field, term);
            resp(result);
        },
        selectItem:true,
        isOntology: field.isOntology,
        minLength:0,//annotator.fields.fields[field.id].minLength,
        select: function(event, ui){
            var value = ui.item.value;
            var label = ui.item.label;
            annotator.fields.autocompletes.setInputValue(value, label, inputEl, field);
            return false;
        },
        focus: function( event, ui ) {
            if(field.isOntology){
                // create details box for ontologies
                var objid = ui.item.value;
                var label = ui.item.label;
                
                if(objid in annotator.fields.ontologyItemsDict){
                    annotator.fields.fillOntologyDetailsBox(objid, label, inputEl);
                } else {
                    $('#autocomplete-details').hide();
                }
            }
            return false;
       },
       open: function(event, ui){
            annotator.fields.autocompletes.onOpenAutocomplete($(this));
            //$(".ui-autocomplete").css("z-index", 1500); // needed to avoid dropdown being below fixedheader of sentencetable
       },
       delay:5,
       close: function(){
            $('#autocomplete-details').hide(); // when closing auto complete, also close the details box
       }
    });
    
    //if(autocomplete.autoOpen){
        inputEl.bind('focus', function(){
            if(field.showAll == true){
                inputEl.autocomplete('search', '');
            } else {
                inputEl.autocomplete('search');
            }
        });
    //}
    
    console.debug('added autocomplete for ' + field.id);
    inputEl.focus();
}

annotator.fields.autocompletes.addAutocompletes = function(jqueryEl){
    jqueryEl.find('input:text').each(function(i, input){
        var inputEl = $(input);
        var fieldNumber = inputEl.attr('name').replace(/field_/,'');
        //console.log(fieldNumber, annotator.fields.fields);
        if(fieldNumber in annotator.fields.fields){
            inputEl.focus(annotator.fields.autocompletes.onFocus);
        }
    });
}


annotator.fields.autocompletes.onOpenAutocomplete = function(el){
    var autocomplete = el.data("autocomplete");
    var menu = autocomplete.menu;

    if(autocomplete.options.selectItem) {
        var val = el.val();
        //console.debug('val ' + val);
        var selectedItem = null;
        menu.element.children().each(function(i, child){
            //console.debug(child);
            if($(child).text() == val){
                selectedItem = child;
                return false;
            }
        });
        if(selectedItem == null){
            selectedItem = menu.element.children().first();
        }
        menu.activate($.Event({type: "mouseenter"}), $(selectedItem)); // select first menu item
    }

    if(autocomplete.options.isOntology){ // enable detail box
        var firstItem = menu.element.children().first();
        var detailBox = $('#autocomplete-details');
        detailBox.css('top', firstItem.offset().top);
        if(detailBox.outerWidth() + firstItem.parent().offset().left + firstItem.parent().outerWidth() > $(window).width()){ // if too wide, put on left side
            detailBox.css('left', firstItem.parent().offset().left - detailBox.outerWidth());
        } else {
            detailBox.css('left', firstItem.parent().offset().left + firstItem.parent().outerWidth());
        }
    }
    
    var $window = $(window);
    if($window.height() + $window.scrollTop() - el.offset().top < 300){
        console.debug('scroll', $window.height() + $window.scrollTop() - el.offset().top)//To ' + (-($window.height() - 300)));
        $window.scrollTo(el, {offset:-($window.height() - 305)}); // scroll to sentence in middle of window, so dropdown is fully visible
    }
}




