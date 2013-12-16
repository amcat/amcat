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


annotator.articletable.trimTableColumnString = function(obj) { // make sure that column text is not excessively long
    var sReturn = obj.aData[obj.iDataColumn];
    if (sReturn && sReturn.length > annotator.articletable.MAX_STR_COLUMN_LENGTH) {
        sReturn = '<div title="' + sReturn + '" class="widthlimit">' + sReturn.substring(0,annotator.articletable.MAX_STR_COLUMN_LENGTH) + '...</div>';
    }
    return '<div class="widthlimit">' + sReturn + '</div>';
};

})();
