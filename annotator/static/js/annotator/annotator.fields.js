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

// CodingRules constants
OPERATORS = {
    OR : "OR", AND : "AND", EQUALS : "EQ",
    NOT_EQUALS : "NEQ", NOT : "NOT",
    GREATER_THAN : "GT", LESSER_THAN : "LT",
    GREATER_THAN_OR_EQUAL_TO : "GTE",
    LESSER_THAN_OR_EQUAL_TO : "LTE"
}

ACTIONS = {
    RED : "display red",
    NOT_CODABLE : "not codable",
    NOT_NULL : "not null"
}


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

    annotator.fields.codingrules = {};
    annotator.fields.codingruleactions = {};

    var url = "/api/v4/codingrule?codingschema__codingjobs_";
    $.getJSON(url + "unit__id=" + annotator.codingjobid, annotator.fields.codingrules_fetched.bind("unit"));
    $.getJSON(url + "article__id=" + annotator.codingjobid, annotator.fields.codingrules_fetched.bind("article"));
    $.getJSON("/api/v4/codingruleaction", annotator.fields.codingruleactions_fetched);

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
                
                annotator.fields.fields[fieldObj.id] = fieldObj;
                count++;
            });
            console.debug('Loaded ' + count + ' fields');
            
            var _hierarchies = {};
            annotator.fields.highlight_labels = json.highlight_labels;
            annotator.fields.ontologies = json.ontologies;
            annotator.fields.ontologies_parents = {};
            annotator.fields.loadedFromServer = true;
            annotator.fields.convertOntologyJson();
            annotator.fields.hierarchies = _hierarchies;

            // Create an mapping: hierarchy[codebook_id][code_id] --> code.
            $.each(annotator.fields.ontologies, function(cid, codebook){
                var codes = {};
                $.each(codebook, function(i, code){
                    codes[code.value] = code;
                });

                _hierarchies[cid] = codes;
            });

            // For each codebook, find the roots
            $.each(_hierarchies, function(cid, codebook){
                annotator.fields.ontologies_parents[cid] = [];
                $.each(codebook, function(code_id, code){
                    if (code.functions[0].parentid === null){
                        code.descendants = [];
                        annotator.fields.ontologies_parents[cid].push(code);
                    }
                });
            });

            // .. and get their descendants
            $.each(_hierarchies, function(cid, codebook){
                $.each(codebook, function(code_id, code){
                    var _code = code, seen = [code.value];
                    if (code.functions[0].parentid !== null){
                        while(_code.functions[0].parentid !== null){
                            _code = _hierarchies[cid][_code.functions[0].parentid];

                            if (seen.indexOf(_code.value) !== -1){
                                // Loop detected, carry on.
                                console.log("Cycle in " + seen);
                                return;
                            }
                            seen.push(_code.value);
                        }

                        _hierarchies[cid][_code.value].descendants.push(code);
                    }
                });
            });

            annotator.fields.setup_wordcount();
            annotator.fields.codingrules_fetched();
        },
        "error": function(jqXHR, textStatus, errorThrown){
            console.debug('error loading fields' + textStatus + errorThrown);
            $('#warning').html('<div class="error">Error loading autocomplete data from <a href="' + this.url + '" target="_blank">' + this.url + '</a></div>');
        },
        "dataType": "json"
    });
}

/*
 * Called when initialsing {article,unit}codings is done. Must be bound
 * (with bind()) to either article or unit.
 */
