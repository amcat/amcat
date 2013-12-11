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

(function(){

annotator.articletable = {};
annotator.articletable.MAX_STR_COLUMN_LENGTH = 35; // length of string when limiting length (in article table for headline/comment)
annotator.articletable.articleTable = null;
annotator.articletable.articleEditForm = null;



/************* Article table *************/
annotator.articletable.get_table = function(){
    return $('#article-table-container').find('table');
};

annotator.articletable.click_article_row = function (row) { // called if user clicks on article table row
    if (!annotator.confirmArticleChange()) return;
    annotator.articletable.get_table().find(".row_selected").removeClass("row_selected");
    annotator.articletable.select_row(row);
};



/* Select row in article table, which means it will be loaded
* from the server, including all their codings. */
annotator.articletable.select_row = function (row) {
    row.addClass('row_selected');
    annotator.articletable.get_article(annotator.articletable.get_article_id(row));
    annotator.articletable.get_table().parent().scrollTo(row, {offset: -50});
};

/*
 * Based on a row (jQuery tr element), return the article id corresponding
 * to the id of the article in that row.
 */
annotator.articletable.get_article_id = function (tr) {
    return parseInt(tr.children('td:first').text());
};

annotator.articletable.select_next_row = function(){
    // Warn user for potentially lost data
    if(!annotator.confirmArticleChange()){
        return;
    }

    // Determine selected row
    var row = annotator.articletable.get_table().find(".row_selected");
    if (row.length === 0) return;
    if (row.length !== 1) throw "Only one row can be selected at a time.";

    // Last article?
    if(row.next().length == 0){
        annotator.showMessage('Last article reached!');
        return;
    }

    // Move to next row
    row.removeClass('row_selected');
    annotator.articletable.select_row(row.next());
};

annotator.articletable.select_previous_row = function () {
    // used for articles table, by 'previous' button
    if (!annotator.confirmArticleChange()) {
        return;
    }

    // Determine selected row
    var row = annotator.articletable.get_table().find(".row_selected");
    if (row.length === 0) return;
    if (row.length !== 1) throw "Only one row can be selected at a time.";

    // First article?
    if (row.prev().length == 0){
        annotator.showMessage('First article reached!');
        return;
    }

    row.removeClass('row_selected');
    annotator.articletable.select_row(row.prev());
};

annotator.articletable.highlight = function(){
    var _labels = [], escape_regex, labels = annotator.fields.highlight_labels;
    console.log("Highlighting ", labels.length ," labels in article..");

    escape_regex = function(str) {
        return str.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, "\\$&");
    }; 

    $.each(labels, function(i, label){
        _labels.push(escape_regex(label));
    });

    $("div.sentences").easymark("highlight", _labels.join(" ")); 
};

// Function to force redraw (recalculation) of element
var redraw = function () {
    var ut = $("#unitcoding-table");
    var _prev = ut.css("display");
    ut.css("display", "none");
    ut.css("display", _prev);
};

_DECREASE_BY = 3;

/*
 * Helper function of fit_table(), which decreases the headers.
 *
 * @return: true if table resized, false if not
 */
annotator.articletable.decrease_headers = function(min_size){
    var ut = $("#unitcoding-table");
    var headers = $("th", ut);
    var old_table_size = ut.outerWidth();

    // Determine largest header
    var max_found = 0;
    $.each(headers, function(i, header){
        max_found = Math.max(max_found, $(header).text().length);
    });

    if (max_found <= min_size || min_size <= _DECREASE_BY){
        // All headers are already resized to their minimum
        return false;
    }

    var aim = max_found - _DECREASE_BY;
    var decreased_headers = [];
    $.each(headers, function(i, header){
        header = $(header);

        var cur_size = header.text().length;
        var new_size = cur_size - _DECREASE_BY;

        if (cur_size <= min_size || cur_size <= aim){
            // Smaller than we can accept.
            return;
        }

        // Save original header for users hovering
        if (header.attr("title") === undefined){
            header.attr("title", header.text());
        }

        // Save current state in case resizing fails
        header.attr("__prev", header.text());
        header.text(header.text().substr(0, aim));

        //console.log(headers.toArray().indexOf(header.get(0)));
        decreased_headers.push(header);
    });

    // Force redraw
    redraw();
    
    if (old_table_size <= ut.outerWidth()){
        // Resizing failed :-(
        $.each(decreased_headers, function(i, header){
            header.text(header.attr("__prev"));
            header.attr("__prev", undefined);
        });

        return false;
    }

    return true;
};

/*
 * Some codingschemas have a lot of fields, causing the table
 * to grow larger than it actually can.
 *
 * @return: resizing succesfull
 */
annotator.articletable.fit_table = function (min_size_input, min_size_header) {
    // Default min_size_input / min_size_header to 50px / 8px
    min_size_header = (min_size_header === undefined) ? 8 : min_size_header;

    var ut = $("#unitcoding-table");
    var inputs = $("input[type=text]", ut);
    var aimed_size = ut.parent().outerWidth();


    // Check if table initialised yet
    if (ut.children().length < 2) {
        window.setTimeout(annotator.articletable.fit_table, 200);
        return;
    }

    // Check if previous resize matched our goals
    if (ut.outerWidth() <= aimed_size) {
        return true;
    }

    // Try to resize headers by deleting characters
    var decr_h = annotator.articletable.decrease_headers;
    while (ut.outerWidth() >= aimed_size && decr_h(min_size_header)) {
    }

    if (ut.outerWidth() > aimed_size) {
        console.log("Could not resize table to width of screen..");
    } else {
        $.each(inputs, function (i, input) {
            redraw();
            //$(input).width("100%");
        });
    }

};

/*
 *
 */
annotator.articletable.get_article = function(article_id) {
    annotator.article_id = article_id;
    var base_url = annotator.get_api_url() + "coded_articles/" + article_id + "/";

    annotator.articletable.requests = [
        $.getJSON(base_url),
        $.getJSON(base_url + "codings"),
        $.getJSON(base_url + "sentences")
    ];

    $("<div id='loading_codings'>Loading codings, please wait..</div>").dialog({modal:true});

    var get_unit = function () {
        return this.parnr + "." + this.sentnr;
    };

    $.when.apply(undefined, annotator.articletable.requests).then(function (article, codings, sentences) {
        console.log("Retrieved " + codings.length + " codings and " + sentences.length + " sentences");
        codings = annotator.map_ids(codings[0].results);
        sentences = annotator.map_ids(sentences[0].results);
        annotator.resolve_ids(codings, sentences, "sentence");

        $.each(codings, function(coding_id, coding){
            annotator.map_ids(coding.values);
            annotator.resolve_ids(coding.values, annotator.fields.schemafields, "field");

            $.each(coding.values, function(value_id, value){
                value.coding = coding;
            });
        });

        annotator.sentences = sentences;
        annotator.codings = codings;
        annotator.article = article;

        $.each(sentences, function(sentence_id, sentence){
            sentence.get_unit = get_unit.bind(sentence);
        });

        // Set buttons
        $('#edit-article-button').button("option", "disabled", false);
       // $('#next-article-button').button("option", "disabled", row.next().length == 0);
        //$('#previous-article-button').button("option", "disabled", row.prev().length == 0);

        $("#article-comment").text(article.comments || "");
        $('#article-status').find('option:contains("' + article.status + '")').attr("selected", "selected");

        // Initialise coding area
        annotator.sentences_fetched(sentences);
        annotator.articletable.highlight();
        annotator.articlecodings.codings_fetched();

        $(".coding-part").show();
        $("#loading_codings").dialog("destroy");
        $("#article-comment").focus();
    });
};


annotator.articletable.trimTableColumnString = function(obj) { // make sure that column text is not excessively long
    var sReturn = obj.aData[obj.iDataColumn];
    if (sReturn && sReturn.length > annotator.articletable.MAX_STR_COLUMN_LENGTH) {
        sReturn = '<div title="' + sReturn + '" class="widthlimit">' + sReturn.substring(0,annotator.articletable.MAX_STR_COLUMN_LENGTH) + '...</div>';
    }
    return '<div class="widthlimit">' + sReturn + '</div>';
};

})();
