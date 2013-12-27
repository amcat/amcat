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

// Workaround: focus events don't carry *Key properties, so we don't
// know for sure if shift is pressed.
shifted = false;
$(document).keydown(function(event){
    shifted = event.shiftKey;
});

$(document).keyup(function(){
    shifted = false;
});


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
            deleted_codings: [],
            modified_codings: [],
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
        self.article_table_container = $("#article-table-container");
        self.article_container = $("article");
        self.article_status_dropdown = $("#article-status").change(self.article_status_changed);
        self.article_comment_textarea = $("#article-comment").change(function(){
            self.article_coding.comments = $(this).val();
        });
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
        self.save_continue_btn.click(self.finish_and_continue);
        self.irrelevant_btn.click(self.irrelevant_and_continue);
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

        // Fill status combobox
        $.each(self.STATUS, function(label, value){
            self.article_status_dropdown.append(
                $("<option>").attr("value", value).text(label)
            );
        });


        $.when.apply(undefined, self._requests).then(function (codingjob, rules, codebooks, schemas, schemafields, actions) {
                // Check if all request completed successfully. (If not, an
                // error is already thrown, but we need not continue processing
                // the data.
                if (!all(self._requests, function (request) {
                    return request.statusText === "OK";
                })) {
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
    self.shortcuts = function(){
        return {
        "ctrl+s" : self.save_btn.trigger.bind(self.save_btn, "click"),
        "ctrl+down" : self.add_row,
        "ctrl+shift+down" : self.add_next_sentence_row,
        "shift+down" : self.copy_row,
        "ctrl+shift+d": self.delete_row,
        "ctrl+i" : self.irrelevant_btn.trigger.bind(self.irrelevant_btn, "click"),
        "ctrl+d" : self.save_continue_btn.trigger.bind(self.save_continue_btn, "click")
    }};

    /******** PUBLIC FUNCTIONS *******/
    /* Returns true if a coding was modified (article or sentence) */
    self.modified = function(){
        return self.sentence_codings_modified() | self.state.article_coding_modified;
    };

    self.sentence_codings_modified = function(){
        return !!(self.state.deleted_codings.length || self.state.modified_codings.length);
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
            var schemafield = schemafields[i];
            var label = widgets.get_label_html(schemafield, widget);
            var value = self.state.article_coding.values[schemafield.id];

            if (value !== undefined){
                widgets.set_value($(widget), value);
            }

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

        // Used to 'steal' focus so we know we need to add another row / switch to next row
        table_header.append($("<th>"));

        self.sentence_codings_container.find("table")
            .append($("<thead>").append(table_header))
            .append($("<tbody>"));
    };


    self.initialise_sentence_codings = function () {
        if (self.codingjob.unitschema === null) return $("<div>");

        if (self.state.sentence_codings.length === 0){
            var empty_coding = self.get_empty_coding();
            self.state.sentence_codings.push(empty_coding);
        }

        $.map(self.state.sentence_codings, self.append_sentence_coding);
    };

    /*
     * Create new row, and append it to existing table
     */
    self.append_sentence_coding = function(coding){
        var coding_el = self.get_sentence_coding_html(coding);
        self.sentence_codings_container.find("tbody").append(coding_el);
        self.set_sentence_codingvalues(coding_el, coding.values||[], coding.sentence);
        self.set_tab_order();
    };

    self.set_sentence_codingvalues = function(coding_el, values, sentence){
        var widget;
        $.each(values, function(_, codingvalue){
            widget = widgets.find(codingvalue.field, coding_el);
            widgets.set_value(widget, codingvalue);
        });

        if (sentence !== undefined && sentence !== null){
            widgets.sentence.set_value($(".sentence", coding_el), sentence);
        }
    };

    self.delete_row = function(){
        var active_row = self.get_active_row();
        var active_coding = self.get_active_sentence_coding();
        if (active_row === null) return;

        // Select a row which need to be focused after the
        // deletion of the currently active row.
        var next = active_row.next();
        if (!next.length){
            // No next row, set previous row
            next = active_row.prevAll(".coding").first();
        }

        if (!next.length){
            // No previous row either
            next = self._add_row({});
        }

        // Register deleted coding
        self.state.deleted_codings.push(active_coding);
        remove_from_array(self.state.modified_codings, active_coding);
        active_row.remove();
        $("input", next).first().focus();
        self.set_tab_order();
    };

    /*
     * Adds new row after currently active row, with `properties`.
     */
    self._add_row = function(properties){
        var active_row = self.get_active_row();
        var empty_coding = self.get_empty_coding(properties);
        self.state.sentence_codings.push(empty_coding);
        active_row.after(self.get_sentence_coding_html(empty_coding));
        self.set_tab_order();
        active_row.next().find(".sentence").focus();
        return active_row.next();
    };

    /*
     * Add new row after current active one, and copy its contents
     */
    self.copy_row = function(){
        var active_coding = self.get_active_sentence_coding();
        var active_row = self.get_active_row();
        if (active_coding === null) return;

        // Add new (empty) coding
        var new_row = self._add_row(active_coding);
        var new_widgets = $(".widget", new_row);

        // Copy codingvalues to new row
        $.each($(".widget", active_row), function(i, widget){
            var coding_value = widgets.get_codingvalue(active_coding, active_coding.sentence, $(widget));
            widgets.set_value($(new_widgets.get(i)), coding_value);
        });
    };

    /*
     * Add new row after currently active row. Does nothing if no row is active
     */
    self.add_row = function(event){
        var active_coding = self.get_active_sentence_coding();
        if (active_coding === null) return;
        return self._add_row({ sentence : active_coding.sentence });
    };

    /*
     * Adds a row after currently active row, and copies its sentence.
     */
    self.add_next_sentence_row = function(){
        var coding = self.get_active_sentence_coding();
        if (coding === null) return;

        var sentence_index = self.state.sentences_array.indexOf(coding.sentence);
        if (sentence_index + 1 === self.state.sentences_array.length){
            // This was the last sentences, just use previous one?
            sentence_index -= 1;
        }

        self._add_row({
            sentence : self.state.sentences_array[sentence_index + 1]
        });
    };

    self.get_active_row = function(){
        var focused = $(document.activeElement);

        if (!focused.closest("#unitcoding-table").length){
            // No sentence activated.
            return null;
        }

        var coding = focused.closest("tr.coding");
        return (coding.length ? coding : null);
    };

    self.get_active_sentence_coding = function(){
        var active_row = self.get_active_row();
        if (active_row === null) return null;
        return self.state.codings[active_row.attr("annotator_coding_id")];
    };

    /*
     * Last widget reached, and TAB was pressed. We need to either add a row
     * or move to the next one available.
     */
    self.last_widget_reached = function(event){
        var row = $(event.currentTarget).closest("tr");

        if (shifted){
            // We need to go back, do nothing!
            $(event.currentTarget).prev().find("input").first().focus();
            return;
        }

        var empty_coding = self.get_empty_coding();
        self.state.sentence_codings.push(empty_coding);

        if (row.next().length === 0){
            self.append_sentence_coding(empty_coding);
        }

        row.next().find("input.sentence").focus();
    };

    /*
     * Display sentence text above currently active coding.
     */
    self.refresh_sentence_text = function(){
        self.sentence_codings_container.find(".sentence-text-row").remove();
        var active_row = self.get_active_row();
        var active_coding = self.get_active_sentence_coding();
        if (active_row === null) return;
        if (active_coding.sentence === null) return;

        active_row.before($("<tr>").addClass("sentence-text-row").append($("<td>")
                .attr("colspan", active_row.closest("table").find("th").size())
                .text(active_coding.sentence.sentence)));
    };


    /* Returns (new) DOM representation of a single sentence coding */
    self.get_sentence_coding_html = function(coding){
        var coding_el = $("<tr>").addClass("coding").attr("annotator_coding_id", coding.annotator_id);
        coding_el.append(widgets.sentence.get_html().val((coding.sentence === null) ? "" : coding.sentence.get_unit()));
        coding_el.append($.map(widgets.get_html(self.sentence_schemafields), function(widget){
            return $("<td>").append(widget);
        }));

        coding_el.append($("<td>").addClass("focus-stealer").focus(self.last_widget_reached));
        coding_el.find("input").focus(self.refresh_sentence_text);

        return coding_el;
    };

    self.select_all_sentences = function () {

    };

    self.validate = function(){
        var article_errors = $("." + rules.ERROR_CLASS, self.article_coding_container);
        var sentence_errors = $("." + rules.ERROR_CLASS, self.sentence_codings_container);
        var error = "An error occured while validating {0} codings. Erroneous fields have been marked red.";

        if (article_errors.length > 0){
            return error.f("article");
        } else if (sentence_errors.length > 0){
            return error.f("sentence");
        }

        // Check ∀v [(v.sentence === null) => (v.intval === null && v.strval === null)]
        var coding_values;
        var codings = $(".coding", self.sentence_codings_container);
        for (var i=0; i < codings.length; i++){
            coding_values = widgets._get_codingvalues($(codings[i]));
            if (any(coding_values, function(v){
                return (v.sentence === null && (v.intval !== null || v.strval !== null));
            })){
                return "A non-empty coding with no sentence was found."
            }
        }

        return true;
    };

    self.is_empty_coding = function(row){

    };

    /*
     * Returns 'minimised' version of given coding, which can easily be serialised.
     */
    self.pre_serialise_coding = function(coding, codingvalues){
        codingvalues = $.grep(codingvalues, function(v){ return v.coding == coding });

        console.log(self.state.article_coding.status);
        return {
            sentence_id : (coding.sentence === null) ? null : coding.sentence.id,
            status_id : self.state.article_coding.status,
            comments : coding.comments,
            values : $.map(codingvalues, self.pre_serialise_codingvalue)
        }
    };

    self.pre_serialise_codingvalue = function(codingvalue){
        return {
            codingschemafield_id : codingvalue.field.id,
            intval : codingvalue.intval,
            strval : codingvalue.strval
        }
    };

    self.save = function(success_callback){
        $(document.activeElement).blur().focus();

        // Get codingvalues
        var article_coding_values = widgets.get_coding_values(self.article_coding_container);
        var sentence_coding_values = widgets.get_coding_values(self.sentence_codings_container);
        sentence_coding_values = $.grep(sentence_coding_values, function(cv) { return cv.sentence !== null; });

        // Get sentence codings (ignore codings without a sentence)
        var sentence_codings = $.grep(self.state.sentence_codings, function(sc){ return sc.sentence !== null; })

        // Check whether we want to save.
        var validation = self.validate();
        if (validation !== true){
            return self.message_dialog.text(validation).dialog("open");
        }

        // Send coding values to server
        self.loading_dialog.text("Saving codings..").dialog("open");
        $.post("article/{0}/save".f(self.state.coded_article_id), JSON.stringify({
            "article_coding" : self.pre_serialise_coding(self.state.article_coding, article_coding_values),
            "sentence_codings" : $.map(sentence_codings, function(coding){
                return self.pre_serialise_coding(coding, sentence_coding_values);
            })
        }), function(data, textStatus, jqXHR){
            self.loading_dialog.dialog("close");

            if (success_callback !== undefined && success_callback.currentTarget === undefined){
                success_callback(data, textStatus, jqXHR);
            }
        });
    };

    self.set_state = function(state){
        self.article_status_dropdown.val(state);
        self.article_status_dropdown.trigger("change");
    };

    self.save_and_continue = function () {
        self.save(self.select_next_article);
    };

    self.finish_and_continue = function(){
        self.set_state(self.STATUS.COMPLETE);
        self.save_and_continue();
    };

    self.irrelevant_and_continue = function () {
        self.set_state(self.STATUS.IRRELEVANT);
        self.save_and_continue();
    };

    self._select = function(row){
        if (row.length === 0){
            self.loading_dialog.text("Coding done!");
            return;
        }

        row.trigger("click");
    };

    self.select_next_article = function () {
        self._select(self.article_table_container.find(".row_selected").next());
    };

    self.select_prev_article = function () {
        self._select(self.article_table_container.find(".row_selected").prev());
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

        self.state.sentences_array = sentences[0].results;
        codings = map_ids(codings[0].results, "annotator_id");
        sentences = map_ids(sentences[0].results);
        resolve_ids(codings, sentences, "sentence");

        $.each(codings, function(_, coding){
            coding.values = map_ids(coding.values, "field");
            resolve_ids(coding.values, self.models.schemafields, "field");

            $.each(coding.values, function(_, value){
                value.coding = coding;
            });
        });

        self.state.sentences = sentences;
        self.state.codings = codings;
        self.state.coded_article = article;

        // Determine coding status (highest counts)
        var status = Math.max.apply(null, $.map(self.state.codings, function(coding){ return coding.status; }));
        self.article_status_dropdown.val(status).trigger("changed");

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
        $(".coding-part").show();
        self.sentences_fetched(sentences);
        self.highlight();
        self.codings_fetched();
        self.set_tab_order();

        self.loading_dialog.dialog("close");

        var container = (self.codingjob.articleschema === null) ? self.sentence_codings_container : self.article_coding_container;
        container.find("input:visible").first().focus();
    };

    self.highlight = function(){
        console.log("Highlighting ", self.highlight_labels.length ," labels in article..");
        $("div.sentences").easymark("highlight", self.highlight_labels.join(" "));
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
        self.sentence_codings_container.find("table tbody").html("");
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

    self.get_empty_coding = function(properties){
        var empty_coding = $.extend({
            annotator_id: self.get_new_id(),
            id: null,
            article: self.state.coded_article,
            sentence: null,
            comments: null,
            codingjob: self.codingjob,
            values : {} // Included to be consistent with AJAX data
        }, properties);

        self.state.codings[empty_coding.annotator_id] = empty_coding;
        return empty_coding;
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
            self.state.article_coding = self.get_empty_coding();
            self.article_status_dropdown.trigger("change");
        } else {
            self.state.article_coding = article_coding[0];
        }

        // Create html content
        self.article_coding_container.html(self.get_article_coding_html());
        rules.add(self.article_coding_container);

        self.initialise_sentence_codings();
        rules.add(self.sentence_codings_container);
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

    /*
     * Sets tabindex-properties to all focusable elements, which are:
     *  - comment textarea
     *  - article codingvalues (visible input elements)
     *  - sentence codingvalues (visible input elements)
     *  - additional "focus stealer" at the end of each codingrow, which is used to determine when
     *    a user reached the end of a coding (and we need to add another coding).
     */
    self.set_tab_order = function(){
        var tabindex = 1;

        var set_tabindex = function(_, el) {
            $(el).attr("tabindex", tabindex);
            tabindex += 1;
        };

        $.each(self.article_comment_textarea, set_tabindex);
        $.each($("input:visible", self.article_coding_container), set_tabindex);
        $.each($("tbody tr", self.sentence_codings_container), function(_, row){
            $.each($("input:visible, .focus-stealer", row), set_tabindex);
        });
    };

    self.article_status_changed = function(){
        self.state.article_coding.status = parseInt($(this).val());

        // Update article table. This is fugly, sorry..
        var status_column = self.article_table_container.find("thead").find("td:contains('status')");
        var status_column_index = status_column.parent().children().index(status_column);
        var status_cell = self.article_table_container.find("tr.row_selected").children(":eq({0})".f(status_column_index-1));

        var status_text;
        $.each(self.STATUS, function(text, id){
            if (self.state.article_coding.status === id){
                status_text = text;
                return false;
            }
        });

        status_cell.text(status_text);
    };

    self.datatables_row_clicked = function(row){
        // Get article id which is stored in the id-column of the datatable
        var article_id = parseInt(row.children('td:first').text());
        self.datatable.find(".row_selected").removeClass("row_selected");
        self.datatable.parent().scrollTo(row, {offset: -50});
        self.get_article(article_id);
        row.addClass("row_selected");
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
                callback(event);
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
