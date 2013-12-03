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
    OR: "OR", AND: "AND", EQUALS: "EQ",
    NOT_EQUALS: "NEQ", NOT: "NOT",
    GREATER_THAN: "GT", LESSER_THAN: "LT",
    GREATER_THAN_OR_EQUAL_TO: "GTE",
    LESSER_THAN_OR_EQUAL_TO: "LTE"
};

ACTIONS = {
    RED: "display red",
    NOT_CODABLE: "not codable",
    NOT_NULL: "not null"
};

SCHEMATYPES = {
    TEXT: 1,
    NUMBER: 2,
    CODEBOOK: 5,
    BOOLEAN: 7,
    QUALITY: 9
};


annotator.fields = {};
annotator.fields.autocompletes = {};
annotator.fields.autocompletes.NUMBER_OF_DROPDOWN_RESULTS = 40; // number of results in autocomplete dropdown list
annotator.fields.autocompletes.EMPTY_CODING_LABEL = '[empty]';
annotator.fields.ontologyRecentItems = {}; // for each ontology, list of items recently used, for autocomplete


annotator.fields.initialise_fields = function () {
    annotator.fields.fields = {};
    annotator.fields.fields['unit'] = {
        'showAll': true, 'isOntology': false, 'autoOpen': true, 'id': 'unit', 'fieldname': 'unit'
    };

    annotator.fields.requests = [
        $.getJSON(annotator.get_api_url()),
        $.getJSON(annotator.get_api_url() + "coding_rules"),
        $.getJSON(annotator.get_api_url() + "codebooks"),
        $.getJSON(annotator.get_api_url() + "codingschemas"),
        $.getJSON(annotator.get_api_url() + "codingschemafields"),
        $.getJSON(API_URL + "coding_rule_actions")
    ];

    $.when.apply(undefined, annotator.fields.requests).then(function (codingjob, rules, codebooks, schemas, schemafields, actions) {
            var self = annotator.fields;

            // Check if all request completed successfully. (If not, an
            // error is already thrown, but we need not continue processing
            // the data.
            if (!all(function (request) {
                return request.statusText === "OK";
            }, annotator.fields.requests)) {
                throw "Not all requests completed successfully.";
            }

            // Extract results from response
            self.rules = annotator.map_ids(rules[0].results);
            self.actions = annotator.map_ids(actions[0].results);
            self.codebooks = annotator.map_ids(codebooks[0].results);
            self.schemas = annotator.map_ids(schemas[0].results);
            self.schemafields = annotator.map_ids(schemafields[0].results);
            self.codingjob = codingjob[0];

            // Resolve foreign keys

            // Convert codebook.codes (array) to mapping code_id -> code
            $.each(self.codebooks, function(codebook_id, codebook){
                codebook.codes = annotator.map_ids(codebook.codes, "code");
                annotator.resolve_ids(codebook.codes, codebook.codes, "parent");
            });

            // Resolve a bunch of foreign keys
            annotator.resolve_ids(self.rules, self.actions, "action");
            annotator.resolve_ids(self.rules, self.schemas, "codingschema");
            annotator.resolve_ids(self.rules, self.schemafields, "field");
            annotator.resolve_ids(self.schemafields, self.schemas, "codingschema");
            annotator.resolve_id(self.codingjob, self.schemas, "articleschema");
            annotator.resolve_id(self.codingjob, self.schemas, "unitschema");

            // Initialize data
            self.codebooks_fetched();
            self.highlighters_fetched();
            self.setup_wordcount();
            $("#loading_fields").dialog("close");
        }
    );
};

/*
 * Initialise highlighters by preparing annotator.fields.highlighter_labels. May
 * push 'undefined' if no label is available in the codebook for the requested
 * language.
 */
