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

// Workaround: focus events don't carry *Key properties, so we don't
// know for sure if shift is pressed.
shifted = false;

require(["jquery"], function($){
    $(document).keydown(function(event){
        shifted = event.shiftKey;
    });

    $(document).keyup(function(){
        shifted = false;
    });
});

// TODO: Remove annotator as global variable. At the moment widgets.js, autoomplete.js still need it.
annotator = null;


define([
    "jquery",
    "annotator/widgets",
    "annotator/autocomplete",
    "annotator/rules",
    "pnotify",
    "clipboard",
    "jquery.highlight",
    "annotator/functional",
    "annotator/utils",
    "jquery.hotkeys",
    "jquery.scrollTo",
    "bootstrap"
    ], function($, widgets, autocomplete, rules, PNotify, Clipboard){
    var self = {};
    annotator = self;

    self.values = function(obj) {
        return $.map(obj, function(value, _) {
            return value;
        });
    };

    self.log = function(data){
        var date = new Date();
        var datetime = date.toUTCString().split(" GMT")[0];
        var millis = date.getUTCMilliseconds().toString();

        if (millis.length === 1){
            millis = "00" + millis;
        } else if (millis.length === 2){
            millis = "0" + millis;
        }

        var currentDate = "[{0}:{1}]".f(datetime, millis);
        console.log(currentDate, data);
    };


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

    self.get_empty_state = function get_empty_state(){
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

    self.SCROLL_TIMEOUT = 100;
    self.scroll_timeout = null;
    self.last_scroll = null;

    /* Containers & dialogs. These can only be set if DOM is ready. */
    self.initialise_containers = function initialise_containers(){
        self.article_coding_container = $("#article-coding");
        self.sentence_codings_container = $("#unitcoding-table-part");
        self.article_table_container = $("#article-table-container");
        self.article_container = $("article");
        self.article_status_dropdown = $("#article-status").change(self.article_status_changed);
        self.article_comment_textarea = $("#article-comment").change(function(){
            self.state.coded_article.comments = $(this).val();
            self.set_unsaved();
        });
    };

    self.initialise_buttons = function initialise_buttons(){
        self.next_btn = $("#next-article-button");
        self.prev_btn = $("#previous-article-button");
        self.select_all_btn = $("#select-all-sentences-button");
        self.save_btn = $(".save-button");
        self.save_continue_btn = $(".save-continue-button");
        self.irrelevant_btn = $(".irrelevant-button");
        self.delete_btn = $("#delete-button");
        self.netviz_btn = $(".copy-to-netviz");
        self.netviz_clipboard_btn = new Clipboard("#copy-to-netviz-clipboard");

        self.next_btn.click(self.select_next_article);
        self.prev_btn.click(self.select_prev_article);
        self.select_all_btn.click(self.select_all_sentences);
        self.save_btn.click(self.save);
        self.save_continue_btn.click(self.finish_and_continue);
        self.irrelevant_btn.click(self.irrelevant_and_continue);
        self.netviz_btn.click(self.copy_to_netviz);

        self.netviz_clipboard_btn.on('success', self.copy_to_netviz_success);
        self.netviz_clipboard_btn.on('error', self.copy_to_netviz_error);

        $("#editor").hide();
        $(".sentence-options").hide();
    };

    self.set_unsaved = function set_unsaved (bool) {
        self.unsaved = (bool === undefined) ? true : bool;
        var icon = self.save_btn.find(".glyphicon");
        icon.removeClass("glyphicon-floppy-disk glyphicon-floppy-saved");
        icon.addClass("glyphicon-floppy-" + ((self.unsaved) ? "disk" : "saved"));

        if (self.unsaved){
            self.save_btn.removeClass("disabled");
        } else {
            self.save_btn.addClass("disabled");
        }
    };

    self.show_unsaved_changes = function show_unsaved_changes(continue_func){
        var save_btn = $(".save", self.unsaved_modal);
        var discard_btn = $(".discard", self.unsaved_modal);

        save_btn.unbind().click(function(){
            self.save({ success_callback : continue_func });
            self.unsaved_modal.modal("hide");
        });

        discard_btn.unbind().click(function(){
            self.unsaved_modal.modal("hide");
            self.set_unsaved(false);
            continue_func();
        });

        self.unsaved_modal.modal("show");
    };

    self.show_loading = function show_loading(text){
        self.loading_dialog.modal("hide");
        self.loading_dialog.find(".modal-body p").text(text);
        self.loading_dialog.modal("show");
    };

    self.hide_loading = function hide_loading(){
        self.loading_dialog.modal("hide");
    };

    self.show_message = function show_message(title, message){
        self.message_dialog.find(".modal-title").text(title);
        self.message_dialog.find(".modal-body p").text(message);
        self.message_dialog.modal("show");
    };

    self.hide_message = function hide_message(){
        self.message_dialog.modal("hide");
    };

    self.initialise_dialogs = function initialise_dialogs(){
        self.unsaved_modal = $("#unsaved-changes").modal({ show : false });
        self.loading_dialog = $("#loading").modal({show : false, keyboard : false});
        self.message_dialog = $("#message").modal({ show : false });
        self.netviz_dialog = $("#copy-to-netviz-dialog").modal({ show : false });
    };

    /* Calls $.getJSON and returns its output, while appending ?page_size=inf
     * to the url to prevent cut-offs.*/
    self.from_api = function from_api(url){
        return $.getJSON("{0}?page_size={1}".f(url, self.API_PAGE_SIZE));
    };
    

    self.display_lost_code = function(code_id, code_value){
        var lostCodes = $('#lost-codes');
        if(lostCodes.hasClass("dont-show")){
            return;
        }
        var triggeredBy = lostCodes.find('.triggered-by');
        var text = "{0}: {1}".format(code_id, code_value);
        if(triggeredBy.text() !== ""){
            text = triggeredBy.text() + ", " + text;
        }
        triggeredBy.text(text);
        lostCodes.show();
    };
    /*
     * Counts currently selection of words in article.
     *
     * TODO: Cleanup
     */
    self.count = function count(){
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

    self.setup_wordcount = function setup_wordcount(){
        $("article").mouseup(function(){
            window.setTimeout(self.count, 50);
        });
    };


    self.initialise_fields = function initialise_fields(){
        self.show_loading("Loading fields..")

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
                $("<option>").attr("value", value).text(self.STATUS_TEXT[value])
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
                self.hide_loading();
            }
        );

    };

    /******** KEYBOARD SHORTCUTS *******/
    self.shortcuts = function shortcuts(){
        return {
        "ctrl_s" : self.save_btn.first().trigger.bind(self.save_btn.first(), "click"),
        "ctrl_down" : self.add_row,
        "ctrl_shift_down" : self.add_next_sentence_row,
        "shift_down" : self.copy_row,
        "ctrl_shift_d": self.delete_row,
        "ctrl_i" : self.irrelevant_btn.first().trigger.bind(self.irrelevant_btn.first(), "click"),
        "ctrl_d" : self.save_continue_btn.first().trigger.bind(self.save_continue_btn.first(), "click"),
        "ctrl_del" : self.delete_codingvalue
    }};

    /******** PUBLIC FUNCTIONS *******/
    /* Returns true if a coding was modified (article or sentence) */
    self.modified = function modified(){
        return self.unsaved;
    };

    /* Returns absolute url pointing to this codingjob (slash-terminated)  */
    self.get_api_url = function get_api_url(){
        return "{0}projects/{1}/codingjobs/{2}/".f(self.API_URL, self.project_id, self.codingjob_id);
    };

    /* Returns (new) DOM representation of the articlecoding */
    self.get_article_coding_html = function get_article_coding_html(){
        var schemafields = self.article_schemafields;
        var table = $("<div>")
            .attr("annotator_coding_id", self.state.article_coding.annotator_id)
            .addClass("coding");

        return table.append($.map(widgets.get_html(schemafields, null), function(widget, i){
            var schemafield = schemafields[i];
            var label = widgets.get_label_html(schemafield, widget);
            var value = self.state.article_coding.values[schemafield.id];

            if (value !== undefined){
                widgets.set_value($(widget), value);
            }

            return $("<div>").addClass("row")
                .append($("<div>").addClass("col-md-3").append(label))
                .append($("<div>").addClass("col-md-9").append(widget));
        }));
    };

    /*
     * Initialises table headers (sentence + fields + action) (columns)
     */
    self.initialise_sentence_codings_table = function initialise_sentence_codings_table () {
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
            .append($("<tbody id='sentence-codings-parent'>"));

    };


    self.initialise_sentence_codings = function initialise_sentence_codings () {
        if (self.codingjob.unitschema === null) return $("<div>");

        if (self.state.sentence_codings.length === 0){
            var empty_coding = self.get_empty_coding();
            self.state.sentence_codings.push(empty_coding);
        }

        $.map(self.state.sentence_codings, self.append_sentence_coding);
        self.set_tab_order();
    };

    /*
     * Create new row, and append it to existing table. Caller is responsible
     * for calling set_tab_order() after execution.
     */
    self.append_sentence_coding = function append_sentence_coding(coding){
        var coding_el = self.get_sentence_coding_html(coding);
        self.sentence_codings_container.find("tbody").append(coding_el);
        self.set_sentence_codingvalues(coding_el, coding.values||[], coding.sentence);
    };

    self.set_sentence_codingvalues = function set_sentence_codingvalues(coding_el, values, sentence){
        var widget;
        $.each(values, function(_, codingvalue){
            if(codingvalue.field === undefined){
                self.display_lost_code(codingvalue.id, codingvalue.strval || codingvalue.intval); 
            }
            else{
                widget = widgets.find(codingvalue.field, coding_el);
                widgets.set_value(widget, codingvalue);
            }
        });

        if (sentence !== undefined && sentence !== null){
            widgets.sentence.set_value($(".sentence", coding_el), sentence);
        }
    };

    self.delete_row = function delete_row(){
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
    self._add_row = function _add_row(properties){
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

    self.show_netviz_dialog = function show_netviz_dialog(csv){
        self.netviz_dialog.find("textarea").val(csv);
        self.netviz_dialog.modal("show");
    };

    self.copy_to_netviz_success = function copy_to_netviz_success(e){
        new PNotify({
            "type": "info",
            "text": "NETviz data copied to clipboard.",
            "delay": 5000
        });

        e.clearSelection();
    };

    self.copy_to_netviz_error = function copy_to_netviz_error(){
        new PNotify({
            "type": "error",
            "text": "Failed to copy data to clipboard. Please use CTRL+C.",
            "delay": 15000
        })

    };

    /**
     * Copy sentence codings to tabular format (for netviz)
     */
    self.copy_to_netviz = function copy_to_netviz(){
        // Create index from id -> index
        var schemafields = new Map();
        $.each(self.sentence_schemafields, function(i, schemafield){
            schemafields.set(schemafield.id, i);
        });


        // Create CSV file as string
        var csv = $.map(self.get_sentence_codings(), function(coding){
            var values = new Array(self.sentence_schemafields.length).fill("");
            $.each(coding.values, function(_, scoding){
                var i = schemafields.get(scoding.field.id);
                var sf = self.sentence_schemafields[i];
                values[i] = (sf.codebook ? sf.codebook.codes[scoding.intval].label :
                    (sf.fieldtype == 9 ? String(scoding.intval / 10) :
                    ((scoding.intval === null) ? (scoding.strval || "") : String(scoding.intval))))
            });

            // We're returning a double array on purpose: map stupidly chains..
            return values.map(function(value){
                // Escape value for use in CSV
                if (value.indexOf('"') !== -1){
                    value.replace('"', '""');
                }

                if (value.indexOf(',') !== -1){
                    value = '"' + value + '"';
                }

                return value;
            }).join();
        }).join("\n");

        var header = self.sentence_schemafields.map(function(f) {return f.label;});
        csv = header.join(",") + "\n" + csv;

        // Pop up dialog allowing the user to copy the CSV
        self.show_netviz_dialog(csv);
    };

    /*
     * Add new row after current active one, and copy its contents
     */
    self.copy_row = function copy_row(){
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
    self.add_row = function add_row(event){
        var active_coding = self.get_active_sentence_coding();
        if (active_coding === null) return;
        return self._add_row({ sentence : active_coding.sentence });
    };

    /*
     * Adds a row after currently active row, and copies its sentence.
     */
    self.add_next_sentence_row = function add_next_sentence_row(){
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

    self.get_active_row = function get_active_row(){
        var focused = $(document.activeElement);

        if (!focused.closest("#unitcoding-table").length){
            // No sentence activated.
            return null;
        }

        var coding = focused.closest("tr.coding");
        return (coding.length ? coding : null);
    };

    self.get_active_sentence_coding = function get_active_sentence_coding(){
        var active_row = self.get_active_row();
        if (active_row === null) return null;
        return self.state.codings[active_row.attr("annotator_coding_id")];
    };

    /*
     * Last widget reached, and TAB was pressed. We need to either add a row
     * or move to the next one available.
     */
    self.last_widget_reached = function last_widget_reached(event){
        var row = $(event.currentTarget).closest("tr");
        var active_coding = self.get_active_sentence_coding();

        if (shifted){
            // We need to go back, do nothing!
            $(event.currentTarget).prev().find("input").first().focus();
            return;
        }

        var empty_coding = self.get_empty_coding({ sentence : active_coding.sentence });
        self.state.sentence_codings.push(empty_coding);

        if (row.next().length === 0){
            self.append_sentence_coding(empty_coding);
            self.set_tab_order();
        }

        row.next().find("input.sentence").focus();
    };

    self.parse_sentence = function parse_sentence(sentence){
        return {
            words: sentence.split(/ +/),
            sentence: sentence
        };
    };

    self.get_new_coding_value = function get_new_coding_value(coding, codingschemafield){
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
    self.set_coding_value = function set_coding_value(annotator_coding_id, codingschemafield_id, value){
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

        self.set_unsaved();
    };

    /*
     * Display sentence text above currently active coding and update from to elements.
     */
    self.refresh_sentence_text = function refresh_sentence_text(){
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
    self.get_sentence_coding_html = function get_sentence_coding_html(coding){
        var coding_el = $("<tr class='coding'>").attr("annotator_coding_id", coding.annotator_id);

        // Add sentencenr, from and to.
        var sentence_td = $("<td>");
        sentence_td.append(widgets.sentence.get_html().val((coding.sentence === null) ? "" : coding.sentence.get_unit()));

        if(self.codingjob.unitschema.subsentences){
            sentence_td.append(widgets.from.get_html().val(coding.start||""));
            sentence_td.append(widgets.to.get_html().val(coding.end||""));
        }

        coding_el.append(sentence_td);

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
    self.mandetory_validate = function mandetory_validate(){
        // Check ∀v [(v.sentence === null) => (v.intval === null && v.strval === null)]
        var codings = self.get_sentence_codings();
        for (var i=0; i < codings.length; i++){
            if (codings[i].sentence !== null) continue;

            if ($.map(self.values(codings[i].values), function(cv){
                return (!self.is_empty_codingvalue(cv)) || null;
            }).length){
                return "Cannot save data.\n 1) Make sure all coded sentences have a sentence number.2) Make sure no codings are left empty if your project does not allow this.";
            }
        }

        return true;
    };

    /*
     * Checks if all codingschemarules pass.
     */
    self.validate = function validate(){
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

    self.is_empty_codingvalue = function is_empty_codingvalue(cv){
        return cv.intval === null && cv.strval === null;
    };

    self.is_empty_coding = function is_empty_coding(coding){
        return all(self.values(coding.values), self.is_empty_codingvalue)
    };

    /*
     * Returns 'minimised' version of given coding, which can easily be serialised.
     */
    self.pre_serialise_coding = function pre_serialise_coding(coding){
        return {
            start : coding.start, end : coding.end,
            sentence_id : (coding.sentence === null) ? null : coding.sentence.id,
            values : $.map($.grep(self.values(coding.values), self.is_empty_codingvalue, true), self.pre_serialise_codingvalue)
        }
    };

    self.pre_serialise_codingvalue = function pre_serialise_codingvalue(codingvalue){
        if(codingvalue.field === undefined){
            return null;
        }
        return {
            codingschemafield_id : codingvalue.field.id,
            intval : codingvalue.intval,
            strval : codingvalue.strval
        }
    };

    self.pre_serialise_coded_article = function pre_serialise_coded_article () {
        return {
            status_id : self.state.coded_article.status,
            comments : self.state.coded_article.comments
        }
    };

    self.warn_for_unfinished = function warn_for_unfinished(){
        if (self.state.coded_article.status !== self.STATUS.IN_PROGRESS){
            new PNotify({
                "type": "warning",
                "text": "Setting status to 'unfinished' while field validation failed."
            });
        }

        self.set_status(self.STATUS.IN_PROGRESS);
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
    self.save = function save(options){
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
            self.warn_for_unfinished();
            return self.show_message("Validation", validation);
        }

        // Check optional requirements
        validation = validate ? self.validate() : true;
        if (validation !== true){
            self.warn_for_unfinished();
            self.show_message("Validation", validation);
        }

        // Send coding values to server
        self.show_loading("Saving codings..");
        $.ajax({url: "codedarticle/{0}/save".f(self.state.coded_article_id),
            data: JSON.stringify({
                "coded_article" : self.pre_serialise_coded_article(),
                "codings" : $.map(self.get_codings(), self.pre_serialise_coding)}),
            type: "POST",
            headers: {"X-CSRFTOKEN": csrf_middleware_token},
            dataType: "text"
        }).done(function(data, textStatus, jqXHR){
            self.hide_loading();

            // BUG: Codings get lost sometimes. We try to detect the bug by checking the server:
            var response = JSON.parse(jqXHR.responseText);
            var expected_n_codings = self.get_codings().length;
            var expected_n_values = $.map(self.get_codings(), function(coding){
                return $.grep(self.values(coding.values), self.is_empty_codingvalue, true).length;
            }).reduce(function(a, b){ return a + b; }, 0);

            if (expected_n_codings != response.saved_codings){
                new PNotify({
                    "title": "Unexpected number of saved codings!",
                    "text": "We sent {0} codings to the server, but server saved only {1}. Press F12 and click 'console'. Copy the messages and open a bug report. Thanks!".format(
                        expected_n_codings, response.saved_codings
                    ),
                    "type" : "error",
                    "delay" : 300000
                });

                self.log("Request: " + String($.map(self.get_codings(), self.pre_serialise_coding)));
                self.log("Response: " + String(response));
            } else if (expected_n_values != response.saved_values) {
                new PNotify({
                    "title": "Unexpected number of saved coding values!",
                    "text": "We sent {0} codings to the server, but server saved only {1}. Press F12 and click 'console'. Copy the messages and open a bug report. Thanks!".format(
                        expected_n_values, response.saved_values
                    ),
                    "type": "error",
                    "delay": 300000
                });

                self.log("Request: " + String($.map(self.get_codings(), self.pre_serialise_coding)));
                self.log("Response: " + String(response));
            }
            // END BUG

            new PNotify({
                "title" : "Done",
                "text" : "Codings saved succesfully. Server replied: saved {0} codings with {1} values.".format(
                    response.saved_codings, response.saved_values
                ),
                "type" : "success",
                "delay" : 5000
            });

            self.set_column_text("status", self.STATUS_TEXT[self.state.coded_article.status]);
            self.set_column_text("comments", self.state.coded_article.comments||"");

            // Reset 'unsaved' state
            self.set_unsaved(false);

            // Change article status in table
            var td_index = self.article_table_container.find("thead th:contains('status')").index();
            var current_row = self.article_table_container.find("tr.row_selected");
            $("td:eq({0})".f(td_index), current_row).text(self.STATUS_TEXT[self.state.coded_article.status]);

            if (success_callback !== undefined && success_callback.currentTarget === undefined){
                success_callback(data, textStatus, jqXHR);
            }
        }).fail(error_callback);
    };

    self.set_status = function set_status(state){
        self.article_status_dropdown.val(state);
        self.article_status_dropdown.trigger("change");
    };

    self.save_and_continue = function save_and_continue () {
        self.save({ success_callback : self.select_next_article, validate : true });
    };

    self.finish_and_continue = function finish_and_continue(){
        self.set_status(self.STATUS.COMPLETE);
        self.save_and_continue();
    };

    self.irrelevant_and_continue = function irrelevant_and_continue () {
        self.set_status(self.STATUS.IRRELEVANT);
        self.save_and_continue();
    };

    self._select = function _select(row){
        if (row.length === 0){
            self.show_message("Done", "Last article finished, coding done!");
            return;
        }

        row.trigger("click");
    };

    self.select_next_article = function select_next_article () {
        self._select(self.article_table_container.find(".row_selected").next());
    };

    self.select_prev_article = function select_prev_article () {
        self._select(self.article_table_container.find(".row_selected").prev());
    };

    /* Returns an every increasing (unique) integer */
    self._id = 0;
    self.get_new_id = function get_new_id(){
        return self._id += 1
    };

    /*
     * Given two sentences a and b, return if a is "greater than" than b.
     */
    self.sentence_greater_than = function sentence_greater_than(a, b){
        if (a.parnr > b.parnr) return 1;
        if (a.parnr < b.parnr) return -1;
        return a.sentnr - b.sentnr;
    };

    self.coded_article_fetched = function coded_article_fetched(coded_article, codings, sentences){
        self.log("Retrieved " + codings.length + " codings and " + sentences.length + " sentences");

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

        self.set_unsaved(false);
        self.state.sentences = sentences;
        self.state.codings = codings;
        self.state.coded_article = coded_article[0];

        self.article_status_dropdown.val(self.state.coded_article.status).trigger("changed");
        self.article_comment_textarea.val(self.state.coded_article.comments).trigger("changed");

        var get_unit = function () {
            return this.parnr + "." + this.sentnr;
            //return "{0}.{1}".f(this.parnr, this.sentnr);
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
        $("#editor").show();
        $(".sidebar").scrollTop(0);
        self.log("Building article html..");
        self.sentences_fetched(sentences);
        self.log("Highlighting..");
        self.highlight();
        self.log("Building codings html..");
        self.codings_fetched();
        self.log("Setting tab order..");
        self.set_tab_order();
        self.log("Hiding non-visible sentence codings..");
        self.hide_non_visibile_sentence_codings();
        self.set_unsaved(false);
        self.hide_loading();

        var container = (self.codingjob.articleschema === null) ? self.sentence_codings_container : self.article_coding_container;
        container.find("input:visible").first().focus();

        self.log("Done.")
    };

    self.highlight = function highlight(){
        $("div.sentences").highlight(self.highlight_labels, { lenient : true });
    };

    self.unhighlight = function unhighlight(){
        $("div.sentences").unhighlight();
    };

    self.hide_non_visibile_sentence_codings = function hide_non_visibile_sentence_codings(){
        // We need to find all codings within [top, bottom]
        var top = $(window).scrollTop();
        var bottom = top + $(window).height();

        codings = $("#sentence-codings-parent").children();
        codings.css("height", codings.height() + "px");
        var from = codings.first(), to = codings.last();

        if (codings.length === 0) return;

        // Find first coding row visible
        var first = codings.first();
        var diff = top - first.offset().top;
        if (diff > 0){
            // First element is not visible, which is?
            var nth = Math.ceil(diff / first.height());
            from = (codings.length > nth) ? $(codings.get(nth)) : codings.last();
        }

        // Find last coding row visible
        var last = codings.last();
        var diff = bottom - last.offset().top;
        if (diff <= 0){
            // Last element is not visible, which is?
            var nth = -Math.floor(diff / first.height());
            to = (codings.length > nth) ? $(codings.get(codings.length - nth)) : codings.first();
        }

        $("> td", codings).show();
        $("> td", from.prevAll()).hide();
        $("> td", to.nextAll()).hide();
    };

    /*
     * Resets internal state and fetches new coded article, which consists of:
     *  - coded_article
     *  - codings + values
     *  - sentences
     * coded_article_fetched is called when requests finished
     */
    self.get_article = function get_article(coded_article_id){
        self.log("get_article(coded_article_id={0}) called".f(coded_article_id))
        var base_url = self.get_api_url() + "coded_articles/" + coded_article_id + "/";

        self.state = self.get_empty_state();
        self.sentence_codings_container.find("table tbody").html("");
        self.state.coded_article_id = coded_article_id;

        self.state.requests = [
            self.from_api(base_url),
            self.from_api(base_url + "codings"),
            self.from_api(base_url + "sentences")
        ];

        self.show_loading("Loading codings..");
        $.when.apply(undefined, self.state.requests).then(self.coded_article_fetched);
    };


    /*
     * Get descendants. Needs to be bound to a code object. This call is
     * automatically cached, and stored in code.descendants.
     */
    self.get_descendants = function get_descendants(depth){
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
    self.get_codings = function get_codings(container){
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
    self.get_sentence_codings = function get_sentence_codings(){
        // Note: this function depends on the presence of DOM elements. This is due to
        // a bug in earlier versions which duplicated codings. The only reliable way for
        // now is to match codings with DOM elements.
        return $.grep(self.get_codings(self.sentence_codings_container), self.is_empty_coding, true);
    };

    /*
     * Return article coding
     */
    self.get_article_coding = function get_article_coding(){
        // Note: this function depends on the presence of DOM elements. This is due to
        // a bug in earlier versions which duplicated codings. The only reliable way for
        // now is to match codings with DOM elements.
        return self.get_codings(self.article_coding_container)[0];
    };

    self.get_empty_coding = function get_empty_coding(properties){
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

    self.is_article_coding = function is_article_coding(coding){
        return coding.sentence === null;
    };


    /******** EVENTS *******/
    // TODO: Only initialise article coding html once.
    self.codings_fetched = function codings_fetched(){
        self.state.sentence_codings = $.grep(self.values(self.state.codings), self.is_article_coding, true);
        self.state.sentence_codings.sort(function(a,b){
            return self.sentence_greater_than(a.sentence, b.sentence);
        });

        // Determine article coding
        var article_coding = $.grep(self.values(self.state.codings), self.is_article_coding);

        if (article_coding.length === 0){
            self.state.article_coding = self.get_empty_coding();
            self.article_status_dropdown.trigger("change");
        } else {
            self.state.article_coding = article_coding[0];
        }

        // Create html content
        self.log("Building article coding html..");
        self.article_coding_container.html(self.get_article_coding_html());
        rules.add(self.article_coding_container);

        self.log("Building sentence coding html..");
        self.initialise_sentence_codings();
        rules.add(self.sentence_codings_container);
    };

    self.delete_codingvalue = function delete_codingvalue () {
        ct = $(document.activeElement);

        // Must be focusable and an input element
        if (ct.attr("tabindex") === undefined && !ct.is("input")) return;
        ct.attr("first_match", "null").val("").blur().focus();
    };

    /*
     * Registers property 'choiches' on each schemafield, which can be used
     * for autocompletes.
     *
     * TODO: Move to autocomplete
     */
    self.schemafields_fetched = function schemafields_fetched(){
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
    self.codebooks_fetched = function codebooks_fetched(){
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

            // Set hidden property
            $.each(self.find_hidden(codebook.codes), function(i, c){
                c.hidden = true;
            });
        });
    };

    self.find_hidden = function find_hidden(codes){
        return Array.prototype.concat.apply([], $.map(codes, function(c){
            return c.hide ? [c].concat(self.values(c.get_descendants())) : null;
        }));
    };

    /*
     * Initialise highlighters by preparing self.highlighter_labels. May
     * push 'undefined' if no label is available in the codebook for the requested
     * language.
     */
    self.highlighters_fetched = function highlighters_fetched(){
        var labels = [];
        var language_id, codebook;

        $.each(self.models.schemas, function(schema_id, schema){
            language_id = schema.highlight_language;
            $.each(schema.highlighters, function(i, codebook_id){
                codebook = self.models.codebooks[codebook_id];
                $.each(codebook.codes, function(i, code){
                    labels.push(code.labels[language_id]||"");
                });
            });
        });

        self.highlight_labels = $.grep(labels, function(label){
            return !!label.trim().length;
        });
    };


    // TODO: Remove legacy code (get_unit() logic, etc.)
    self.sentences_fetched = function sentences_fetched(sentences) {
        var html = $('<div>');
        var prev_parnr = 1;

        $.each(sentences, function (i, s) {
            var _html = $('<div />').attr('id', 'sentence-' + s.id);
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
    self.set_tab_order = function set_tab_order(){
        var tabindex = 1;

        var set_tabindex = function(_, el) {
            $(el).attr("tabindex", tabindex);
            tabindex += 1;
        };

        $.each(self.article_comment_textarea, set_tabindex);
        $.each($("input:visible", self.article_coding_container), set_tabindex);
        $.each($("#sentence-codings-parent > .coding"), function(_, row){
            $.each($("input:visible, .focus-stealer", row), set_tabindex);
        });
    };

    /*
     * Change the contents of the column with `column_name` in the currently active row.
     */
    self.set_column_text = function set_column_text(column_name, value){
        var column = self.article_table_container.find("thead").find("th:contains('{0}')".f(column_name));
        var column_index = column.parent().children().index(column);
        var cell = self.article_table_container.find("tr.row_selected").children(":eq({0})".f(column_index));
        cell.text(value);
    };

    self.article_status_changed = function article_status_changed(){
        self.state.coded_article.status = parseInt($(this).val());
        self.set_unsaved();
    };

    self.datatables_row_clicked = function datatables_row_clicked(row){
        // Do nothing if header is clicked
        if (row.closest("thead").length){
            return;
        }

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

    self.window_resized = function window_resized(){
        var width = $(window).width();
        if (self.previous_width !== width)
            return;

        // We need to adjust to the new browser width
        self.previous_width = width;
        self.datatable.fnAdjustColumnSizing();
    };

    self.initialise_shortcuts = function initialise_shortcuts(){
        $.each(self.shortcuts(), function(keys, callback){
            $(document).delegate('*', 'keydown.' + keys, function(event){
                event.preventDefault();
                event.stopPropagation();
                callback(event);
            });
        })
    };

    // TODO: Clean, comment on magic
    self.initialise_wordcount = function initialise_wordcount(){
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

    self.on_unload = function on_unload(){
        if (!self.unsaved) return;
        return "You have unsaved changes. Continue?"
    };

    self.stopped_scrolling = function(){
        self.last_scroll = null;
        self.hide_non_visibile_sentence_codings();
    };

    self.on_scroll = function(e){
        if (self.last_scroll === null){
            self.last_scroll = Date.now();
        }

        delta = Date.now() - self.last_scroll;
        if (delta > self.SCROLL_TIMEOUT){
            self.last_scroll = null;
        } else {
            clearTimeout(self.scroll_timeout);
            self.scroll_timeout = setTimeout(self.stopped_scrolling.bind(e), self.SCROLL_TIMEOUT);
        }
    };
    
    self.initialise = function initialise(project_id, codingjob_id, coder_id, language_id){
        $("#lost-codes").hide();
        $("#lost-codes").append($("<a>").attr('href','#').text("Don't show this message again")
            .addClass("pull-right")).click(
            function(e){
                $("#lost-codes").addClass("dont-show").hide();
                e.preventDefault();
            });
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

        /**
         * For all AJAX errors, display a generic error messages. This eliminates
         * lots of boiler-plate code in functions which use AJAX calls.
         */
        $(document).ajaxError(function(event, xhr, ajaxOptions) {
            var message = "An error occured while requesting: {0}. Server responded: {1} {2}.";
            message = message.f(ajaxOptions.url, xhr.status, xhr.statusText);
            self.hide_loading();
            self.show_message("AJAX error", message);
        });

        /*
         * Ask user to confirm quitting in the case of unsaved changes
         */
        $(window).bind("beforeunload", function(){
            return self.modified() ? "Unsaved changes present. Continue quitting?" : undefined;
        });


        window.onbeforeunload = self.on_unload;
        $(window).on("scroll", self.on_scroll);
    };

    return self;
});


