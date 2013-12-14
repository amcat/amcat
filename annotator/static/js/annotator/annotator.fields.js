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
        if (widgets.SCHEMATYPES[schemafield.fieldtype] === "codebook"){
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
    return $.grep(array, function(o){ return o.value == obj.value }).length > 0;
};


annotator.fields.getFieldByInputName = function (inputname) {
    var autocompleteid = inputname.replace(/field_/, '');
    return annotator.fields.fields[autocompleteid];
};