annotator.fields.highlighters_fetched = function(){
    var self = annotator.fields;
    var labels = [];
    var language_id, codebook;

    $.each(self.schemas, function(schema_id, schema){
        language_id = schema.highlight_language;
        $.each(schema.highlighters, function(i, codebook_id){
            codebook = self.codebooks[codebook_id];
            $.each(codebook.codes, function(i, code){
                labels.push(code.labels[language_id]);
            });
        });
    });

    annotator.fields.highlight_labels = labels;
};

/*
 * Called when initialising {article,unit}codings is done. Must be bound
 * (with bind()) to either article or unit.
 */
annotator.fields.add_rules = function (html) {
    $.each($("input", html), function (i, input) {
        $(input).focus();
        $(input).blur();
    });

    $(window).scrollTop(0);

    $("input", html).keyup(function (event) {
        // We need to figure out which rules apply when a user is done
        // editing this field.
        var input = $(event.currentTarget);

        // Parse id when field is "id_field_n"
        var field_id = input.get(0).id.split("_")[2];
        var rules = annotator.fields.get_field_codingrules()[field_id];

        if (rules === undefined) {
            console.log("No codingrules for field " + field_id);
            return;
        }

        // Check each rule
        var apply = [], not_apply = [];
        $.each(rules, function (i, rule_id) {
            var rule = annotator.fields.codingrules[rule_id];
            (annotator.fields.rule_applies(rule.parsed_condition)
                ? apply : not_apply).push(rule);
        });

        $.each(not_apply, function (i, rule) {
            rule.get_field_input().css("borderColor", "");
            rule.get_field_input().get(0).disabled = false;
            rule.get_field_input().attr("null", true);
            rule.get_field_input().attr("placeholder", "");
        });

        $.each(apply, function (i, rule) {
            if (rule.field === null || rule.action === null) return;

            var action = rule.get_action().label;

            if (action === ACTIONS.RED) {
                rule.get_field_input().css("borderColor", "red");
            } else if (action === ACTIONS.NOT_CODABLE) {
                rule.get_field_input().get(0).disabled = true;
            } else if (action === ACTIONS.NOT_NULL) {
                rule.get_field_input().attr("null", false);
                rule.get_field_input().attr("placeholder", "NOT NULL");
            }
        });
    });
};

/*
 * Get current value of input element. This takes in account hidden fields
 * and autocomplete fields.
 *
 * @param input: jQuery element 
 */
annotator.fields.get_value = function (input) {
    if (input.hasClass("ui-autocomplete-input")) {
        // This is an autocomplete field, so we need to fetch the value
        // from the hidden input field.
        return $(":hidden", input.parent()).val();
    }

    return input.val();
};


/*
 * Return true if rule applies, false if it is not.
 *
 * @type rule: object
 * @param rule: parsed_condition property of a CodingRule
 */
annotator.fields.rule_applies = function (rule) {
    var ra = annotator.fields.rule_applies;
    var truth, input, assert = function (cond) {
        if (!cond) throw "AssertionError";
    };

    // Get input element and its value
    var input = $("#id_field_" + rule.values[0].id);
    var input_value = annotator.fields.get_value(input);

    if (rule.type === null) {
        // Empty rule. "Waardeloos waar".
        return true;
    }

    // Resolve other types
    if (rule.type === OPERATORS.OR) {
        return ra(rule.values[0]) || ra(rule.values[1]);
    }

    if (rule.type === OPERATORS.AND) {
        return ra(rule.values[0]) && ra(rule.values[1]);
    }

    if (rule.type === OPERATORS.NOT) {
        return !ra(rule.value);
    }

    if (rule.type === OPERATORS.LESSER_THAN) {
        return input_value < rule.values[1];
    }

    if (rule.type === OPERATORS.GREATER_THAN) {
        return input_value > rule.values[1];
    }

    if (rule.type === OPERATORS.GREATER_THAN_OR_EQUAL_TO) {
        return input_value >= rule.values[1];
    }

    if (rule.type === OPERATORS.LESSER_THAN_OR_EQUAL_TO) {
        return input_value <= rule.values[1];
    }

    // rule.type must equal either EQUALS or NOT_EQUALS. Furthermore
    // rule.values[0] must be a codingschemafield and rule.values[1]
    // a value.
    assert(rule.values[0].type === "codingschemafield");
    assert(typeof(rule.values[1]) !== typeof({}));

    truth = input_value == rule.values[1];
    return (rule.type === OPERATORS.EQUALS) ? truth : !truth;
};