annotator.fields.add_rules = function(html){
    $.each($("input", html), function(i, input){
        $(input).focus();
        $(input).blur();
    });

    $(window).scrollTop(0);

    $("input", html).keyup(function(event){
        // We need to figure out which rules apply when a user is done
        // editing this field. 
        var input = $(event.currentTarget);

        // Parse id when field is "id_field_n"
        var field_id = input.get(0).id.split("_")[2];
        var rules = annotator.fields.get_field_codingrules()[field_id];

        if (rules===undefined){
            console.log("No codingrules for field " + field_id);
            return;
        }

        // Check each rule
        var apply = [], not_apply = [];
        $.each(rules, function(i, rule_id){
            var rule = annotator.fields.codingrules[rule_id];
            (annotator.fields.rule_applies(rule.parsed_condition)
                ? apply : not_apply).push(rule);
        });

        $.each(not_apply, function(i, rule){
            rule.get_field_input().css("borderColor", "");
            rule.get_field_input().get(0).disabled = false;
            rule.get_field_input().attr("null", true);
            rule.get_field_input().attr("placeholder", "");
        });

        $.each(apply, function(i, rule){
            if(rule.field === null || rule.action === null) return;

            var action = rule.get_action().label;

            if(action === ACTIONS.RED){
                rule.get_field_input().css("borderColor", "red");
            } else if (action === ACTIONS.NOT_CODABLE){
                rule.get_field_input().get(0).disabled = true;
            } else if (action === ACTIONS.NOT_NULL){
                rule.get_field_input().attr("null", false);
                rule.get_field_input().attr("placeholder", "NOT NULL");
            }
        });
    });
}

/*
 * Get current value of input element. This takes in account hidden fields
 * and autocomplete fields.
 *
 * @param input: jQuery element 
 */
annotator.fields.get_value = function(input){
    if (input.hasClass("ui-autocomplete-input")){
        // This is an autocomplete field, so we need to fetch the value
        // from the hidden input field.
        return $(":hidden", input.parent()).val();
    } 

    return input.val();
}


/*
 * Return true if rule applies, false if it is not.
 *
 * @type rule: object
 * @param rule: parsed_condition property of a CodingRule
 */
annotator.fields.rule_applies = function(rule){
    var ra = annotator.fields.rule_applies;
    var truth, input, assert = function(cond){
        if(!cond) throw "AssertionError";
    }

    // Get input element and its value
    var input = $("#id_field_" + rule.values[0].id);
    var input_value = annotator.fields.get_value(input);

    if (rule.type === null){
        // Empty rule. "Waardeloos waar".
        return true;
    }

    // Resolve other types
    if (rule.type === OPERATORS.OR){
        return ra(rule.values[0]) || ra(rule.values[1]);
    } 
    
    if (rule.type === OPERATORS.AND){
        return ra(rule.values[0]) && ra(rule.values[1]);
    }
    
    if (rule.type === OPERATORS.NOT){
        return !ra(rule.value);
    }

    if (rule.type === OPERATORS.LESSER_THAN){
        return input_value < rule.values[1];
    }

    if (rule.type === OPERATORS.GREATER_THAN){
        return input_value > rule.values[1];
    }

    if (rule.type === OPERATORS.GREATER_THAN_OR_EQUAL_TO){
        return input_value >= rule.values[1];
    }

    if (rule.type === OPERATORS.LESSER_THAN_OR_EQUAL_TO){
        return input_value <= rule.values[1];
    }

    // rule.type must equal either EQUALS or NOT_EQUALS. Furthermore
    // rule.values[0] must be a codingschemafield and rule.values[1]
    // a value.
    assert(rule.values[0].type === "codingschemafield");
    assert(typeof(rule.values[1]) !== typeof({}));

    truth = input_value == rule.values[1];
    return (rule.type === OPERATORS.EQUALS) ? truth : !truth;
}

/*
 * Called when codingrules are fetched.
 */
annotator.fields.codingrules_fetched_count = 0;
annotator.fields.codingrules_fetched = function(json){
    annotator.fields.codingrules_fetched_count += 1;

    var get_field_input = function(){
        return $("#id_field_" + this.field);
    }

    var get_action = function(){
        return annotator.fields.codingruleactions[this.action];
    }

    if (json !== undefined){
        var rules = {};
        $.each(json.results, function(i, rule){
            rules[rule.id] = rule;
            rule.get_field_input = get_field_input.bind(rule);
            rule.get_action = get_action.bind(rule);
        });

        $.extend(annotator.fields.codingrules, rules);
    }

    if (annotator.fields.codingrules_fetched_count === 4){
        $( "#loading_fields" ).dialog( "destroy" );
    }
}

