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

annotator.articletable.selectRow = function(row){
    // select a row in the article table. used by goToNextRow and goToPreviousRow functions below
    row.addClass('row_selected');
    annotator.articletable.showArticleFromRow(row);
    var scroller = $('#article-table-container table').parent(); 
    $(scroller).scrollTo(row, {offset:-50});
}

annotator.articletable.goToNextRow = function(){
    // used for articles table, by continue buttons and 'next'
    if(!annotator.confirmArticleChange()) return;
    $('#article-table-container table .row_selected').each(function(){
        var row = $(this);
        if(row.next().length == 0){
            annotator.showMessage('last article reached!');
        } else {
            row.removeClass('row_selected');
            annotator.articletable.selectRow(row.next());
        }
    });
    
    if($('#article-table-container table .row_selected').length == 0) {
        // no selected row exists, pick first row
        var firstTr = $('#article-table-container table tbody tr:first')
        firstTr.addClass('row_selected');
        annotator.articletable.showArticleFromRow(firstTr);
    }
}

annotator.articletable.goToPreviousRow = function(){
    // used for articles table, by 'previous' button
    if(!annotator.confirmArticleChange()) return;
    $('#article-table-container table .row_selected').each(function(){
        var row = $(this);
        if(row.prev().length == 0){
            annotator.showMessage('first article reached!');
        } else {
            row.removeClass('row_selected');
            annotator.articletable.selectRow(row.prev());
        }
    });
}


annotator.articletable.highlight = function(){
    console.log("Highlighting all labels in article..");
    $.each(annotator.fields.ontologies, function(ont_id, ont){
        // For each ontology
        var labels = [];
        $.each(ont, function(code_id, code){
            labels.push(code.label);
        });

        $("div.sentences").easymark("highlight", labels.join(" ")); 
    });
};

// Function to force redraw (recalculation) of element
var redraw = function(){
    var ut = $("#unitcoding-table");
    var _prev = ut.css("display");
    ut.css("display", "none");
    ut.css("display", _prev);
}

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

        // We would decrease the current header too much if
        // we blindly accept the new_size in case this headers
        // length is less than we aim for.
        new_size = (new_size < aim) ? aim : new_size;

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
}

/*
 * Some codingschemas have a lot of fields, causing the table
 * to grow larger than it actually can.
 *
 * @return: resizing succesfull
 */
annotator.articletable.fit_table = function(min_size_input, min_size_header){
    // Default min_size_input / min_size_header to 50px / 8px
    min_size_input = (min_size_input === undefined) ? 50 : min_size_input;
    min_size_header = (min_size_header === undefined) ? 8 : min_size_header;
    
    var ut = $("#unitcoding-table");
    var headers = $("th", ut);
    var inputs = $("input[type=text]", ut);
    var aimed_size = ut.parent().outerWidth();


    // Check if table initialised yet
    if(ut.children().length < 2){
        window.setTimeout(annotator.articletable.fit_table, 200);
        return;
    }

    // Check if previous resize matched our goals
    if (ut.outerWidth() <= aimed_size){
        return true;
    }

    // Try to resize headers by deleting characters
    var decr_h = annotator.articletable.decrease_headers;
    while(ut.outerWidth() >= aimed_size && decr_h(min_size_header)){ }

    if (ut.outerWidth() > aimed_size){
        console.log("Could not resize table to width of screen..");
    } else {
        $.each(inputs, function(i, input){
            redraw();
            //$(input).width("100%");
        });
    }

}

annotator.articletable.showArticleFromRow = function(row){
    var aid = row.children('td:first').text(); // get article id from first column of current row
    annotator.articleid = aid;
   
    $('.sentences').html('Loading..');
    $.ajax({
        "url": "../article/" + annotator.articleid + "/sentences",
        "success": function(json) {
            annotator.articleSentences = json.sentences;
            annotator.writeArticleSentences(json.sentences);
            
            if(json.video){
                console.debug('video html found');
                json.video = json.video.replace(/width="\d+"/g, 'width="250"').replace(/height="\d+"/g, 'height="140"')
                $('.video-container').html(json.video);
                //$('.sentences').css('height', '80%');
            } else {
               // $('.sentences').css('height', '100%');
                $('.video-container').html('').hide();
            }
            
            /*** set autocomplete for 'unit' column ***/
            annotator.fields.fields['unit'].items = [];
            $.each(json.sentences, function(i, sentenceObj){
                annotator.fields.fields['unit'].items.push({'label':sentenceObj.unit, 'value':sentenceObj.id})
            });
            console.debug('set fields for unit');

            annotator.articletable.highlight();
            annotator.articletable.fit_table();
        },
        "error": function(jqXHR, textStatus, errorThrown){
            console.debug('error loading article');
            $('.article-part').html('<div class="error">Error loading article data from <a href="' + this.url + '" target="_blank">' + this.url + '</a></div>');
        },
        "dataType": "json"
    });
    
    
    
    $('.coding-part').show();
    //$('#irrelevant-button').focus();
    //annotator.codingTypeSet();
    annotator.articlecodings.showArticleCodings();
    annotator.unitcodings.showSentenceCodings();
    
    annotator.codingsAreModified(false);
    annotator.resetArticleState();
    
    var comment = row.find('td:nth-child(8) div div').attr('title'); // very long comments are stored in title
    if(!comment) comment = row.children('td:nth-child(8)').text();
    console.debug('comment', comment);
    $('#article-comment').val(comment);
    
    console.debug('status', row.children('td:nth-child(7)').text());
    $('#article-status option:contains("' + row.children('td:nth-child(7)').text() + '")').attr('selected', 'selected');
    
    
    $('#edit-article-button').button( "option", "disabled", false); // when article is selected, it is possible to edit
    
    if(row.next().length == 0){ // no next article available
        $('#next-article-button').button( "option", "disabled", true);
    } else {
        $('#next-article-button').button( "option", "disabled", false);
    }
    if(row.prev().length == 0){ // no previous article available
        $('#previous-article-button').button( "option", "disabled", true);
    } else {
        $('#previous-article-button').button( "option", "disabled", false);
    }
    
    annotator.articletable.highlight();
}