/*
 * Get descendants. Needs to be bound to a code object. This call is
 * automatically cached, and stored in code.descendants.
 */
annotator.fields.get_descendants = function(depth){
    depth = (depth === undefined) ? 0 : depth;

    if (depth >= 1000){
        throw "Maximum recursion depth exceeded, loop in codes?";
    }

    if (this.children.length === 0) return {};
    if (this.descendants !== undefined) return this.descendants;

    this.descendants = $.extend({}, this.children);
    $.each(this.children, function(code_id, code){
        $.extend(this.descendants, code.get_descendants(depth+1));
    });

    return this.descendants;
};

/*
 * Called when codebooks are fetched. Codebooks include all labels and all
 * functions. codebooks_fetched converts the flat codebookcodes into an
 * hierarchy.
 */
annotator.fields.codebooks_fetched = function(){
    var self = annotator.fields;

    // Set `roots` property on each codebook which contains a mapping
    // of code_id -> code.
    $.each(self.codebooks, function(codebook_id, codebook){
        codebook.roots = filter(function(code){ return code.parent === null }, codebook.codes);
        codebook.roots = annotator.map_ids(codebook.roots);
    });

    $.each(self.codebooks, function(codebook_id, codebook){
        // Initialise children property, and register get_descendants
        $.each(codebook.codes, function(code_id, code){
            code.children = {};
            code.get_descendants = annotator.fields.get_descendants.bind(code);
        });

        // Add property 'children' to each code, and call get_descendants for
        // caching purposes.
        $.each(codebook.codes, function(code_id, code){
            code.get_descendants();
            if (code.parent === null) return;
            code.parent.children[code.id] = code;
        });
    });

};

/*
 * Called when codingrules are fetched. Registeres two functions on each
 * rule object:
 *   get_action: returns action object (or undefined)
 *   get_field_input: returns jQuery input element
 */
annotator.fields.codingrules_fetched = function (rules) {
    var get_field_input = function () {
        return $("#id_field_" + this.field);
    };

    var get_action = function () {
        return annotator.fields.actions[this.action];
    };

    $.each(rules, function(rule_id, rule){
        rule.get_action = get_action.bind(rule);
        rule.get_field_input = get_field_input.bind(rule);
    });
};

/*
 * Get a field_id --> [rule, rule..] mapping.
 */
annotator.fields.get_field_codingrules = function () {
    if (annotator.fields.field_codingrules !== undefined) {
        return annotator.fields.field_codingrules;
    }

    var codingrule_fields = {};
    $.each(annotator.fields.codingrules, function (i, rule) {
        var self = this;
        codingrule_fields[rule.id] = [];

        /*
         * Return a list with all nodes in parsed condition tree.
         */
        self.walk = function (node) {
            if (node === undefined) {
                node = self.parsed_condition;
            }
            var nodes = [node];

            if (node.values !== undefined) {
                $.merge(nodes, self.walk(node.values[0]));
                $.merge(nodes, self.walk(node.values[1]));
            } else if (node.value !== undefined) {
                $.merge(nodes, self.walk(node.value));
            }

            return nodes;
        };

        $.each(self.walk(), function (i, node) {
            if (node.type === "codingschemafield") {
                if (codingrule_fields[rule.id].indexOf(node.id) === -1) {
                    codingrule_fields[rule.id].push(node.id);
                }
            }
        });
    });

    // Reverse dictionary
    var field_codingrules = {};
    $.each(codingrule_fields, function (rule_id, fields) {
        $.each(fields, function (i, field_id) {
            if (field_codingrules[field_id] === undefined) {
                field_codingrules[field_id] = [];
            }

            if (field_codingrules[field_id].indexOf(rule_id) === -1) {
                // Objects ('hashmaps') can only contain strings as keys, so
                // the rule_id's got converted to strings...
                field_codingrules[field_id].push(parseInt(rule_id));
            }
        });
    });

    return field_codingrules;
};

