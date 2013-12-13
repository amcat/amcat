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

AUTOCOMPLETE_LANGUAGE = 0;

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
            self.codingrules = annotator.map_ids(rules[0].results);
            self.actions = annotator.map_ids(actions[0].results);
            self.codebooks = annotator.map_ids(codebooks[0].results);
            self.schemas = annotator.map_ids(schemas[0].results);
            self.schemafields = annotator.map_ids(schemafields[0].results);
            self.codingjob = codingjob[0];

           // Convert codebook.codes (array) to mapping code_id -> code
            $.each(self.codebooks, function(codebook_id, codebook){
                codebook.codes = annotator.map_ids(codebook.codes, "code");
                annotator.resolve_ids(codebook.codes, codebook.codes, "parent");
            });

            // Resolve a bunch of foreign keys
            annotator.resolve_ids(self.codingrules, self.actions, "action");
            annotator.resolve_ids(self.codingrules, self.schemas, "codingschema");
            annotator.resolve_ids(self.codingrules, self.schemafields, "field");
            annotator.resolve_ids(self.schemafields, self.schemas, "codingschema");
            annotator.resolve_ids(self.schemafields, self.codebooks, "codebook");
            annotator.resolve_id(self.codingjob, self.schemas, "articleschema");
            annotator.resolve_id(self.codingjob, self.schemas, "unitschema");

            // Initialize data
            self.codebooks_fetched();
            self.highlighters_fetched();
            self.setup_wordcount();
            self.schemafields_fetched();
            $("#loading_fields").dialog("close");
        }
    );
};

annotator.fields.get_choices = function(codes, language_id){
    language_id = language_id || AUTOCOMPLETE_LANGUAGE;
    var get_code = function(){ return this };

    var labels = $.map(codes, function(code){
        return {
            // We can't store code directly, as it triggers an infinite
            // loop in some jQuery function (autocomplete).
            get_code : get_code.bind(code),
            label : code.labels[language_id],
            value : code.labels[language_id],
            descendant_choices : annotator.fields.get_choices(code.descendants)
        }
    });

    labels.sort(function(a, b){
        return a.ordernr - b.ordernr;
    });

    return labels;
};

annotator.fields.schemafields_fetched = function(){
    var codes;

    $.each(annotator.fields.schemafields, function(id, schemafield){
        if (schemafield.choices !== undefined) return;
        if (schemafield.fieldtype === SCHEMATYPES.CODEBOOK){
            codes = (schemafield.split_codebook ? schemafield.codebook.roots : schemafield.codebook.codes);
            schemafield.choices = annotator.fields.get_choices(codes);
        }
    });
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
   $("input.coding", html).change(function (event) {
       var container, sentence, schemafield, rules;

       container = annotator.fields.get_container_by_input($(event.currentTarget));
       sentence = container.attr("sentence_id");
       sentence = (sentence === undefined) ? null : annotator.sentences[sentence];
       schemafield = annotator.fields.schemafields[container.attr("codingschemafield_id")];

       rules = annotator.fields.get_field_codingrules()[schemafield.id];

       if (rules === undefined) {
           console.log("No codingrules for field " + schemafield.id);
           return;
       }

       // Check each rule
       var apply = [], not_apply = [];
       $.each(rules, function (i, rule) {
           (annotator.fields.rule_applies(sentence, schemafield, rule.parsed_condition)
               ? apply : not_apply).push(rule);
       });

       // If a rule not applies, reset their error-state
       $.each(not_apply, function (i, rule) {
           // We mark all input fields in the container belonging to the rule destination
           var inputs = annotator.fields.get_container(rule.field, sentence).find("input");

           inputs.css("borderColor", "");
           inputs.prop("disabled", false);
           inputs.attr("null", true);
           inputs.attr("placeholder", "");
       });

       $.each(apply, function (i, rule) {
           var inputs = annotator.fields.get_container(rule.field, sentence).find("input");

           if (rule.field === null || rule.action === null) return;

           var action = rule.action.label;
           if (action === ACTIONS.RED) {
               inputs.css("borderColor", "red");
           } else if (action === ACTIONS.NOT_CODABLE) {
               inputs.prop("disabled", true);
           } else if (action === ACTIONS.NOT_NULL) {
               inputs.attr("null", false);
               inputs.attr("placeholder", "NOT NULL");
           }
       });
   });
};

