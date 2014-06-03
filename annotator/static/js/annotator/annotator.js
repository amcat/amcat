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
    self.API_PAGE_SIZE = 999999;

    self.STATUS = {
        NOT_STARTED: 0,
        IN_PROGRESS: 1,
        COMPLETE: 2,
        IRRELEVANT: 9
    };

    self.STATUS_TEXT = {
        0 : "Not started",
        1 : "In progress",
        2 : "Finished",
        9 : "Irrelevant"
    };

    self.get_empty_state = function(){
        return {
            requests : null,
            coded_article_id: -1,
            coded_article: null,
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
    self.unsaved = false;

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
            self.state.coded_article.comments = $(this).val();
            self.unsaved = true;
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
        self.hide_articles_btn = $("#hide-articles-button")

        self.next_btn.click(self.select_next_article);
        self.prev_btn.click(self.select_prev_article);
        self.select_all_btn.click(self.select_all_sentences);
        self.save_btn.click(self.save);
        self.save_continue_btn.click(self.finish_and_continue);
        self.irrelevant_btn.click(self.irrelevant_and_continue);
        self.copy_btn.click(self.copy);
        self.help_btn.click(function(){ self.help_dialog.dialog("open"); });
        self.hide_articles_btn.click(self.hide_articles)

        $(".coding-part").hide();
        $(".sentence-options").hide();
        $(window).scroll(self.window_scrolled);
        $(window).resize(self.window_resized);
        $(window).trigger("resize");

    };

    self.post_record_entries = function(record_entries) {
        console.log("Sending " + record_entries.length + " entries...");
        $.post("/api/recorder/record", JSON.stringify(record_entries));
    };

    self.add_record_entry = function(record_entry) {
        self.state.recorded_events.push(record_entry);
        if (self.state.recorded_events.length >= 25) {
            var to_post = self.state.recorded_events;
            self.post_record_entries(to_post);
            self.state.recorded_events = [];
        }
    };

    self.record_event = function(e) {
        var categories = ["keywords", "description", "variable", "sentence"];
        var $target = $(e.currentTarget)
        var target_classes = $target.attr("class").split(" ");
        var target_categories = target_classes.filter(function(target_class) {
            return categories.indexOf(target_class) != -1;
        });
        
        if (target_categories.length == 0) {
            return;
        }
        var record_entry = {
            'event_type': e.type, 
            'ts': new Date(),
            'codingjob_id': self.codingjob_id,
            'article_id': self.state.coded_article.article_id
        };
        var target_category = target_categories[0];
        record_entry["category"] = target_category;

        if (target_category == "variable") {
            record_entry["target_id"] = $target.attr("data-id");
        }
        if (target_category == "sentence") {
            record_entry["target_id"] = $target.attr("id").split("-")[1];   
        }
        record_entry['selected_schema_field_id'] = self.state.selected_schema_field_id;
        self.add_record_entry(record_entry);
    };

    self.initialise_recorder_handlers = function() {
        self.state.recorded_events = [];
        $('.sentence, .keywords, .description, .variable, button, #sentence-selection')
            .on('click mouseover mouseleave', function(e) {
                self.record_event(e);
            });

    };

    self.show_unsaved_changes = function(continue_func){
        var save_btn = $(".save", self.unsaved_modal);
        var discard_btn = $(".discard", self.unsaved_modal);

        save_btn.unbind().click(function(){
            self.save({ success_callback : continue_func });
            self.unsaved_modal.modal("hide");
        });

        discard_btn.unbind().click(function(){
            self.unsaved_modal.modal("hide");
            self.unsaved = false;
            continue_func();
        });

        self.unsaved_modal.modal("show");
    };

    self.initialise_dialogs = function(){
        self.unsaved_modal = $("#unsaved-changes").modal({ show : false });
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

    /* Calls $.getJSON and returns its output, while appending ?page_size=inf
     * to the url to prevent cut-offs.*/
    self.from_api = function(url){
        return $.getJSON("{0}?page_size={1}".f(url, self.API_PAGE_SIZE));
    };

    self.hide_articles = function() {
        self.hide_articles_btn.find("i")
            .toggleClass("fa-chevron-up")
            .toggleClass("fa-chevron-down")
        if (self.article_table_container.is(':hidden')) {
            self.article_table_container.show();
            self.hide_articles_btn.attr("title", "Hide articles")
        } else {
            self.article_table_container.hide();
            self.hide_articles_btn.attr("title", "Show articles")
        }
        
    }

    /*
     * Counts currently selection of words in article.
     *
     * TODO: Cleanup
     */
    self.count = function(){
        // http://stackoverflow.com/questions/6743912/get-the-pure-text-without-html-element-by-javascript
        var sentence_re = / id="sentence-[0-9]*"/g
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
        $(".highlight", html).remove();

        $.each($(".new-paragraph", html), function(i, el){
            $(el).removeClass("new-paragraph");
        });

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
    };

    self.setup_wordcount = function(){
        $("article").mouseup(function(){
            window.setTimeout(self.count, 50);
        });
    };


    self.initialise_fields = function(){
        self.loading_dialog.text("Loading fields..").dialog("open");

        self._requests = [
            self.from_api(self.get_api_url()),
            self.from_api(self.get_api_url() + "coding_rules"),
            self.from_api(self.get_api_url() + "codebooks"),
            self.from_api(self.get_api_url() + "codingschemas"),
            self.from_api(self.get_api_url() + "codingschemafields"),
            self.from_api(self.API_URL + "coding_rule_actions")
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
                self.setup_wordcount();
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
        $("#coding").show()
        self.hide_articles();
        return table.append($.map(widgets.get_html(schemafields, null), function(widget, i){
            var schemafield = schemafields[i];
            var label = widgets.get_label_html(schemafield, widget);
            var value = self.state.article_coding.values[schemafield.id];

            if (value !== undefined){
                widgets.set_value($(widget), value);
            }

            if (schemafield.keywords)
                var nice_keywords = schemafield.keywords.split(",").join(", ");
            else
                var nice_keywords = "<i>No keywords.</i>"
            if (schemafield.description)
                var nice_description = schemafield.description
            else
                var nice_description = "<i>No description.</i>"


            return $("<tr>")
                .attr("data-id", schemafield.id)
                .attr("data-keywords", nice_keywords)
                .attr("data-description", nice_description)
                .addClass("variable")
                .append($("<td>").append(label))
                .append($("<td>").append(widget));
        }));

    };

    /*
     * Initialises table headers (sentence + fields + action) (columns)
     */
    self.initialise_sentence_codings_table = function () {
        amcat.datatables.done = true;
        var table_header = $("<tr>");

        // Used to 'steal' focus so we know we need to add another row / switch to next row
        table_header.append($("<th>"));

        self.sentence_codings_container.find("table")
            .append($("<thead>"))
            .append($("<tbody>").append(table_header));
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
        var sentence_input = $(coding_el).find("> input")
        var sentence_variables = $(coding_el).find("> td").slice(0, -1);
        self.sentence_codings_container.find("tbody").
            append($("<tr>")
                .append($("<td>")
                    .append($("<label>")
                        .append($("<u>")
                            .append("Sentence:")
                        )
                    )
                )
                .append($("<td>")
                    .append(sentence_input)
                )
                .attr('id', 'sentence-selection')
            );
        sentence_variables.each(function(i, bar) {
            var schemafield = self.sentence_schemafields[i];
            if (schemafield.keywords)
                    var nice_keywords = schemafield.keywords.split(",").join(", ");
                else
                    var nice_keywords = "<i>No keywords.</i>"
                if (schemafield.description)
                    var nice_description = schemafield.description
                else
                    var nice_description = "<i>No description.</i>"

            self.sentence_codings_container.find("tbody").
                append($("<tr>")
                    .append($("<td>")
                        .append($("<label>")
                            .append(schemafield.label)
                        )
                    )
                    .append(bar)
                    .attr("data-id", schemafield.id)
                    .attr("data-keywords", nice_keywords)
                    .attr("data-description", nice_description)
                    .addClass("variable")
                )
        })
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
        active_row.remove();
        delete self.state.codings[active_row.attr("annotator_coding_id")];
        $("input", next).first().focus();
        self.set_tab_order();
    };

    /*
     * Adds new row after currently active row, with `properties`.
     */
    self._add_row = function(properties){
        var active_row = self.get_active_row();
        var empty_coding = self.get_empty_coding(properties);
        var new_active_row;

        self.state.sentence_codings.push(empty_coding);
        active_row.after(self.get_sentence_coding_html(empty_coding));
        self.set_tab_order();

        new_active_row = active_row.nextAll(".coding").first();
        new_active_row.find(".sentence").focus();
        return new_active_row;
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
        var new_coding = self.state.codings[new_row.attr("annotator_coding_id")];
        var new_widgets = $(".widget", new_row);

        // Copy codingvalues to new row
        $.each($(".widget", active_row), function(i, widget){
            var coding_value = widgets.get_codingvalue(active_coding, active_coding.sentence, $(widget));
            new_coding.values[coding_value.field.id] = coding_value;
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

    self.parse_sentence = function(sentence){
        return {
            words: sentence.split(/ +/),
            sentence: sentence
        };
    };

    self.get_new_coding_value = function(coding, codingschemafield){
        return {
            id : null,
            coding : coding,
            field : codingschemafield,
            intval : null,
            strval : null
        }

    };

    /*
     * This function is called after a widget-value has been changed. It updates the
     * inner state to reflect the "outer" state (DOM).
     */
    self.set_coding_value = function(annotator_coding_id, codingschemafield_id, value){
        var coding = self.state.codings[annotator_coding_id];
        var codingvalue = coding.values[codingschemafield_id];
        var codingschemafield = self.models.schemafields[codingschemafield_id];

        // Create codingvalue if needed.
        if (codingvalue === undefined){
            coding.values[codingschemafield_id] = self.get_new_coding_value(coding, codingschemafield);
            return self.set_coding_value(annotator_coding_id, codingschemafield_id, value);
        }

        codingvalue.intval = null;
        codingvalue.strval = null;

        if (typeof(value) === "number") {
            codingvalue.intval = value;
        } else if (typeof(value) === "string") {
            codingvalue.strval = value;
        }

        self.unsaved = true;
    };

    /*
     * Display sentence text above currently active coding and update from to elements.
     */
    self.refresh_sentence_text = function(){
        self.sentence_codings_container.find(".sentence-text-row").remove();
        self.article_container.find(".active").removeClass("active");

        var active_row = self.get_active_row();
        var active_coding = self.get_active_sentence_coding();
        if (active_row === null) return;
        if (active_coding.sentence === null) return;

        // Display sentence text above coding
        active_row.before($("<tr>").addClass("sentence-text-row").append($("<td>")
                .attr("colspan", active_row.closest("table").find("th").size())
                .text(active_coding.sentence.sentence)));

        // Highlight sentence in article text
        self.article_container.find("#sentence-{0}".f(active_coding.sentence.id)).addClass("active");

        // Set min, max values on from/to widgets
        var sentence = self.parse_sentence(active_coding.sentence.sentence);
        var from = $(".from", active_row);
        var to = $(".to", active_row);

        from.attr("min", 0).attr("max", sentence.words.length - 2);
        to.attr("min", 1).attr("max", sentence.words.length - 1);

        var fromv = parseInt(from.val());
        if (!isNaN(fromv)){
            to.attr("min", fromv+1);
        }

        var tov = parseInt(to.val());
        if (!isNaN(tov)){
            from.attr("max", tov-1);
        }

        active_coding.start = fromv || null;
        active_coding.end = tov || null;

        // Highlight selected part
        if (isNaN(fromv) && isNaN(tov)) return;
        if (isNaN(fromv)) fromv = 0;
        if (isNaN(tov)) tov = sentence.words.length;

        var prefix = sentence.words.slice(0, fromv).join(" ");
        var middle = sentence.words.slice(fromv, tov+1).join(" ");
        var remainer = sentence.words.slice(tov+1, sentence.words.length).join(" ");

        $("td", active_row.prev()).html(
            $("<span>")
                .append($("<span>").text(prefix))
                .append($("<code>").text(middle))
                .append($("<span>").text(remainer))
        );
    };


    /* Returns (new) DOM representation of a single sentence coding */
    self.get_sentence_coding_html = function(coding){
        var coding_el = $("<tr>").addClass("coding").attr("annotator_coding_id", coding.annotator_id);

        // Add sentencenr, from and to.
        coding_el.append(widgets.sentence.get_html().val((coding.sentence === null) ? "" : coding.sentence.get_unit()));

        if(self.codingjob.unitschema.subsentences){
            coding_el.append(widgets.from.get_html().val(coding.start||""));
            coding_el.append(widgets.to.get_html().val(coding.end||""));
        }

        coding_el.append($.map(widgets.get_html(self.sentence_schemafields), function(widget){
            return $("<td>").append(widget);
        }));

        coding_el.append($("<td>").addClass("focus-stealer").focus(self.last_widget_reached));
        coding_el.on("sentence-changed", self.refresh_sentence_text);
        coding_el.find("input").focus(function(){
            $(this).closest(".coding").trigger("sentence-changed");
        });

        return coding_el;
    };

    /*
     * Mandetory validation are present to preserve a consistent database state.
     */
    self.mandetory_validate = function(){
        // Check ∀v [(v.sentence === null) => (v.intval === null && v.strval === null)]
        var codings = self.get_sentence_codings();
        for (var i=0; i < codings.length; i++){
            if (codings[i].sentence !== null) continue;

            if ($.map($.values(codings[i].values), function(cv){
                return (!self.is_empty_codingvalue(cv)) || null;
            }).length){
                return "A non-empty coding with no sentence was found.";
            }
        }

        return true;
    };

    /*
     * Checks if all codingschemarules pass.
     */
    self.validate = function(){
        var article_errors = $("." + rules.ERROR_CLASS, self.article_coding_container);
        var sentence_errors = $("." + rules.ERROR_CLASS, self.sentence_codings_container);
        var error = "An error occured while validating {0} codings. Erroneous fields have been marked red.";

        if (article_errors.length > 0){
            return error.f("article");
        } else if (sentence_errors.length > 0){
            return error.f("sentence");
        }

        return true;
    };

    self.is_empty_codingvalue = function(cv){
        return cv.intval === null && cv.strval === null;
    };

    self.is_empty_coding = function(coding){
        return all($.values(coding.values), self.is_empty_codingvalue)
    };

    /*
     * Returns 'minimised' version of given coding, which can easily be serialised.
     */
    self.pre_serialise_coding = function(coding){
        return {
            start : coding.start, end : coding.end,
            sentence_id : (coding.sentence === null) ? null : coding.sentence.id,
            values : $.map($.grep($.values(coding.values), self.is_empty_codingvalue, true), self.pre_serialise_codingvalue)
        }
    };

    self.pre_serialise_codingvalue = function(codingvalue){
        return {
            codingschemafield_id : codingvalue.field.id,
            intval : codingvalue.intval,
            strval : codingvalue.strval
        }
    };

    self.pre_serialise_coded_article = function () {
        return {
            status_id : self.state.coded_article.status,
            comments : self.state.coded_article.comments
        }
    };

    /*
     * Save codings.
     *
     * @type success_callback: function
     * @param success_callback: function called when server replied with non-error code
     * @required success_callback: no
     *
     * @type validate: boolean
     * @param validate: when true open display when validation fails
     * @default validate: false
     */
    self.save = function(options){
        if (options === undefined || options.currentTarget !== undefined) options = {};

        options = $.extend({}, {
            validate : false,
            success_callback : function(){},
            error_callback : function(){}
        }, options);

        var validate = options.validate;
        var success_callback = options.success_callback;
        var error_callback = options.error_callback;

        $(document.activeElement).blur().focus();

        // Set status to 'in progress' if current status is 'not started'
        if (self.state.coded_article.status == self.STATUS.NOT_STARTED){
            self.set_status(self.STATUS.IN_PROGRESS);
        }

        // Check whether we want to save, by first checking the mandetory checks.
        var validation = self.mandetory_validate();
        if (validation !== true){
            return self.message_dialog.text(validation).dialog("open");
        }

        // Check optional requirements
        validation = validate ? self.validate() : true;
        if (validation !== true){
            return self.message_dialog.text(validation).dialog("open");
        }

        // Send coding values to server
        self.loading_dialog.text("Saving codings..").dialog("open");
        $.post("codedarticle/{0}/save".f(self.state.coded_article_id), JSON.stringify({
            "coded_article" : self.pre_serialise_coded_article(),
            "codings" : $.map(self.get_codings(), self.pre_serialise_coding)
        })).done(function(data, textStatus, jqXHR){
            self.loading_dialog.dialog("close");

            $.pnotify({
                "title" : "Done",
                "text" : "Codings saved succesfully.",
                "type" : "success",
                "delay" : 500
            });

            self.set_column_text("status", self.STATUS_TEXT[self.state.coded_article.status]);
            self.set_column_text("comments", self.state.coded_article.comments);

            // Reset 'unsaved' state
            self.unsaved = false;

            // Change article status in table
            var td_index = self.article_table_container.find("thead th:contains('status')").index();
            var current_row = self.article_table_container.find("tr.row_selected");
            $("td:eq({0})".f(td_index), current_row).text(self.STATUS_TEXT[self.state.coded_article.status]);

            if (success_callback !== undefined && success_callback.currentTarget === undefined){
                success_callback(data, textStatus, jqXHR);
            }
        }).error(error_callback);
    };

    self.set_status = function(state){
        self.article_status_dropdown.val(state);
        self.article_status_dropdown.trigger("change");
    };

    self.save_and_continue = function () {
        self.save({ success_callback : self.select_next_article, validate : true });
    };

    self.finish_and_continue = function(){
        self.set_status(self.STATUS.COMPLETE);
        self.save_and_continue();
    };

    self.irrelevant_and_continue = function () {
        self.set_status(self.STATUS.IRRELEVANT);
        self.save_and_continue();
    };

    self._select = function(row){
        if (row.length === 0){
            self.loading_dialog.text("Last article reached, coding done!").dialog("open");
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

    /*
     * Given two sentences a and b, return if a is "greater than" than b.
     */
    self.sentence_greater_than = function(a, b){
        if (a.parnr > b.parnr) return 1;
        if (a.parnr < b.parnr) return -1;
        return a.sentnr - b.sentnr;
    };

    self.coded_article_fetched = function(coded_article, codings, sentences){
        console.log("Retrieved " + codings.length + " codings and " + sentences.length + " sentences");
        $("#lost-codes").hide();
        $("#lost-codes .triggered-by").empty();

        $.each(codings[0].results, function(i, coding){
            coding.annotator_id = self.get_new_id();
        });

        // sentences_array holds a list of ordered sentences (by sentnr, parnr)
        self.state.sentences_array = sentences[0].results;
        self.state.sentences_array.sort(self.sentence_greater_than);

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
        self.state.coded_article = coded_article[0];

        self.article_status_dropdown.val(self.state.coded_article.status).trigger("changed");
        self.article_comment_textarea.val(self.state.coded_article.comments).trigger("changed");

        var get_unit = function () {
            return "{0}.{1}".f(this.parnr, this.sentnr);
        };

        $.each(sentences, function(_, sentence){
            sentence.get_unit = get_unit.bind(sentence);
        });

        // Set buttons
        // $('#next-article-button').button("option", "disabled", row.next().length == 0);
        //$('#previous-article-button').button("option", "disabled", row.prev().length == 0);

        $("#article-comment").text(coded_article.comments || "");
        $('#article-status').find('option:contains("' + coded_article.status + '")').attr("selected", "selected");

        // Initialise coding area
        $(".coding-part").show();
        self.sentences_fetched(sentences);
        self.highlight();
        self.codings_fetched();
        self.set_tab_order();
        self.unsaved = false;

        self.initialise_recorder_handlers();
        self.loading_dialog.dialog("close");

        var container = (self.codingjob.articleschema === null) ? self.sentence_codings_container : self.article_coding_container;
        container.find("input:visible").first().focus();
        $.when.apply(undefined, [self.get_schema_field_highlighting("articleschema")]).then(self.highlight_schema_fields);
        $.when.apply(undefined, [self.get_schema_field_highlighting("unitschema")]).then(self.highlight_unit_schema_fields);

    };

    self.highlight = function(){
        console.log("Highlighting ", self.highlight_labels.length ," labels in article..");
        $("div.sentences").easymark("highlight", self.highlight_labels.join(" "));
    };

    self.get_schema_field_highlighting = function(schematype) {
        var base_highlighter_url = "/api/highlighter/" + schematype;
        var article_id = self.state.coded_article.article_id;
        var highlighter_url = "{0}?codingjob_id={1}&article_id={2}".f(base_highlighter_url, self.codingjob_id, article_id);
        return $.getJSON(highlighter_url);
    }

    self.highlight_unit_schema_fields = function(highlighting) {
        $("#unitcoding-table").find("tr")
            .unbind("click")
            .bind("click", function() {
                var that = this;
                self.state.selected_schema_field_id = $(that).attr('data-id');
                var field_index = $(this).index() - 1;
                var sentence_id = 0;
                var keywords = $(that).attr("data-keywords");
                if (typeof keywords === 'undefined')
                    return;
                var description = $(that).attr("data-description");
                $('#coding-details .keywords > div').html(keywords);
                $('#coding-details .description > div').html(description);
                $(".coding-part tr").css('background-color', 'white');
                $(that).css('background-color', '#9FAFD1');
                $.each(highlighting, function(pIndex, sentences) {
                    $.each(sentences, function(sIndex, fields) {
                        sentence_id += 1;
                        var yellow = Math.round(fields[field_index] * 255);
                        $("#sentence-{0}".f(sentence_id)).css("background-color", "rgb(255,255,{0})".f(yellow));
                    })
                })
            })
    }

    self.highlight_schema_fields = function(highlighting) {
        self.article_coding_container.find("tr")
            .unbind("click")
            .bind("click", function() {
                var that = this;
                var field_index = $(this).index();
                if (self.state.selected_schema_field == field_index) {
                    return;
                }
                self.state.selected_schema_field_id = $(that).attr('data-id'); 
                self.state.selected_schema_field = field_index;
                var keywords = $(that).attr("data-keywords")
                var description = $(that).attr("data-description")
                $('#coding-details .keywords > div').html(keywords);
                $('#coding-details .description > div').html(description);
                $(".coding-part tr").css('background-color', 'white');
                $(that).css('background-color', '#9FAFD1');
                var sentence_id = 0;
                $.each(highlighting, function(pIndex, sentences) {
                    $.each(sentences, function(sIndex, fields) {
                        sentence_id += 1;
                        var yellow = Math.round(fields[field_index] * 255);
                        $("#sentence-{0}".f(sentence_id)).css("background-color", "rgb(255,255,{0})".f(yellow))
                    })
                })
            })
    }

    /*
     * Resets internal state and fetches new coded article, which consists of:
     *  - coded_article
     *  - codings + values
     *  - sentences
     * coded_article_fetched is called when requests finished
     */
    self.get_article = function(coded_article_id){
        var base_url = self.get_api_url() + "coded_articles/" + coded_article_id + "/";

        self.state = self.get_empty_state();
        self.sentence_codings_container.find("table tbody").html("");
        self.state.coded_article_id = coded_article_id;

        self.state.requests = [
            self.from_api(base_url),
            self.from_api(base_url + "codings"),
            self.from_api(base_url + "sentences")
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

    /*
     * Retrieve all coding objects contained in `container`. If `container` is not given,
     * return all codings.
     *
     * @type container: DOM element
     */
    self.get_codings = function(container){
        if (container === undefined){
            return $.merge([self.get_article_coding()], self.get_sentence_codings());
        }

        return $.map($(container).find(".coding"), function(coding_el){
            return self.state.codings[$(coding_el).attr("annotator_coding_id")];
        });
    };

    /*
     * Return all codings which are not the article coding.
     */
    self.get_sentence_codings = function(){
        // Note: this function depends on the presence of DOM elements. This is due to
        // a bug in earlier versions which duplicated codings. The only reliable way for
        // now is to match codings with DOM elements.
        return $.grep(self.get_codings(self.sentence_codings_container), self.is_empty_coding, true);
    };

    /*
     * Return article coding
     */
    self.get_article_coding = function(){
        // Note: this function depends on the presence of DOM elements. This is due to
        // a bug in earlier versions which duplicated codings. The only reliable way for
        // now is to match codings with DOM elements.
        return self.get_codings(self.article_coding_container)[0];
    };

    self.get_empty_coding = function(properties){
        var empty_coding = $.extend({
            coded_article : self.state.coded_article,
            sentence: null,
            start: null,
            end: null
        }, properties, {
            id: null,
            annotator_id : self.get_new_id(),
            values : {}
        });

        self.state.codings[empty_coding.annotator_id] = empty_coding;
        return empty_coding;
    };

    self.is_article_coding = function(coding){
        return coding.sentence === null;
    };


    /******** EVENTS *******/
    // TODO: Only initialise article coding html once.
    self.codings_fetched = function(){
        self.state.sentence_codings = $.grep($.values(self.state.codings), self.is_article_coding, true);
        self.state.sentence_codings.sort(function(a,b){
            return self.sentence_greater_than(a.sentence, b.sentence);
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
            var _html = $('<div />').attr('id', 'sentence-' + s.id).addClass('sentence');
            if (s.parnr != prev_parnr) {
                _html.addClass('new-paragraph');
            }
            if (s.get_unit() == '1.1') {
                _html.append($('<h2 />').text(s.sentence));
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

    /*
     * Change the contents of the column with `column_name` in the currently active row.
     */
    self.set_column_text = function(column_name, value){
        var column = self.article_table_container.find("thead").find("th:contains('{0}')".f(column_name));
        var column_index = column.parent().children().index(column);
        var cell = self.article_table_container.find("tr.row_selected").children(":eq({0})".f(column_index));
        cell.text(value);
    };

    self.article_status_changed = function(){
        self.state.coded_article.status = parseInt($(this).val());
        self.unsaved = true;
    };

    self.datatables_row_clicked = function(row){
        if(row["0"]["_DT_RowIndex"] === undefined)
            return

        if(self.unsaved){
            return self.show_unsaved_changes((function(){
                self.datatables_row_clicked.bind(this)(row);
            }).bind(this));
        }

        // Get article id which is stored in the id-column of the datatable
        var coded_article_id = parseInt(row.children('td:first').text());
        self.datatable.find(".row_selected").removeClass("row_selected");
        self.datatable.parent().scrollTo(row, {offset: -50});

        self.get_article(coded_article_id);
        row.addClass("row_selected");
    };

    self.window_scrolled = function(){
        // if ($(window).scrollTop() < 85){
        //     self.article_container.css("position", "absolute");
        // } else {
        //     self.article_container.css("position", "fixed");
        //     self.article_container.css("top", "5px");
        // }
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

    self.on_unload = function(){
        if (!self.unsaved) return;
        return "You have unsaved changes. Continue?"
    };

    self.initialise = function(project_id, codingjob_id, coder_id, language_id){
        $("#lost-codes").hide();

        self.project_id = project_id;
        self.codingjob_id = codingjob_id;
        self.coder_id = coder_id;
        self.language_id = language_id;

        self.initialise_containers();
        self.initialise_buttons();
        self.initialise_dialogs();
        self.initialise_shortcuts();
        self.initialise_fields();
        self.initialise_wordcount();

        window.onbeforeunload = self.on_unload;
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