annotator.fields.codingruleactions_fetched = function(json){
    $.each(json.results, function(i, action){
        annotator.fields.codingruleactions[action.id] = action;
    });

    annotator.fields.codingrules_fetched();
}

/*
 * Get a field_id --> [rule, rule..] mapping.
 */
annotator.fields.get_field_codingrules = function(){
    if (annotator.fields.field_codingrules !== undefined){
        return annotator.fields.field_codingrules;
    }

    var codingrule_fields = {};
    $.each(annotator.fields.codingrules, function(i, rule){
        var self = this;
        codingrule_fields[rule.id] = [];

        /*
         * Return a list with all nodes in parsed condition tree.
         */
        self.walk = function(node){
            if (node === undefined){
                node = self.parsed_condition;
            }
            var nodes = [node];

            if (node.values !== undefined){
                $.merge(nodes, self.walk(node.values[0]));
                $.merge(nodes, self.walk(node.values[1]));
            } else if (node.value !== undefined){
                $.merge(nodes, self.walk(node.value));
            }

            return nodes;
        }

        $.each(self.walk(), function(i, node){
            if (node.type === "codingschemafield"){
                if (codingrule_fields[rule.id].indexOf(node.id) === -1){
                    codingrule_fields[rule.id].push(node.id);
                }
            }
        });
    });

    // Reverse dictionary
    var field_codingrules = {};
    $.each(codingrule_fields, function(rule_id, fields){
        $.each(fields, function(i, field_id){
            if (field_codingrules[field_id] === undefined){
                field_codingrules[field_id] = [];
            }

            if (field_codingrules[field_id].indexOf(rule_id) === -1){
                // Objects ('hashmaps') can only contain strings as keys, so
                // the rule_id's got converted to strings...
                field_codingrules[field_id].push(parseInt(rule_id));
            }
        });
    });

    return field_codingrules;
}