annotator.fields.setup_wordcount = function () {
    // http://stackoverflow.com/questions/6743912/get-the-pure-text-without-html-element-by-javascript
    var sentence_re = / id="sentence-[0-9]*"/g;
    var count = function () {
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
        $.each(html, function (i, el) {
            text += el.innerHTML.replace("</div><div>", " ");
            text += " ";
        });

        var count = 0;
        $.each(text.split(/ /g), function (i, word) {
            // replace functions like strip() in Python
            if (word.replace(/^\s+|\s+$/g, '') !== "") count++;
        });

        $("#wordcount").html(count);
    };

    $(".article-part").find(".sentences").mouseup(function () {
        window.setTimeout(count, 50);
    });
};

/*
 * Returns a list of codes which the coder can choose from, filtered on a given
 * search string.
 * 
 * @param field: selected field (must be in annotator.fields.fields)
 * @param term: term the user entered. All labels containing it will be shown.
 * @param selected_root: if relevant, the selected root. Only display descendants.
 */
annotator.fields.autocompletes.getSearchResults = function (field, term, selected_root) {
    var resultStart = []; // results where term is in the start of label
    var resultRest = []; // results where term can be anywhere in label
    var result = []; // final result
    var items = field.items;


    if (field.isOntology && field.split_codebook) {
        items = [];

        // This is a Codebook and needs to be splitted in root/descendants.
        if (selected_root === undefined) {
            // First box. Only display roots.
            $.each(annotator.fields.ontologies_parents[field["items-key"]], function (code_id, code) {
                items.push(code);
            });
        } else {
            // Second box. Display descendants.
            items = selected_root.descendants;
        }
    }

    var recentLength = 0; // just for debuggin

    var maxDropdownLength = annotator.fields.autocompletes.NUMBER_OF_DROPDOWN_RESULTS;
    if (field.id == 'unit') {
        maxDropdownLength = 1000; // make sure all (or at least more) units are visible
    }

    // add recent items in front of the result list
    if (term == '' && annotator.fields.ontologyRecentItems[field['items-key']]) {
        $.each(annotator.fields.ontologyRecentItems[field['items-key']], function (i, obj) {
            if (result.indexOf(obj) !== -1) result.push(obj);
        });
        result.reverse(); // reverse since last selected items are added last, while they should be displayed first
    }

    for (var i = 0; i < items.length; i++) {
        var index = items[i].label.toLowerCase().indexOf(term);
        if (index > -1) {
            if (index == 0) { // match in start of label
                resultStart.push(items[i]);
                if (resultStart.length > maxDropdownLength) {
                    break;
                }
            } else {
                if (resultRest.length < maxDropdownLength) {
                    resultRest.push(items[i]);
                }
            }
        }
    }

    if (field.noSorting != true) {
        resultStart.sort(annotator.sortLabels);
        resultRest.sort(annotator.sortLabels);
    }

    for (var i = 0; result.length < maxDropdownLength && i < resultStart.length; i++) {
        if (!annotator.fields.inArray(resultStart[i], result)) {
            result.push(resultStart[i]);
        }
    }
    for (var i = 0; result.length < maxDropdownLength && i < resultRest.length; i++) {
        if (!annotator.fields.inArray(resultRest[i], result)) {
            result.push(resultRest[i]);
        }
    }

    if (term == '') {
        // only add emtpy field when searching for empty string
        result.unshift({'value': '', 'label': annotator.fields.autocompletes.EMPTY_CODING_LABEL})
    }

    return result;
};


