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

/*
 * Usage:
 *
 * 'Added {0} by {1} to your collection'.f(title, artist)
 * 'Your balance is {0} USD'.f(77.7)
 */
String.prototype.format = String.prototype.f = function() {
    var s = this,
        i = arguments.length;

    while (i--) {
        s = s.replace(new RegExp('\\{' + i + '\\}', 'gm'), arguments[i]);
    }
    return s;
};

$.values = function(obj) {
    return $.map(obj, function(value, _) {
        return value;
    });
};

annotator = (function(self){
    /******** STATE & CONSTANTS *******/
    self.API_URL = "/api/v4/";
    self.STATUS = {
        NOT_STARTED: 0,
        IN_PROGRESS: 1,
        COMPLETE: 2,
        IRRELEVANT: 9
    };

    self.get_empty_state = function(){
        return {
            requests : null,
            coded_article_id: -1,
            coded_article: null,
            deleted_rows: [],
            modified_rows: [],
            sentence_codings_modified: false,
            article_coding_modified: false,
            article_coding : null,
            sentence_codings: [],
            codings : [],
            sentences : []
        }
    };

    self.width_warning = "Your window width is lower than 1000 pixels. For Annotator to function ";
    self.width_warning += "normally, you need to use a wider window.";

    /*
     * Contains model objects which are constant for this particular
     * codingjob. All volatile models are stored in self.state. It is
     * populated after initialise() finished.
     */
    self.models = {
        "rules" : null,
        "actions" : null,
        "codebooks" : null,
        "schemas" : null,
        "schemafields" : null
    };

    self.sentence_schemafields = [];
    self.article_schemafields = [];

    self.state = self.get_empty_state();
    self.highlight_labels = null;
    self.codingjob = null;
    self.datatable = null;
    self.previous_width = -1;
    self.codingjob_id = -1;
    self.project_id = -1;
    self.coder_id = -1;

    self.dialog_ok = {
        OK : function(){
            $(this).dialog("close");
        }
    };

    self.dialog_defaults = {
        resizable: false,
        modal: true,
        autoOpen: false,
        buttons : self.dialog_ok
    };

    /* Containers & dialogs. These can only be set if DOM is ready. */
    self.initialise_containers = function(){
        self.article_coding_container = $("#article-coding");
        self.sentence_codings_container = $("#unitcoding-table-part");
        self.article_container = $("article");
    };



    self.initialise_buttons = function(){
        self.next_btn = $("#next-article-button");
        self.prev_btn = $("#previous-article-button");
        self.select_all_btn = $("#select-all-sentences-button");
        self.save_btn = $("#save-button");
        self.save_continue_btn = $("#save-continue-button");
        self.irrelevant_btn = $("#irrelevant-button");
        self.copy_btn = $("#copy-coding-button");
        self.delete_btn = $("#delete-button");
        self.help_btn = $("#help-button");

        self.next_btn.click(self.select_next_article);
        self.prev_btn.click(self.select_prev_article);
        self.select_all_btn.click(self.select_all_sentences);
        self.save_btn.click(self.save);
        self.save_continue_btn.click(self.save_and_continue);
        self.irrelevant_btn.click(self.irrelevant_and_save);
        self.copy_btn.click(self.copy);
        self.delete_btn.click(self.delete);
        self.help_btn.click(function(){ self.help_dialog.dialog("open"); });

        $(".coding-part").hide();
        $(".sentence-options").hide();
        $(window).scroll(self.window_scrolled);
        $(window).resize(self.window_resized);
        $(window).trigger("resize");
    };

    self.initialise_dialogs = function(){
        self.loading_dialog = $("<div>Loading..</div>").dialog(self.dialog_defaults);
        self.message_dialog = $("#message-dialog").dialog(self.dialog_defaults);
        self.width_warning_dialog = $("<div>{0}</div>".f(self.width_warning)).dialog(self.dialog_defaults);
        self.save_dialog = $("#dialog-save").dialog(self.dialog_defaults);
        self.help_dialog = $("#dialog-help").dialog($.extend({}, self.dialog_defaults, { width: 500 }));
        self.delete_row_dialog = $("#dialog-confirm-delete-row").dialog($.extend({}, self.dialog_defaults, {
            buttons: {
                "Delete row": function(){
                    self.delete();
                    $(this).dialog("close");
                },
                Cancel: function(){
                    $(this).dialog("close");
                }
            }
        }))
    };

    self.initialise_fields = function(){
        self.loading_dialog.text("Loading fields..").dialog("open");

        self._requests = [
            $.getJSON(self.get_api_url()),
            $.getJSON(self.get_api_url() + "coding_rules"),
            $.getJSON(self.get_api_url() + "codebooks"),
            $.getJSON(self.get_api_url() + "codingschemas"),
            $.getJSON(self.get_api_url() + "codingschemafields"),
            $.getJSON(self.API_URL + "coding_rule_actions")
        ];

        $.when.apply(undefined, self._requests).then(function (codingjob, rules, codebooks, schemas, schemafields, actions) {
                // Check if all request completed successfully. (If not, an
                // error is already thrown, but we need not continue processing
                // the data.
                if (!all(function (request) {
                    return request.statusText === "OK";
                }, self._requests)) {
                    throw "Not all requests completed successfully.";
                }

                // Extract results from response
                self.models.rules = map_ids(rules[0].results);
                self.models.actions = map_ids(actions[0].results);
                self.models.codebooks = map_ids(codebooks[0].results);
                self.models.schemas = map_ids(schemas[0].results);
                self.models.schemafields = map_ids(schemafields[0].results);
                self.codingjob = codingjob[0];

                // Convert codebook.codes (array) to mapping code_id -> code
                $.each(self.models.codebooks, function(codebook_id, codebook){
                    codebook.codes = map_ids(codebook.codes, "code");
                    resolve_ids(codebook.codes, codebook.codes, "parent");
                });

                // Resolve a bunch of foreign keys
                resolve_ids(self.models.rules, self.models.actions, "action");
                resolve_ids(self.models.rules, self.models.schemas, "codingschema");
                resolve_ids(self.models.rules, self.models.schemafields, "field");
                resolve_ids(self.models.schemafields, self.models.schemas, "codingschema");
                resolve_ids(self.models.schemafields, self.models.codebooks, "codebook");
                resolve_id(self.codingjob, self.models.schemas, "articleschema");
                resolve_id(self.codingjob, self.models.schemas, "unitschema");

                // Initialize data
                self.codebooks_fetched();
                self.highlighters_fetched();
                self.schemafields_fetched();
                self.initialise_sentence_codings_table();
                self.loading_dialog.dialog("close");
            }
        );

    };

    /******** KEYBOARD SHORTCUTS *******/
    self.shortcuts = function(){ return {
        "ctrl+s" : self.save_btn.trigger.bind(self.save_btn, "click"),
        "ctrl+down" : self.add_row,
        "ctrl+shift+down" : self.add_row,
        "shift+down" : self.copy_row,
        "ctrl+i" : self.irrelevant_btn.trigger.bind(self.irrelevant_btn, "click"),
        "ctrl+d" : self.save_continue_btn.trigger.bind(self.save_continue_btn, "click")
    }};

    /******** PUBLIC FUNCTIONS *******/
    /* Returns true if a coding was modified (article or sentence) */
    self.modified = function(){
        return self.sentence_codings_modified() | self.state.article_coding_modified;
    };

    self.sentence_codings_modified = function(){
        return !!(self.state.deleted_rows.length || self.state.modified_rows.length);
    };

    /* Returns absolute url pointing to this codingjob (slash-terminated)  */
    self.get_api_url = function(){
        return "{0}projects/{1}/codingjobs/{2}/".f(self.API_URL, self.project_id, self.codingjob_id);
    };

    /* Returns (new) DOM representation of the articlecoding */
    self.get_article_coding_html = function(){
        var schemafields = self.article_schemafields;
        var table = $("<table>")
            .attr("annotator_coding_id", self.state.article_coding.annotator_id)
            .addClass("coding");

        return table.append($.map(widgets.get_html(schemafields, null), function(widget, i){
            var label = widgets.get_label_html(schemafields[i], widget);
            return $("<tr>")
                .append($("<td>").append(label))
                .append($("<td>").append(widget));
        }));
    };

    /*
     * Initialises table headers (sentence + fields + action) (columns)
     */
    self.initialise_sentence_codings_table = function () {
        var table_header = $("<tr>");
        table_header.append($("<th>").text("Sentence"));
        table_header.append(
            $.map(self.sentence_schemafields, function(schemafield){
                return $("<th>").text(schemafield.label);
            })
        );

        self.sentence_codings_container.find("table")
            .append($("<thead>").append(table_header))
            .append($("<tbody>"));
    };


    self.initialise_sentence_codings = function () {
        if (self.codingjob.unitschema === null) return $("<div>");

        if (self.state.sentence_codings.length === 0){
            var empty_coding = self.get_empty_coding();
            empty_coding.codingschema = self.codingjob.unitschema;
            self.state.sentence_codings.push(empty_coding);
        }

        $.map(self.state.sentence_codings, self.append_sentence_coding);
    };

    /*
     * Create new row, and append it to existing table
     */
    self.append_sentence_coding = function(coding){
        self.sentence_codings_container.find("tbody").append(
            self.get_sentence_coding_html(coding)
        );
    };

    /* Returns (new) DOM representation of a single sentence coding */
    self.get_sentence_coding_html = function(coding){
        var coding_el = $("<tr>").addClass("coding").attr("annotator_coding_id", coding.annotator_id);
        coding_el.append(widgets.sentence.get_html());
        coding_el.append($.map(widgets.get_html(self.sentence_schemafields), function(widget){
            return $("<td>").append(widget);
        }));

        return coding_el;
    };

    self.select_all_sentences = function () {

    };

    self.validate = function(){
        return true;
    };

    self.save = function(success_callback){
        var coding_values = {};

        // Check whether we want to save.
        var validation = self.validate();
        if (validation !== true){
            self.message_dialog.text("Could not validate, relevant fields are marked red.").dialog("open");
            return;
        }

        // Get codingvalues of article codings
        var coding_el = self.article_coding_container.find(".coding");
        var article_coding_values = $.map(coding_el.find(".widget"), function(widget){
            return widgets.get_codingvalue(self.state.article_coding, null, $(widget));
        });

    };

    self.save_and_continue = function () {
        self.save(self.select_next_article);
    };

    self.irrelevant_and_save = function () {

    };
    self.select_next_article = function () {

    };
    self.select_prev_article = function () {

    };

    /* Returns an every increasing (unique) integer */
    self._id = 0;
    self.get_new_id = function(){
        return self._id += 1
    };


    self.coded_article_fetched = function(article, codings, sentences){
        console.log("Retrieved " + codings.length + " codings and " + sentences.length + " sentences");

        $.each(codings[0].results, function(i, coding){
            coding.annotator_id = self.get_new_id();
        });

        codings = map_ids(codings[0].results, "annotator_id");
        sentences = map_ids(sentences[0].results);
        resolve_ids(codings, sentences, "sentence");

        $.each(codings, function(_, coding){
            map_ids(coding.values);
            resolve_ids(coding.values, self.models.schemafields, "field");

            $.each(coding.values, function(_, value){
                value.coding = coding;
            });
        });

        self.state.sentences = sentences;
        self.state.codings = codings;
        self.state.coded_article = article;

        var get_unit = function () {
            return "{0}.{1}".f(this.parnr, this.sentnr);
        };

        $.each(sentences, function(_, sentence){
            sentence.get_unit = get_unit.bind(sentence);
        });

        // Set buttons
        // $('#next-article-button').button("option", "disabled", row.next().length == 0);
        //$('#previous-article-button').button("option", "disabled", row.prev().length == 0);

        $("#article-comment").text(article.comments || "");
        $('#article-status').find('option:contains("' + article.status + '")').attr("selected", "selected");

        // Initialise coding area
        self.sentences_fetched(sentences);
        self.highlight();
        self.codings_fetched();

        $(".coding-part").show();
        $("#article-comment").focus();

        self.loading_dialog.dialog("close");
    };

    self.highlight = function(){
        var _labels = [], escape_regex, labels = self.highlight_labels;
        console.log("Highlighting ", labels.length ," labels in article..");

        escape_regex = function(str) {
            return str.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, "\\$&");
        };

        $.each(labels, function(i, label){
            _labels.push(escape_regex(label));
        });

        $("div.sentences").easymark("highlight", _labels.join(" "));
    };

    /*
     * Resets internal state and fetches new coded article, which consists of:
     *  - coded_article
     *  - codings + values
     *  - sentences
     * coded_article_fetched is called when requests finished
     */
    self.get_article = function(article_id){
        var base_url = self.get_api_url() + "coded_articles/" + article_id + "/";

        self.state = self.get_empty_state();
        self.state.coded_article_id = article_id;

        self.state.requests = [
            $.getJSON(base_url),
            $.getJSON(base_url + "codings"),
            $.getJSON(base_url + "sentences")
        ];

        self.loading_dialog.text("Loading codings..").dialog("open");
        $.when.apply(undefined, self.state.requests).then(self.coded_article_fetched);
    };


    /*
     * Get descendants. Needs to be bound to a code object. This call is
     * automatically cached, and stored in code.descendants.
     */
    self.get_descendants = function(depth){
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

    self.get_empty_coding = function(){
        return {
            annotator_id: self.get_new_id(),
            id: null,
            codingschema: null,
            article: self.state.coded_article,
            sentence: null,
            comments: null,
            codingjob: self.codingjob
        };

    };

    self.is_article_coding = function(coding){
        return coding.sentence === null;
    };


    /******** EVENTS *******/
    // TODO: Only initialise article coding html once.
    self.codings_fetched = function(){
        // Determine sentence codings
        self.state.sentence_codings = $.grep($.values(self.state.codings), function(c){
            return !self.is_article_coding(c);
        });

        // Determine article coding
        var article_coding = $.grep($.values(self.state.codings), self.is_article_coding);

        if (article_coding.length === 0){
            var empty_coding = self.get_empty_coding();
            empty_coding.codingschema = self.codingjob.articleschema;
            self.state.article_coding = empty_coding;
            self.state.codings[empty_coding.annotator_id] = empty_coding;
        } else {
            self.state.article_coding = article_coding[0];
        }

        // Create html content
        self.article_coding_container.html(self.get_article_coding_html());
        rules.add(self.article_coding_container);

        self.initialise_sentence_codings();
        //rules.add(self.sentence_codings_container);
    };

    /*
     * Registers property 'choiches' on each schemafield, which can be used
     * for autocompletes.
     *
     * TODO: Move to autocomplete
     */
    self.schemafields_fetched = function(){
        var codes;

        $.each(self.models.schemafields, function(id, schemafield){
            if (schemafield.choices !== undefined) return;
            if (widgets.SCHEMATYPES[schemafield.fieldtype] === "codebook"){
                codes = (schemafield.split_codebook ? schemafield.codebook.roots : schemafield.codebook.codes);
                schemafield.choices = autocomplete.get_choices(codes);
            }
        });


        // Categorize schemafields
        var articleschema = self.codingjob.articleschema;
        $.each(self.models.schemafields, function(id, schemafield){
            if (schemafield.codingschema === articleschema){
                self.article_schemafields.push(schemafield);
            } else {
                self.sentence_schemafields.push(schemafield)
            }
        });

        // Sort schemafields according to fieldnr
        self.sentence_schemafields.sort(function(f1, f2){ return f1.fieldnr - f2.fieldnr });
        self.article_schemafields.sort(function(f1, f2){ return f1.fieldnr - f2.fieldnr });
    };

    /*
     * Called when codebooks are fetched. Codebooks include all labels and all
     * functions. codebooks_fetched converts the flat codebookcodes into an
     * hierarchy.
     */
    self.codebooks_fetched = function(){
        // Set `roots` property on each codebook which contains a mapping
        // of code_id -> code.
        $.each(self.models.codebooks, function(codebook_id, codebook){
            codebook.roots = filter(function(code){ return code.parent === null }, codebook.codes);
            codebook.roots = map_ids(codebook.roots, "code");
        });

        $.each(self.models.codebooks, function(codebook_id, codebook){
            // Initialise children property, and register get_descendants
            $.each(codebook.codes, function(code_id, code){
                code.children = {};
                code.get_descendants = self.get_descendants.bind(code);
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
     * Initialise highlighters by preparing self.highlighter_labels. May
     * push 'undefined' if no label is available in the codebook for the requested
     * language.
     */
    self.highlighters_fetched = function(){
        var labels = [];
        var language_id, codebook;

        $.each(self.models.schemas, function(schema_id, schema){
            language_id = schema.highlight_language;
            $.each(schema.highlighters, function(i, codebook_id){
                codebook = self.models.codebooks[codebook_id];
                $.each(codebook.codes, function(i, code){
                    labels.push(code.labels[language_id]);
                });
            });
        });

        self.highlight_labels = labels;
    };


    // TODO: Remove legacy code (get_unit() logic, etc.)
    self.sentences_fetched = function(sentences) {
        var html = $('<div>');
        var prev_parnr = 1;

        $.each(sentences, function (i, s) {
            var _html = $('<div />').attr('id', 'sentence-' + s.id);
            if (s.parnr != prev_parnr) {
                _html.addClass('new-paragraph');
            }
            if (s.get_unit() == '1.1') {
                _html.append($('<h2 />').text(s.text));
            } else {
                _html.append($('<span />').addClass('annotator-sentencenr').text('(' + s.get_unit() + ') '));
                _html.append(document.createTextNode(s.sentence));
            }
            prev_parnr = s.parnr;
            html.append(_html);
        });

        if (sentences.length == 0) {
            html.append('No sentences found for this article');
        }

        $('.sentence-options').show();
        $('.sentences').html(html);
    };

    self.datatables_row_clicked = function(row){
        // Get article id which is stored in the id-column of the datatable
        var article_id = parseInt(row.children('td:first').text());
        self.datatable.find(".row_selected").removeClass("row_selected");
        self.datatable.parent().scrollTo(row, {offset: -50});
        self.get_article(article_id);
    };

    self.window_scrolled = function(){
        if ($(window).scrollTop() < 85){
            self.article_container.css("position", "absolute");
        } else {
            self.article_container.css("position", "fixed");
            self.article_container.css("top", "5px");
        }
    };

    self.window_resized = function(){
        var width = $(window).width();
        if (self.previous_width !== width)
            return;

        // We need to adjust to the new browser width
        self.previous_width = width;
        self.datatable.fnAdjustColumnSizing();
        self.width_warning_dialog.dialog((width < 1000) ? "open" : "close");
    };

    self.initialise_shortcuts = function(){
        var doc = $(document);
        $.each(self.shortcuts(), function(keys, callback){
            doc.bind("keydown", keys, function(event){
                event.preventDefault();
                callback();
            });
        })
    };

    // TODO: Clean, comment on magic
    self.initialise_wordcount = function(){
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

    self.initialise = function(project_id, codingjob_id, coder_id){
        self.project_id = project_id;
        self.codingjob_id = codingjob_id;
        self.coder_id = coder_id;

        self.initialise_containers();
        self.initialise_buttons();
        self.initialise_dialogs();
        self.initialise_shortcuts();
        self.initialise_fields();
        self.initialise_wordcount();
    };


    return self;
})({});


/************* Storing data *************/
/*
 * For all AJAX errors, display a generic error messages. This eliminates
 * lots of boiler-plate code in functions which use AJAX calls.
 */
$(document).ajaxError(function(event, xhr, ajaxOptions) {
    var message = "An error occured while requesting: {0}. Server responded: {1} {2}.";
    message = message.f(ajaxOptions.url, xhr.status, xhr.statusText);
    $("<div>").text(message).dialog({ modal: true });
});

/*
 * Ask user to confirm quitting in the case of unsaved changes
 */
$(window).bind("beforeunload", function(){
    return annotator.modified() ? "Unsaved changes present. Continue quitting?" : undefined;
});