annotator.articletable.clickArticleRow = function(row) { // called if user clicks on article table row
    if(!annotator.confirmArticleChange()) return;
    $('#article-table-container table .row_selected').removeClass('row_selected');
    row.addClass('row_selected');
    annotator.articletable.showArticleFromRow(row);
} 


annotator.articletable.onCreateArticleTable = function(){
    /*** set items of articles table ***/
    //$("#article-table-container table tbody").click(annotator.articletable.clickArticleRow);
    //$("#article-table-container table td").css('cursor', 'pointer');
    $('#next-article-button').button("option", "disabled", false);
}
   

   
   
annotator.articletable.showEditArticleDialog = function(articleid){
    if(!annotator.confirmArticleChange()) return;
    $('#article-edit-form').html('Loading...');
    $("#article-dialog-form").dialog("open");
    annotator.articletable.articleEditForm = new Form("annotator/articleFormJSON/" + articleid, {'sortFields':true});
    annotator.articletable.articleEditForm.ready = function(){
        $('#article-edit-form').html(annotator.articletable.articleEditForm.render.table);
    }
    annotator.articletable.articleEditForm.handle_loaderror = function(jqXHR, textStatus, errorThrown){
        console.debug('Error loading form: ' + textStatus);
        $('#article-edit-form').html('<div class="error">Failed to load form: ' + textStatus + '</div>');
    }
    
    // ugly hack... should be removed when moving to django..
    annotator.articletable.articleEditForm.initialize_form2 = annotator.articletable.articleEditForm.initialize_form;
    annotator.articletable.articleEditForm.initialize_form = function(json){
        fields.autocompletes['source-6'] = {'showAll':true, 'isOntology':false, 'autoOpen':true, 'id':'source-6',
            items:json.mediumlist
        }
        annotator.articletable.articleEditForm.initialize_form2(json.form);
        annotator.fields.autocompletes.addAutocompletes($('#article-edit-form'));
        
        if(articleid == 0){ // new article form
            annotator.articletable.articleEditForm.fields['setnr'].initial = annotator.setnr;
            annotator.articletable.articleEditForm.fields['jobid'].initial = annotator.codingjobid;
            console.log('done setting setnr and jobid');
        }
    }
    
    console.debug('loading article edit form');
    annotator.articletable.articleEditForm.load();
}

annotator.articletable.saveEditArticleDetails = function(){
    annotator.articletable.articleEditForm.clean();
    if(annotator.articletable.articleEditForm.is_valid()){
        $('#article-edit-form').hide();
        $('#article-edit-status').html('Saving...');
        annotator.articletable.articleEditForm.send('annotator/storeEditArticle', function(data, textStatus, jqXHR){
            console.debug('article details', data);
            if(data.response == 'ok'){
                console.debug('saved edit article!' + textStatus);
                $("#article-dialog-form").dialog("close");
                location.reload();
            } else {
                 $('#article-edit-form').show();
                $('#article-edit-status').html('<div class="error">Failed to save. Error message: ' + data.errormsg + '</div>');
            }
        }, function(){
             $('#article-edit-form').show();
            $('#article-edit-status').html('<div class="error">Failed to save. Server error</div>');
        });
    } else {
        console.debug('invalid form');
    }
}


annotator.articletable.trimTableColumnString = function(obj) { // make sure that column text is not excessively long
    var sReturn = obj.aData[obj.iDataColumn];
    if (sReturn && sReturn.length > annotator.articletable.MAX_STR_COLUMN_LENGTH) {
        sReturn = '<div title="' + sReturn + '" class="widthlimit">' + sReturn.substring(0,annotator.articletable.MAX_STR_COLUMN_LENGTH) + '...</div>';
    }
    return '<div class="widthlimit">' + sReturn + '</div>';
};

})();