annotator.fields.inArray = function (obj, array) {
    /* check if obj is in array, using the value property to compare objects */
    var result = false;
    $.each(array, function (i, obj2) {
        if (obj.value == obj2.value) {
            result = true;
            return false;
        }
    });
    return result;
};


// TODO: implement

annotator.fields.fillOntologyDetailsBox = function (objid, label, inputEl) {
    var content = ['<h2>' + label + ' <span class="objid">[' + objid + ']</span></h2>'];

    var obj = annotator.fields.ontologyItemsDict[objid];

    if (obj.functions) {
        content.push('<table cellspacing="3"><tr><th>Function</th><th>Parent</th><th>Start</th><th>End</th></tr>');
        $.each(obj.functions, function (i, func) {
            content.push('<tr><td>');
            content.push(func['function']);
            content.push('</td><td>');
            if (func.parentid in annotator.fields.ontologyItemsDict) {
                // TODO: make nice safe jQuery html here, this is a security risk
                content.push(annotator.fields.ontologyItemsDict[func.parentid].label);
            }
            content.push('</td><td>');
            if (func.from) content.push(func.from);
            content.push('</td><td>');
            if (func.to) content.push(func.to);
            content.push('</td></tr>');
        });
        content.push('</table>');
    }

    if (content.length == 1) {
        console.debug('no details for', objid);
        $('#autocomplete-details').hide();
        return;
    }


    $('#autocomplete-details').html(content.join(''));
    $('#autocomplete-details').find('ul').menu();
    $("#autocomplete-details").find("li").bind("click", function () {
        console.log('select');
        inputEl.val($(this).text());
        inputEl.next().val($(this).attr('value'));
        inputEl.focus();
        if (inputEl.parents('#unitcoding-table').length > 0) {
            annotator.unitcodings.onchangeSentenceCoding(inputEl);
        }
        if (inputEl.parents('#article-coding').length > 0) {
            annotator.articlecodings.onchange(inputEl);
        }
    });
    $('#autocomplete-details').show();
};


annotator.fields.addToRecentItemsList = function (field, value, label) {
    var key = field['items-key'];
    annotator.fields.ontologyRecentItems[key] = $.grep(annotator.fields.ontologyRecentItems[key],
        function (item, i) {
            return item.value != value;
        });
    annotator.fields.ontologyRecentItems[key].push({'value': value, 'label': label});
    console.debug('added to recent', label);
    if (annotator.fields.ontologyRecentItems[key].length > annotator.fields.autocompletes.NUMBER_OF_DROPDOWN_RESULTS) {
        annotator.fields.ontologyRecentItems[key].pop(); // remove item to keep list from growing too large
    }
};


annotator.fields.autocompletes.setInputValue = function (value, label, inputEl, field) {
    /* set the inputEl to a value with label */
    if (label == annotator.fields.autocompletes.EMPTY_CODING_LABEL) {
        inputEl.val('').removeAttr("_value");
    } else {
        if (!(field.isOntology && field.split_codebook && inputEl.attr("root") === undefined)) {
            inputEl.parent().children(":hidden").val(value); // set value of hidden input
        }
        inputEl.val(label).attr("_value", value);

        if (field.isOntology) {
            annotator.fields.addToRecentItemsList(field, value, label);
        }
    }
    if (inputEl.attr('name') == 'unit') {
        annotator.unitcodings.setSentence();
    }
    if (inputEl.parents('#unitcoding-table').length > 0) { // if input is in sentences table
        annotator.unitcodings.onchangeSentenceCoding(inputEl);
        console.log("Should I set NET codings??");
        //annotator.fields.setNETCodings(field, value, label);
    }

    if (inputEl.parents('#article-coding').length > 0) {
        annotator.articlecodings.onchange(inputEl);
    }
};