/*
 * Get value of coding. This function looks for an input element with
 * class 'coding', which can either have an attribute 'intval' which
 * will be returned (or null, if EMPTY_INTVAL is set). Else, it will
 * return a string which is equal to the inner value of the input element.
 *
 * @param container: jQuery/DOM element
 * @return: null / int / string
 */
annotator.fields.get_value = function (container) {
    var value, coding = $(".coding", $(container));

    if (coding.size() == 0) throw "No coding found in container. Bug.";
    if (coding.size() > 1) throw "Muliple codings found in container. Bug."

    value = coding.attr("intval");
    if (value === undefined){
        return coding.val();
    } else if (value == EMPTY_INTVAL) {
        return null;
    }
    return parseInt(value);
};

/*
 * Get container of `schemafield` and `sentence`. If sentence is null,
 * an articlecoding-container is returned. A container contains exactly
 * one input-element which value can be retrieved by get_value().
 *
 * @type schemafield: schemafield object
 * @type sentence: sentence object
 */
annotator.fields.get_container = function(schemafield, sentence){
    if (sentence !== null){
        return $("#unitcoding-table-part").find(
            "[codingschemafield_id={0}][sentence_id={1}]".f(schemafield.id, sentence.id)
        )
    }
    return $("#article-coding").find("[codingschemafield_id={0}]".f(schemafield.id));
};

/*
 * Get container of coding, given an input-field which represents a coding.
 *
 * @type el: jQuery element
 * @requires: el.hasClass("coding")
 */
annotator.fields.get_container_by_input = function(el){
    // Work through hierarchy until we found either a coding-container or
    // the root of this document.
    while ((el=el.parent()).length && !el.hasClass("coding-container")){ }

    if (!el.length){
        throw "No coding-container found for this element."
    }

    return el;
};



/*
 * Return true if rule applies, false if it is not.
 *
 * @type rule: object
 * @param rule: CodingRule.parsed_condition
 * @type schemafield: Schemafield
 * @type sentence: Sentence object
 */
annotator.fields.rule_applies = function (sentence, schemafield, rule) {
    // Create partially applied rule_applies function
    var ra = function(rule){
        annotator.fields.rule_applies(sentence, schemafield, rule)
    };

    var truth, assert = function (cond) {
        if (!cond) throw "AssertionError";
    };

    var input_value = annotator.fields.get_value(
        annotator.fields.get_container(schemafield, sentence)
    );

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

    var descendants = $.extend({}, this.children);
    $.each(this.children, function(code_id, code){
        $.extend(descendants, code.get_descendants(depth+1));
    });

    this.descendants = descendants;
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
        codebook.roots = annotator.map_ids(codebook.roots, "code");
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
            if (code.parent === null) return;
            code.parent.children[code_id] = code;
        });

        // Cache descendants
        $.each(codebook.codes, function(i, code) { code.get_descendants() });
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
            var rules = field_codingrules[field_id] = field_codingrules[field_id] || [];
            if (rules.indexOf(rule_id) === -1) rules.push(parseInt(rule_id));
        });
    });

    $.each(field_codingrules, function(field_id, rules){
        field_codingrules[field_id] = $.map(rules, function(rule_id){
            return annotator.fields.codingrules[rule_id];
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


annotator.fields.getFieldByInputName = function (inputname) {
    var autocompleteid = inputname.replace(/field_/, '');
    return annotator.fields.fields[autocompleteid];
};