annotator.fields.setup_wordcount = function(){
    // http://stackoverflow.com/questions/6743912/get-the-pure-text-without-html-element-by-javascript
    var sentence_re = / id="sentence-[0-9]*"/g
    var count = function(){
        var html = "";
        if (typeof window.getSelection != "undefined") {
            var sel = window.getSelection();
            if (sel.rangeCount) {
                var container = document.createElement("div");
                for (var i = 0, len = sel.rangeCount; i < len; ++i) {
                    container.appendChild(sel.getRangeAt(i).cloneContents());
                }
                html = container.innerHTML;
            }
        } else if (typeof document.selection != "undefined") {
            if (document.selection.type == "Text") {
                html = document.selection.createRange().htmlText;
            }
        }
        
        html = $("<div>" + html.replace(sentence_re, '') + "</div>");
        $(".annotator-sentencenr", html).remove();

        var text = "";
        $.each(html, function(i, el){
            text += el.innerHTML.replace("</div><div>", " ");
            text += " ";
        });

        var count = 0;
        $.each(text.split(/ /g), function(i, word){
            // replace functions like strip() in Python
            if (word.replace(/^\s+|\s+$/g, '') !== "") count++;
        });

        $("#wordcount").html(count);
    }

    $("#.article-part .sentences").mouseup(function(){
        window.setTimeout(count, 50);
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


/*
 * Returns a list of codes which the coder can choose from, filtered on a given
 * search string.
 * 
 * @param field: selected field (must be in annotator.fields.fields)
 * @param term: term the user entered. All labels containing it will be shown.
 * @param selected_root: if relevant, the selected root. Only display descendants.
 */
annotator.fields.autocompletes.getSearchResults = function(field, term, selected_root){
    var resultStart = []; // results where term is in the start of label
    var resultRest = []; // results where term can be anywhere in label
    var result = []; // final result
    var items = field.items;
    var fields = annotator.fields;

    if (field.isOntology && field.split_codebook){
        items = [];

        // This is a Codebook and needs to be splitted in root/descendants. 
        if (selected_root === undefined){
            // First box. Only display roots.
            $.each(annotator.fields.ontologies_parents[field["items-key"]], function(code_id, code){
                items.push(code);
            });
        } else {
            // Second box. Display descendants.
            items = selected_root.descendants;
        }
    }

    var recentLength = 0; // just for debuggin 
    
    var maxDropdownLength = annotator.fields.autocompletes.NUMBER_OF_DROPDOWN_RESULTS;
    if(field.id == 'unit'){
        maxDropdownLength = 1000; // make sure all (or at least more) units are visible
    }
    
    // add recent items in front of the result list
    if(term == '' && annotator.fields.ontologyRecentItems[field['items-key']]){
        $.each(annotator.fields.ontologyRecentItems[field['items-key']], function(i, obj){
            if (result.indexOf(obj) !== -1) result.push(obj);
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
    
    if(obj.functions){
        content.push('<table cellspacing="3"><tr><th>Function</th><th>Parent</th><th>Start</th><th>End</th></tr>');
        $.each(obj.functions, function(i, func){
            content.push('<tr><td>')
            content.push(func['function']);
            content.push('</td><td>')
            if(func.parentid in annotator.fields.ontologyItemsDict){
                // TODO: make nice safe jQuery html here, this is a security risk
                content.push(annotator.fields.ontologyItemsDict[func.parentid].label); 
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
        console.log('select');
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
        inputEl.val('').removeAttr("_value");
    } else {
        if(!(field.isOntology && field.split_codebook && inputEl.attr("root") === undefined)){
            inputEl.parent().children(":hidden").val(value); // set value of hidden input
        }
        inputEl.val(label).attr("_value", value);
        
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


/*
 * Called when an element with autocompletion is focused.
 */
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
    
    if(field.items.length == 0){
        console.log('no field items, ignoring', field.id);
        return;
    }
    
    inputEl.autocomplete({
        source: function(req, resp){
            var selected_root = undefined;
            if (this.element.attr("root") !== undefined){
                var root = $("#" + this.element.attr("root"));
                if (root.attr("_value") === undefined){
                    // No root selected! Do not display list.
                    resp([]);
                    return;
                }

                var codebook = annotator.fields.hierarchies[field["items-key"]];
                selected_root = codebook[root.attr("_value")];
            } 

            var term = req.term.toLowerCase();
            var result = annotator.fields.autocompletes.getSearchResults(field, term, selected_root);
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
        var field = annotator.fields.fields[fieldNumber];

        if(fieldNumber in annotator.fields.fields){
            inputEl.focus(annotator.fields.autocompletes.onFocus);

            if (field.isOntology && field.split_codebook){
                var desc = $("<input type='text'>");
                inputEl.parent().append(desc);
                inputEl.attr("placeholder", "Root..");

                desc.attr("skip_saving", true);
                desc.attr("placeholder", "Descendant..").attr("root", inputEl.get(0).id);
                desc.attr("name", inputEl.attr("name"));
                desc.focus(annotator.fields.autocompletes.onFocus);

                if(inputEl.val() !== ''){
                     /* Well.. here comes a bit of a hack. We don't know anything about the
                     * parent and we only know the *label* of the coded value, not the id. As
                     * we still want to display the parent, we need to find a code with the
                     * same label as the given code. However, this label is not guarenteed to be
                     * unique, so we could display the wrong parent.. Should work in 99% of the
                     * cases though. */
                     var found = []; var label = inputEl.val(); var code;
                     $.each(annotator.fields.ontologies_parents[field['items-key']], function(i, root){
                        for(var i=0; i < root.descendants.length; i++){
                            code = root.descendants[i];
                            if(code.label === label && found.indexOf(code) === -1){
                                code.root = root;
                                found.push(code);
                            }
                        }
                     });

                     if (found.length > 1){
                        console.log("We found multiple codes for this label :-(:", found);
                     } else if (found.length == 0){
                        console.log("No code found for label", label, "bug?");
                        return;
                     } 

                     code = found[0];
                     inputEl.val(code.root.label).attr("_value", code.root.value);
                     desc.attr("_value", code.value).val(code.label);
                 }
            }
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