annotator.fields.findInOntology = function (label, ontology) {
    /* find label in ontology, return the corresponding item */
    for (var i = 0; i < ontology.length; i++) {
        var obj = ontology[i];
        if (obj.label == label) {
            console.debug('found in ontology', label);
            return obj;
        }
    }
    console.error('not found in ontology', label);
    return null;
};


annotator.fields.isChild = function (obj, objid) {
    console.debug('check ischild for', obj, objid);
    if (!obj) return false;
    if (obj.parentid == objid) {
        return true;
    }
    if (obj.parentid in annotator.fields.ontologyItemsDict) {
        var parent = annotator.fields.ontologyItemsDict[obj.parentid];
        return annotator.fields.isChild(parent, objid);
    }
    return false;
};


annotator.fields.isObjectOrChild = function (inputLabel, obj, ontology) {
    // check if inputLabel is the obj or a child of it, in ontology, which should be an array of objects
    if (inputLabel == obj.label) {
        console.debug('inputlabel == objlabel');
        return true;
    }
    var inputObj = annotator.fields.findInOntology(inputLabel, ontology);
    if (inputObj && inputObj.value in annotator.fields.ontologyItemsDict) {
        return annotator.fields.isChild(annotator.fields.ontologyItemsDict[inputObj.value], obj.value);
    }
    return false;
};


annotator.fields.getFieldByInputName = function (inputname) {
    var autocompleteid = inputname.replace(/field_/, '');
    return annotator.fields.fields[autocompleteid];
};


/*
 * Called when an element with autocompletion is focused.
 */
annotator.fields.autocompletes.onFocus = function () {
    if ($(this).hasClass('ui-autocomplete-input')) { // already an autocomplete element
        console.log('already an autocomplete'); // should never be called, event should by unbind
        return;
    }
    var inputEl = $(this);
    var field = annotator.fields.getFieldByInputName(inputEl.attr('name'));

    if (field == undefined) {
        console.debug('field undefined', field.id);
        return;
    }

    inputEl.unbind('focus'); // unbind event that calls this function

    if (field.items.length == 0) {
        console.log('no field items, ignoring', field.id);
        return;
    }

    inputEl.autocomplete({
        source: function (req, resp) {
            var selected_root = undefined;
            if (this.element.attr("root") !== undefined) {
                var root = $("#" + this.element.attr("root"));
                if (root.attr("_value") === undefined) {
                    // No root selected! Do not display list.
                    resp([]);
                    return;
                }

                var codebook = annotator.fields.hierarchies[field["items-key"]];
                selected_root = codebook[root.attr("_value")];
            }

            var term = req.term.toLowerCase();
            var result = annotator.fields.autocompletes.getSearchResults(field, term, selected_root);
            result.sort(function (a, b) {
                return a.ordernr - b.ordernr;
            });
            resp(result);
        },
        selectItem: true,
        isOntology: field.isOntology,
        minLength: 0,//annotator.fields.fields[field.id].minLength,
        select: function (event, ui) {
            var value = ui.item.value;
            var label = ui.item.label;
            annotator.fields.autocompletes.setInputValue(value, label, inputEl, field);
            return false;
        },
        focus: function (event, ui) {
            if (field.isOntology) {
                // create details box for ontologies
                var objid = ui.item.value;
                var label = ui.item.label;

                if (objid in annotator.fields.ontologyItemsDict) {
                    annotator.fields.fillOntologyDetailsBox(objid, label, inputEl);
                } else {
                    $('#autocomplete-details').hide();
                }
            }
            return false;
        },
        open: function (event, ui) {
            annotator.fields.autocompletes.onOpenAutocomplete($(this));
            //$(".ui-autocomplete").css("z-index", 1500); // needed to avoid dropdown being below fixedheader of sentencetable
        },
        delay: 5,
        close: function () {
            $('#autocomplete-details').hide(); // when closing auto complete, also close the details box
        }
    });

    //if(autocomplete.autoOpen){
    inputEl.bind('focus', function () {
        if (field.showAll == true) {
            inputEl.autocomplete('search', '');
        } else {
            inputEl.autocomplete('search');
        }
    });
    //}

    console.debug('added autocomplete for ' + field.id);
    inputEl.focus();
};

