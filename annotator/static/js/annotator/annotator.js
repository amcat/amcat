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
            deleted_rows: [],
            modified_rows: [],
            sentence_codings_modified: false,
            article_coding_modified: false,
            article_coding : null,
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

    self.state = self.get_empty_state();
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
        self.sentence_codings_container = $("<div>");
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

    /******** KEYBOARD SHORTCUTS *******/
    self.shortcuts = function(){ return {
        "ctrl+s" : self.save_btn.click,
        "ctrl+down" : self.add_row,
        "ctrl+shift+down" : self.add_row,
        "shift+down" : self.copy_row,
        "ctrl+i" : self.irrelevant_btn.click,
        "ctrl+d" : self.save_continue_btn.click
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
    self.get_article_coding_html = function(schemafields){
        return $("<table>").append($.map(widgets.get_html(schemafields, null), function(widget, i){
            var label = widgets.get_label_html(schemafields[i], widget);
            return $("<tr>")
                .append($("<td>").append(label))
                .append($("<td>").append(widget));
        }));
    };

    self.select_all_sentences = function () {

    };

    self.save_and_continue = function () {

    };
    self.irrelevant_and_save = function () {

    };
    self.select_next_article = function () {

    };
    self.select_prev_article = function () {

    };

    /* Returns (new) DOM representation of a single sentence coding */
    self.get_sentence_coding_html = function(schemafields, sentence){

    };

    self.get_article = function(article_id){

    };

    /******** EVENTS *******/
    // TODO: Only initialise article coding html once.
    self.codings_fetched = function(){
        // Check whether there is an articleschema for this codingjob
        if (self.codingjob.articleschema === null) return;

        // Get schemafields belonging to this articleschema
        var articleschema = self.codingjob.articleschema;
        var schemafields = filter(function(f){ return f.codingschema === articleschema }, self.models.schemafields);
        schemafields.sort(function(f1, f2){ return f1.fieldnr - f2.fieldnr });

        var empty_coding = {
            id: null,
            codingschema: articleschema,
            article: self.state.article_coding.article,
            sentence: null,
            comments: null,
            codingjob: self.codingjob
        };

        // Collect article codings. If no codings are available, create a
        // new empty one.
        var codings = filter(function(c){ return c.sentence === null }, self.state.codings);
        if (codings.length === 0) codings.push(empty_coding);

        // Create html content
        self.article_coding_container.html(
            annotator.articlecodings.get_schemafields_html(schemafields, null)
        );

        rules.add(self.article_coding_container);
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
                callback(event);
            });
        })
    };

    self.initialise = function(project_id, codingjob_id, coder_id){
        console.log("test");

        self.project_id = project_id;
        self.codingjob_id = codingjob_id;
        self.coder_id = coder_id;

        self.initialise_containers();
        self.initialise_buttons();
        self.initialise_dialogs();
        self.initialise_shortcuts();
    };


    return self;
})({});


/************* Storing data *************/
annotator.showMessage = function (text) {
    $('#message-dialog-msg').text(text);
    $('#message-dialog').dialog('open');
};

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