annotator.fields.autocompletes.add_autocomplete = function (coding) {
    var self = annotator.fields;
    var input = coding.get_input();

    input.focus(self.autocompletes.on_focus);
    if (coding.schemafield.codebook !== null){
    }
};

annotator.fields.autocompletes.addAutocompletes = function (jqueryEl) {
    jqueryEl.find('input:text').each(function (i, input) {
        var inputEl = $(input);
        var fieldNumber = inputEl.attr('name').replace(/field_/, '');
        var field = annotator.fields.fields[fieldNumber];

        if (fieldNumber in annotator.fields.fields) {
            inputEl.focus(annotator.fields.autocompletes.onFocus);

            if (field.isOntology && field.split_codebook) {
                var desc = $("<input type='text'>");
                inputEl.parent().append(desc);
                inputEl.attr("placeholder", "Root..");

                desc.attr("skip_saving", true);
                desc.attr("placeholder", "Descendant..").attr("root", inputEl.get(0).id);
                desc.attr("name", inputEl.attr("name"));
                desc.focus(annotator.fields.autocompletes.onFocus);

                if (inputEl.val() !== '') {
                    /* Well.. here comes a bit of a hack. We don't know anything about the
                     * parent and we only know the *label* of the coded value, not the id. As
                     * we still want to display the parent, we need to find a code with the
                     * same label as the given code. However, this label is not guarenteed to be
                     * unique, so we could display the wrong parent.. Should work in 99% of the
                     * cases though.
                     *
                     * Btw: I'm so sorry :-(
                     * - martijn
                     */
                    var found = [];
                    var label = inputEl.val();
                    var code;
                    $.each(annotator.fields.ontologies_parents[field['items-key']], function (i, root) {
                        for (var i = 0; i < root.descendants.length; i++) {
                            code = root.descendants[i];
                            if (code.label === label && found.indexOf(code) === -1) {
                                code.root = root;
                                found.push(code);
                            }
                        }
                    });

                    if (found.length > 1) {
                        console.log("We found multiple codes for this label :-(:", found);
                    } else if (found.length == 0) {
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
};


annotator.fields.autocompletes.onOpenAutocomplete = function (el) {
    var autocomplete = el.data("autocomplete");
    var menu = autocomplete.menu;

    if (autocomplete.options.selectItem) {
        var val = el.val();
        //console.debug('val ' + val);
        var selectedItem = null;
        menu.element.children().each(function (i, child) {
            //console.debug(child);
            if ($(child).text() == val) {
                selectedItem = child;
                return false;
            }
        });
        if (selectedItem == null) {
            selectedItem = menu.element.children().first();
        }
        menu.activate($.Event({type: "mouseenter"}), $(selectedItem)); // select first menu item
    }

    if (autocomplete.options.isOntology) { // enable detail box
        var firstItem = menu.element.children().first();
        var detailBox = $('#autocomplete-details');
        detailBox.css('top', firstItem.offset().top);
        if (detailBox.outerWidth() + firstItem.parent().offset().left + firstItem.parent().outerWidth() > $(window).width()) { // if too wide, put on left side
            detailBox.css('left', firstItem.parent().offset().left - detailBox.outerWidth());
        } else {
            detailBox.css('left', firstItem.parent().offset().left + firstItem.parent().outerWidth());
        }
    }

    var $window = $(window);
    if ($window.height() + $window.scrollTop() - el.offset().top < 300) {
        console.debug('scroll', $window.height() + $window.scrollTop() - el.offset().top);//To ' + (-($window.height() - 300)));
        $window.scrollTo(el, {offset: -($window.height() - 305)}); // scroll to sentence in middle of window, so dropdown is fully visible
    }
};




