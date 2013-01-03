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


/**************************************************************************
    This script is split up in multiple files, to keep the script 
    easier to maintain.
    This file has dependencies for:
    annotator.unitcodings.js
    annotator.articletable.js
    annotator.fields.js
    jquery
    jquery.hotkeys
    jquery.dataTables
    jquery-ui
***************************************************************************/

var annotator = {}


var STATUS_NOTSTARTED = 0;
var STATUS_INPROGRESS = 1;
var STATUS_COMPLETE = 2;
var STATUS_IRRELEVANT = 9;

annotator.articleid = 0;
annotator.articleSentences = null;

annotator.articlecodings = {};
annotator.articlecodings.articleCodingForm = null;

annotator.commentAndStatus = {};

annotator.previousWidth = 0; // browser width


annotator.resetArticleState = function(){ // set state of article to unmodified
    annotator.unitcodings.deletedRows = []; // list with codedsentence ids
    annotator.unitcodings.modifiedRows = []; // list with codedsentence ids
    annotator.articlecodings.modified = false;
    annotator.unitcodings.modified = false;
    annotator.commentAndStatus.modified = false;
}





/************* Article codings *************/

annotator.articlecodings.showArticleCodings = function(){
    //$('#coding-title').html('Article Codings');
    if(annotator.articlecodings.containsArticleSchema){
        annotator.articlecodings.writeArticleCodingsTable();
        $('#article-coding').show();
    }
}


annotator.articlecodings.hideArticleCodings = function(){
    $('#article-coding').hide();
}


annotator.articlecodings.writeArticleCodingsTable = function(){
    $('#article-coding-form').html('Loading...');
    
    $.ajax({
        "url": "../codingjob/" + annotator.codingjobid + "/article/" + annotator.articleid + "/articlecodings",
        "success": function(html) {
            $('#article-coding-form').html(html);
            annotator.fields.autocompletes.addAutocompletes($('#article-coding-form'));
            $('#article-coding-form input').change(function(){
                annotator.articlecodings.onchange($(this));
            });
        },
        "error": function(jqXHR, textStatus, errorThrown){
            console.debug('error loading article codings');
            $('#article-coding-form').html('<div class="error">Error loading article codings data from <a href="' + this.url + '" target="_blank">' + this.url + '</a></div>');
        },
        "dataType": "html"
    });
}


annotator.articlecodings.onchange = function(el){
    console.debug('article coding', el.attr('name'), 'changed to', el.val());
    annotator.articlecodings.modified = true;
    annotator.codingsAreModified(true);
}


/************* state saving *************/


annotator.codingsAreModified = function(enable){
    annotator.enableSaveButtons(enable);
    //annotator.enableContinueButtons(enable);
    if(enable){
        $(window).bind("beforeunload", function(){return 'You have unsaved changes. Are you sure you would like to close this page?'});
    } else {
        $(window).unbind("beforeunload");
    }
}

annotator.enableSaveButtons = function(enable){
     $('#save-button, #save-button2').button( "option", "disabled", !enable);
}
// annotator.enableContinueButtons = function(enable){
    // $('#save-continue-button2, #save-continue-button').button( "option", "disabled", !enable);
// }




/*********** Comment & article status ***************/


annotator.commentAndStatus.onArticleStatusChange = function(){
    annotator.commentAndStatus.modified = true;
    annotator.codingsAreModified(true);
}


annotator.commentAndStatus.onCommentChange = function(){
    annotator.commentAndStatus.modified = true;
    annotator.codingsAreModified(true);
}


/************* Storing data *************/


annotator.setDialogSuccessButtons = function(){
    $("#dialog-save").dialog('option', 'buttons', {
        "Continue Editing": function(){
            annotator.resetArticleState();
            annotator.codingsAreModified(false);
            $(this).dialog("close");
        },
        "Go to next article": function(){
            annotator.resetArticleState();
            annotator.codingsAreModified(false);
            $(this).dialog("close");
            annotator.articletable.goToNextRow();
        }
    });
    $('.ui-dialog-buttonpane button:first').focus();
}


annotator.setDialogFailureButtons = function(){
    $("#dialog-save").dialog('option', 'buttons', {
        "Return to Article": function(){
            // annotator.resetArticleState();
            // annotator.codingsAreModified(false);
            $(this).dialog("close");
        }
    });
    $('.ui-dialog-buttonpane button:first').focus();
}


annotator.saveCodings = function(goToNext){
    if(annotator.fields.loadedFromServer == false){
        annotator.showMessage('Unable to save: ontologies not loaded yet. Please wait a few seconds');
        return;
    }
    var storeDict = {}
    if(annotator.commentAndStatus.modified){
        var comment = $('#article-comment').val();
        var status = $('#article-status').val();
        
        // set comment and status in article table
        var commentPos = annotator.articletable.articleTable.fnGetPosition($('#article-table-container .row_selected td:nth-child(8)').get(0));
        var statusPos = annotator.articletable.articleTable.fnGetPosition($('#article-table-container .row_selected td:nth-child(7)').get(0));
        annotator.articletable.articleTable.fnUpdate(comment, commentPos[0], commentPos[1]);
        annotator.articletable.articleTable.fnUpdate($('#article-status option:selected').text(), statusPos[0], statusPos[1]);
        
        // console.debug('set comment', comment, aPos, aData[aPos[1]]);
        storeDict['commentAndStatus'] = {'comment': comment, 'status':status};
    }
    if(annotator.articlecodings.modified){
        storeDict['articlecodings'] = {}; //amcat.getFormDict($('#article-coding-form'));
        $('#article-coding-form').find('input:text').each(function(j, input){
            input = $(input);
            var value = input.val();
            var field = annotator.fields.getFieldByInputName(input.attr('name'));
            var validationResult = annotator.validateInput(input, field);
            if(validationResult != true){
                input.addClass("error");
                if(validationResult != false){ // validationResult is text with error message
                    console.debug('validation', validationResult);
                    input.attr('title', validationResult);
                }
                input.bind("focus", function(){$(this).removeClass("error")});
                valid = false;
            } else {
                input.removeClass("error");
                storeDict['articlecodings'][input.attr('name')] = input.next().val() ? parseInt(input.next().val()) : input.val(); //{'text':input.val(), 'id':input.next().val(), 'name':input.attr('name')};
            }
        });
        console.log(storeDict['articlecodings']);
    }
    
    if($('#unitcoding-table').length > 0 && annotator.unitcodings.modified){
        var valid = true;
        var formjson = {'delete':annotator.unitcodings.deletedRows, 'modify':[], 'new':[]};
        var hasAnyValue = false;
        $('#unitcoding-table tbody tr').each(function(i, row){
            var rowjson = {};
            rowjson['codingid'] = $(row).find('input[name=codingid]').val();
            //console.debug('check row', rowjson['codingid'])
            if(rowjson['codingid'] == undefined) return; // for row with sentence text
            $(row).find('input:text').each(function(j, input){
                //console.debug(input);
                input = $(input);
                var value = input.val();
                var field = annotator.fields.getFieldByInputName(input.attr('name'));
                if(value.length > 0){
                    hasAnyValue = true;
                }
                //console.log(value, field, input.attr('name'));
                var validationResult = annotator.validateInput(input, field);
                
                if(validationResult != true){
                    annotator.markInputError(input, validationResult || '');
                    valid = false;
                } else {
                    input.removeClass("error");
                    rowjson[input.attr('name')] = input.next().val() || input.val();//{'text':input.val(), 'id':input.next().val(), 'name':input.attr('name')};
                }
            });
            if(!valid) return;
            if($.inArray(rowjson.codingid, annotator.unitcodings.modifiedRows) != -1){
                formjson['modify'].push(rowjson);
            } else if(rowjson.codingid.substring(0,3) == 'new'){
                formjson['new'].push(rowjson);
            } else { // unmodified sentence
                //console.debug('unmodified codedsentence', rowjson.codingid);
            }
        });
        if(!valid && $('#unitcoding-table tbody tr').length == 1 && hasAnyValue == false){
            //valid = true; // if there is only one row without any values added, it is still a valid sentence table (since completely empty)
            console.debug('ignoring empty sentence table');
        }
        else if(valid && (formjson['delete'].length > 0 || formjson['modify'].length > 0 || formjson['new'].length > 0)){
            //$("#dialog-save").dialog("open");
            console.debug('valid sentence coding form');
            //var data = JSON.stringify(formjson);
            //console.debug(annotator.unitcodings.codedarticleid, formjson);
            storeDict['unitcodings'] = formjson;
            
            
        } else if(!valid){
            console.debug('invalid sentence coding form');
            $('#message-dialog-msg').text('Unable to save: An invalid entry has been found in Sentence Codings');
            $('#message-dialog').dialog('open');
            return;
        }
    }
    
    $("#dialog-save-msg").html('Saving...');
    $("#dialog-save").dialog("open");
    var data = JSON.stringify(storeDict);
    if(data == '{}'){ // empty dict
        console.debug('no codings data to send');
        //return;
    }
    
    $.ajax({
      type: 'POST',
      url: "../codingjob/" + annotator.codingjobid + "/article/" + annotator.articleid + "/storecodings",
      data: data,
      success: function(json, textStatus, jqXHR){
          console.debug('saved!' + json.response);
          if(json.response == 'ok'){
            annotator.resetArticleState();
            $("#dialog-save-msg").html('<h3>Successfully saved codings!</h3>');
            if(goToNext){
                $("#dialog-save").dialog("close");
                annotator.articletable.goToNextRow();
            } else {
                for(var oldid in json.codedsentenceMapping){
                    $('input[name="codingid"][value="' + oldid + '"]').val(json.codedsentenceMapping[oldid]);
                    console.debug('mapping sentenceid', oldid, 'to', json.codedsentenceMapping[oldid]);
                }
                
                annotator.codingsAreModified(false);
                annotator.setDialogSuccessButtons();
            }
          } else {
            var errorMsg = '<h3>Error while saving, invalid form</h3>';
            if(json.id && json.fields){
                errorMsg += '<p>The fields in error are marked in red</p>';
            }
            if(json.message){
                errorMsg += '<p>' + json.message + '</p>'; // TODO: escape HTML, security issue
            }
            console.debug(errorMsg);
            $("#dialog-save-msg").html(errorMsg);
            annotator.setDialogFailureButtons();
            if(json.id){
                if(json.id == 'articlecodings'){
                    $.each(json.fields, function(name, errors){
                        var el = $('input[name=' + name + ']');
                        annotator.markInputError(el, errors[0]);
                    });
                } else if (json.id == 'commentAndStatus'){
                    $.each(json.fields, function(name, errors){
                        var el = $('input[name=' + name + ']');
                        annotator.markInputError(el, errors[0]);
                    });
                } else {
                    var row = $('input[value=' + json.id + ']').parents('tr').first();
                    $.each(json.fields, function(name, errors){
                        var el = $('input[name=' + name + ']', row);
                        console.log(name, errors, el);
                        annotator.markInputError(el, errors[0]);
                    });
                }
            }
         }
      }, error: function(jqXHR, textStatus, errorThrown){
          console.debug('error!' + textStatus);
          $("#dialog-save-msg").html('<h3>Error while saving, server error</h3><p>' + textStatus + '</p><br />');
          annotator.setDialogFailureButtons();
      },
      dataType: 'json'
    });
}   



annotator.markInputError = function(input, errorText){
    input.addClass("error");
    input.attr('title', errorText);
    input.bind("focus", function(){$(this).removeClass("error")});
}


annotator.validateInput = function(input, field){
    /* this will check if the text value of input and the related hidden input contain valid data (based on the allowed items of the field)
    it will also set the hidden value if it is outdated */
    var items = field.items;

    
    if(items.length == 0){
        console.log('no items for autocomplete');
        return true;
    }
    
    var value = input.val();
    
    if(value == ''){
        input.next().val(''); // if text input is empty, hidden field should be cleared
        return true;
    }
    
    var id = input.next().val(); // value of hidden input
    for(var i=0; i<items.length; i++){
        var item = items[i];
        if(value == item.label){
            if(id == item.value){ // both label and id match an item in the autocomplete list, thus valid
                return true;
            } else { // hidden id is not correct, but label is present in autocomplete list, thus valid, but need to update hidden value
                //$('input:hidden[name=' + v.name + '-hidden]').val(item.value);
                input.next().val(item.value);
            }
            return true;
        }
        //console.debug(v.text + ' - ' + item.label);
    }
    
    return 'Value not found in list of allowed values';
}


/************* General functions *************/



annotator.selectText = function(obj){
    annotator.deselectText();
    if(document.selection){
        var range = document.body.createTextRange();
        range.moveToElementText(obj);
        range.select();
    } else if(window.getSelection){
        var range = document.createRange();
        range.selectNode(obj);
        window.getSelection().addRange(range);
    }
}

annotator.deselectText = function(){
    if(document.selection){
        document.selection.empty(); 
    } else if(window.getSelection){
        window.getSelection().removeAllRanges();
    }
}


annotator.showMessage = function(text){
    $('#message-dialog-msg').text(text);
    $('#message-dialog').dialog('open');
}




annotator.sortLabels = function(a, b){ // natural sort on the labels
    a = a.label.toLowerCase();
    var asplit = a.split(/(\-?[0-9]+)/g);
    b = b.label.toLowerCase();
    var bsplit = b.split(/(\-?[0-9]+)/g);
    for(var i=0; i<asplit.length; i++){
        var diff = parseInt(asplit[i]) - parseInt(bsplit[i]);
        if(isNaN(diff)){
            diff = asplit[i].localeCompare(bsplit[i]);
        }
        if(diff != 0){
            return diff;
        }
    }
    return 0;
}



annotator.findSentenceByUnit = function(unit){
    var result = null;
    $.each(annotator.articleSentences, function(i, sentence){
        if(sentence.unit == unit){
            result = sentence;
            return false;
        }
    });
    return result;
}


annotator.findSentenceById = function(sentenceid){
    var result = null;
    $.each(annotator.articleSentences, function(i, sentence){
        if(sentence.id == sentenceid){
            result = sentence;
            return true;
        }
    });
    return result;
}


annotator.stripIdAttribute = function(id){ // used for sentence numbers that contain dots. does not work as 'id' attributes..
    return id.replace(/\./g, '-')
}


/* NOt used anymore
annotator.codingTypeSet = function(){ // if user picks sentence/article/both coding type
    if($('#article-coding-radio:checked').val()){ // radio is checked
        annotator.articlecodings.showArticleCodings();
        annotator.unitcodings.hideSentenceCodings();
    } else if($('#sentence-coding-radio:checked').val()){ // sentence codings radio checked
        annotator.unitcodings.showSentenceCodings();
        annotator.articlecodings.hideArticleCodings();
    } else { // both
        annotator.articlecodings.showArticleCodings();
        annotator.unitcodings.showSentenceCodings();
    }
}*/
// This function is not yet implemented
annotator.getNextSentenceNumber = function(sentencenumber){
    var result = null;
    $.each(annotator.articleSentences, function(i, sentence){
        if(sentence.unit == sentencenumber){
            //console.debug('sentences length', annotator.articleSentences.length,i+1);
            if(annotator.articleSentences.length > i+1){
                result = annotator.articleSentences[i+1].unit;
                console.log('next unit found', result);
            }
            return false;
        }
    });
    if(result == null) console.debug('next sentence not found');
    return result;
}


// This function is not yet implemented
annotator.findNextAvailableSentences = function(){
    var availableSentencenrs = [];
    var parnr = 0;
    $.each(annotator.articleSentences, function(i, sentence){
        parnr = parseInt(sentence.unit.split('.')[0]);
        var sentnr = parseInt(sentence.unit.split('.')[1]);
        var nextSentencenr = parnr + '.' + (sentnr+1);
        var exists = false;
        $.each(annotator.articleSentences, function(j, sentence2){
            if(sentence2.unit == nextSentencenr){
                exists = true;
                return true;
            }
        });
        if(!exists){
            availableSentencenrs.push(nextSentencenr);
        }
    });
    availableSentencenrs.push((parnr + 1) + '.1');
    return availableSentencenrs;
}

// This function is not yet implemented
annotator.showNewSentenceDialog = function(){
    if(!annotator.confirmArticleChange()) return;
    $('#new-sentence-text').val('DUMMY');
    var availableSentencenrs = annotator.findNextAvailableSentences();
    console.debug('available', availableSentencenrs);
    var html = $('<select id="new-sentence-nr" />');
    $.each(availableSentencenrs, function(i, nr){
        //html.append('<option value="' + nr + '">' + nr + '</option>');
        html.append($('<option />').attr('value', nr).text(nr));
    });
    $('#new-sentence-nr-placeholder').html(html);
    $("#new-sentence-dialog-form").dialog("open");
}

// This function is not yet implemented
annotator.saveNewSentenceDialog = function(){
    var text = $('#new-sentence-text').val();
    var sentencenr = $('#new-sentence-nr').val();
    
    var data = JSON.stringify({'text':text, 'sentencenr':sentencenr});
    
    $.ajax({
      type: 'POST',
      url: 'annotator/addSentence/' + annotator.articleid,
      data: {'jsonparams' : data},
      success: function(json, textStatus, jqXHR){
          console.debug('saved!' + json.response);
          if(json.response == 'ok'){
            console.debug('ok recieved');
            annotator.articletable.showArticleFromRow($('#article-table-container .row_selected'));
            $("#new-sentence-dialog-form").dialog("close");
            // $('#new-sentence-status').html('Saved!');
            // $("#new-sentence-dialog-form").dialog('option', 'buttons', {
                // "OK": function(){
                    
                    // $(this).dialog("close");
                // }
            // });
          } else {
            var errorMsg = '<h3>Error while saving</h3>' + $('<span />').text(json.errormsg).html();
            console.debug(errorMsg);
            $("#new-sentence-status").html(errorMsg);
          }
      }, error: function(jqXHR, textStatus, errorThrown){
          console.debug('error!' + textStatus);
          $("#new-sentence-status").html('Error while adding sentence! ' + textStatus + '<br />');
      },
      dataType: 'json'
    });
    
    //$("#new-sentence-dialog-form").dialog("close");
}



annotator.writeArticleSentences = function(sentences){
    var html = $('<div />');
    var previousParnr = 1;
    $.each(sentences, function(i, sentence){
        var sentenceHtml = $('<div />').attr('id', 'sentence-' + sentence.id);
        var parnr = sentence.unit.split('.')[0];
        if(parnr != previousParnr){
            sentenceHtml.addClass('new-paragraph');
        }
        if(sentence.unit == '1.1'){
            sentenceHtml.append($('<h2 />').text(sentence.text));
        } else {
            sentenceHtml.append($('<span />').addClass('annotator-sentencenr').text('(' + sentence.unit + ') '));
            sentenceHtml.append(document.createTextNode(sentence.text));
        }
        previousParnr = parnr;
        html.append(sentenceHtml);
    });
    
    if(sentences.length == 0){
        html.append('No sentences found for this article');
    }

    $('.sentence-options').show();
    $('.sentences').html(html);
    
}

// This function is not yet implemented
annotator.showSplitArticleDialog = function(){ //TODO make nice form out of this
    if(!annotator.confirmArticleChange()) return;
    $("#article-dialog-form").dialog("option", "title", "Create new article based on split");
    var html = $('<div />');
    
    var headline = $('#article-table-container .row_selected td:nth-child(3)').text(); // get headline from article table
    html.append($('<label />').text('Headline'));
    html.append($('<input />', {'value':headline, 'name':'headline'})).append('<br />');
    var selecthtml1 = $('<select />', {'name':'startSentence'});
    var selecthtml2 = $('<select />', {'name':'endSentence'});
    $.each(annotator.articleSentences, function(i, sentence){
        selecthtml1.append($('<option />', {'value': sentence.id}).text(sentence.unit));
        selecthtml2.append($('<option />', {'value': sentence.id}).text(sentence.unit));
    });
    html.append($('<label />').text('Start Sentence'));
    html.append(selecthtml1).append('<br />');
    html.append($('<label />').text('End Sentence'));
    html.append(selecthtml2).append('<br />');
    
    $('#article-edit-form').html(html);
    $("#article-dialog-form").dialog('option', 'buttons', {
        "Save": annotator.saveSplitArticle,
        "Cancel": function(){
            $(this).dialog("close");
        }
    });
    $("#article-dialog-form").dialog('open');
}

// This function is not yet implemented
annotator.saveSplitArticle = function(){
    var headline = $("#article-dialog-form input[name='headline']").val();
    var startSentence = $("#article-dialog-form select[name='startSentence']").val();
    var endSentence = $("#article-dialog-form select[name='endSentence']").val();
    
    if(!headline){
        $('#article-edit-status').html('Please insert a headline');
        return;
    }
            
    var data = JSON.stringify({
        'headline':headline,
        'startSentence':startSentence,
        'endSentence':endSentence,
        'codingjobid':annotator.codingjobid,
        'setnr':annotator.setnr
    });
    
    $.ajax({
      type: 'POST',
      url: 'annotator/createSplit/' + annotator.articleid,
      data: {'jsonparams' : data},
      success: function(json, textStatus, jqXHR){
          console.debug('saved!' + json.response);
          if(json.response == 'ok'){
            console.debug('ok recieved');
            $('#article-edit-status').html('Saved!');
            $("#article-dialog-form").dialog('option', 'buttons', {
                "OK": function(){
                    //$(this).dialog("close");
                    location.reload();
                }
            });
          } else {
            var errorMsg = '<h3>Error while saving</h3>' + $('<span />').text(json.errormsg).html();
            console.debug(errorMsg);
            $("#article-edit-status").html(errorMsg);
          }
      }, error: function(jqXHR, textStatus, errorThrown){
          console.debug('error!' + textStatus);
          $("#article-edit-status").html('Server error! ' + textStatus + '<br />');
      },
      dataType: 'json'
    });
}


annotator.confirmArticleChange = function(){
    if(annotator.articlecodings.modified || annotator.unitcodings.modified || annotator.commentAndStatus.modified){
        return confirm('You have unsaved changes. Are you sure you would like to change article?');
    }
    return true;
}


annotator.checkWindowWidth = function(){
    var widthMessage = 'Your browser width is lower than 1000 pixels. Please use a higher resolution for a better layout.'
    if($(window).width() < 1000){
        if($('#messages:contains("' + widthMessage + '")').length == 0){ // message not already visible
            $('#messages').append('<div>' + widthMessage + '</div>')
        }
    } else {
        $('#messages div:contains("' + widthMessage + '")').remove();
    }
}

annotator.initPage = function(){
    annotator.resetArticleState();
    
    
    /*** Hide currently unused elements ***/
    $('.coding-part').hide();
    $('.sentence-options').hide();
    
    
    /*** Initialize all buttons ***/
    $('#next-article-button').button({
        icons:{primary:'icon-next-article'},
        disabled: true
    });
    $('#previous-article-button').button({
        icons:{primary:'icon-previous-article'},
        disabled: true
    });
    $('#edit-article-button').button({
        icons:{primary:'icon-edit-article'},
        disabled: true
    });
    $('#new-article-button').button({
        icons:{primary:'icon-new-article'},
        disabled: false
    });
    $('#delete-coding-button, #delete-coding-button2').button({
        icons:{primary:'icon-delete-coding'},
        disabled: true
    });
    $('#copy-coding-button, #copy-coding-button2').button({
        icons:{primary:'icon-copy-coding'},
        disabled: true
    });
    $('#copy-switch-coding-button, #copy-switch-coding-button2').button({
        icons:{primary:'icon-copy-switch-coding'},
        disabled: true
    });
    $('#save-button, #save-button2').button({
        icons:{primary:'icon-save'},
        disabled: true
    });
    $('#save-continue-button, #save-continue-button2').button({
        icons:{primary:'icon-save-continue'},
        disabled: false
    });
    $('#irrelevant-button').button({
        icons:{primary:'icon-irrelevant-continue'}
    });
    
	$(".sentence-options .add-sentence-button").button({
        icons:{primary:'ui-icon-plus'}
    });
	$(".sentence-options .select-all-sentences-button").button({
        icons:{primary:'ui-icon-arrow-4-diag'}}
    );
	$(".sentence-options .split-sentences-button").button({
        icons:{primary:'ui-icon-scissors'}}
    );
    
    
    
    // $("#coding-type-radios").buttonset();
    // if(!annotator.articlecodings.containsArticleSchema || !annotator.unitcodings.containsUnitSchema){
        // $("#coding-type-radios").hide();
    // }
    if(!annotator.articlecodings.containsArticleSchema){
        $("#article-coding").hide();
    }
    if(!annotator.unitcodings.containsUnitSchema){
        $("#sentence-coding-table-part").hide();
    }
    if(!annotator.unitcodings.isNETcoding){ // only enable for net codings
        $('#copy-switch-coding-button, #copy-switch-coding-button2').hide();
    }
    
    //$('#new-article-button').hide(); // todo: make it work
    
    
    
    /*** set click events of buttons ***/
    $('#save-button, #save-button2').click(function(event){
        if($('#article-status').val() == STATUS_NOTSTARTED){
            $('#article-status').val(STATUS_INPROGRESS);
            annotator.commentAndStatus.onArticleStatusChange();
        }
        annotator.saveCodings();
    });
    $('#save-continue-button, #save-continue-button2').click(function(event){
        $('#article-status').val(STATUS_COMPLETE);
        annotator.commentAndStatus.onArticleStatusChange();
        annotator.saveCodings(true);
    });
    $('#irrelevant-button').click(function(event){
        $('#article-status').val(STATUS_IRRELEVANT);
        annotator.commentAndStatus.onArticleStatusChange();
        annotator.saveCodings(true);
    });
    $('#next-article-button').click(function(event){
        annotator.articletable.goToNextRow();
    });
    $('#delete-coding-button, #delete-coding-button2').click(function(event){
        $("#dialog-confirm-delete-row").dialog("open");
    });
    $('#copy-coding-button, #copy-coding-button2').click(function(event){
        annotator.unitcodings.copySelectedRow();
    });
    $('#copy-switch-coding-button, #copy-switch-coding-button2').click(function(event){
        annotator.unitcodings.copySelectedRow();
        annotator.unitcodings.switchSubjectObject();
    });
    $('#previous-article-button').click(function(event){
        annotator.articletable.goToPreviousRow();
    });
    // $('#article-coding-radio, #sentence-coding-radio, #both-coding-radio').click(function(){
        // if(!annotator.confirmArticleChange()) return;
        // annotator.codingTypeSet();
    // });
    
    $('#help-button').click(function(event){
        $("#dialog-help").dialog("open");
    });
    $(".sentence-options .add-sentence-button").click(annotator.showNewSentenceDialog);
    $(".sentence-options .split-sentences-button").click(annotator.showSplitArticleDialog);
    $(".sentence-options .select-all-sentences-button").click(function(){
        annotator.selectText($('.sentences').get(0));
    });
        
        
    /*** Initialize dialogs ***/
    
    $("#dialog-save").dialog({
        resizable: false,
        autoOpen: false,
        modal: true
    });
    $("#article-dialog-form").dialog({
        resizable: false,
        autoOpen: false,
        modal: true,
        open: function(){
            $('#article-edit-status').html('');
            $('#article-edit-form').show();
        },
        buttons: {
            "Save Article Details": function(){
                annotator.articletable.saveEditArticleDetails();
            },
            Cancel: function(){
                $(this).dialog("close");
            }
        }
    });
    $("#new-sentence-dialog-form").dialog({
        resizable: false,
        autoOpen: false,
        modal: true,
        open: function(){
            $('#new-sentence-status').html('');
        },
        buttons:{
            "Add new Sentence": function(){
                    annotator.saveNewSentenceDialog();
                },
                Cancel: function(){
                    $(this).dialog("close");
                }
        }
    });
        
    $("#message-dialog").dialog({
        resizable: false,
        autoOpen: false,
        modal: true,
        buttons: {
            "OK": function(){
                $(this).dialog("close");
            }
        }
     });
        
    $("#dialog-help").dialog({
        resizable: false,
        autoOpen: false,
        width:500,
        modal: true,
        buttons: {
            "OK": function(){
                $(this).dialog("close");
            }
        }
     });
    $("#dialog-confirm-delete-row").dialog({
        resizable: false,
        autoOpen: false,
        modal: true,
        buttons: {
            "Delete Row": function(){
                annotator.unitcodings.deleteSelectedRow();
                $(this).dialog("close");
            },
            Cancel: function(){
                $(this).dialog("close");
            }
        }
     });
        
    $('#edit-article-button').click(function(){
        $("#article-dialog-form").dialog("option", "title", "Edit article");
        annotator.articletable.showEditArticleDialog(annotator.articleid);
    });

    $('#new-article-button').click(function(){
        $("#article-dialog-form").dialog("option", "title", "Add new article");
        annotator.articletable.showEditArticleDialog(0);
    });
  
    
    
    
    /*** misc initialization ***/
    
    $('#article-status').change(annotator.commentAndStatus.onArticleStatusChange);
    $('#article-comment').change(annotator.commentAndStatus.onCommentChange);
    
    
    $('#next-article-button').focus();
        
    annotator.checkWindowWidth();
    annotator.fields.initFieldData();
    
    $(window).bind('resize', function () {
        if(annotator.previousWidth != $(window).width()){
            annotator.articletable.articleTable.fnAdjustColumnSizing();
            //if(annotator.unitcodings.sentenceTable) annotator.unitcodings.sentenceTable.fnAdjustColumnSizing();
            
            annotator.checkWindowWidth();
            annotator.previousWidth = $(window).width();
            console.debug('resized to ' + $(window).width());
        }
    });
    
    
    $('#unitcoding-table input:text').live('focus', annotator.unitcodings.focusCodingRow);
    $('#unitcoding-table input:text').live('hover', function(){
        var el = $(this);
        if(el.val().length > 10){
            el.attr('title', el.val());
        } else if(el.hasClass('error') == false){
            el.removeAttr('title');
        }
    });

   
    
    $(window).bind('scroll', function(){
        if($(window).scrollTop() < 85){
            $('.article-part').css('position', 'absolute');
            //$('.article-part').css('top', '90px');
            //$('.article-part').css('height', ($(window).height() - 90) + 'px');
        } else {
            $('.article-part').css('position', 'fixed');
            $('.article-part').css('top', '5px');
            //$('.article-part').css('height', '100%');
        }
    });
    
    
    $(document).bind('keydown', 'ctrl+s', function(event){
        event.preventDefault();
        try{
            if($('#save-button').button("option", "disabled") == false){
                $('#save-button').click();
            }
        } catch(e){
            console.error('error', e);
        }
        return false;
    });
    
    
    $(document).bind('keydown', 'ctrl+down', function(event){
        var el = $(event.target);
        if(el.is('input, button') && el.parents('#unitcoding-table').length > 0){ // pressed in sentences table
            event.preventDefault();
            el.blur();
            el.parents('tr').find('.add-row-button').click();
            return false;
        }
    })
    $(document).bind('keydown', 'ctrl+shift+down', function(event){
         var el = $(event.target);
        if(el.is('input, button') && el.parents('#unitcoding-table').length > 0){ // pressed in sentences table
            event.preventDefault();
            el.blur();
            console.debug('ctrl + sift');
            var currentUnit = $('#unitcoding-table .row_selected input:first').val();
            var newUnit = annotator.getNextSentenceNumber(currentUnit);
            el.parents('tr').find('.add-row-button').trigger('click', newUnit);
            return false;
        }
    });
    $(document).bind('keydown', 'shift+down', function(event){
        var el = $(event.target);
        if(el.is('input, button') && el.parents('#unitcoding-table').length > 0){ // pressed in sentences table
            event.preventDefault();
            el.blur();
            $('#copy-coding-button').click();
            return false;
        }
    });
    $(document).bind('keydown', 'alt+down', function(event){
        var el = $(event.target);
        if(el.is('input, button') && el.parents('#unitcoding-table').length > 0){ // pressed in sentences table
            event.preventDefault();
            el.blur();
            $('#copy-switch-coding-button').click();
            return false;
        }
    });
    
    // $(document).bind('keydown', 'ctrl+a', function(event){ // disabled since it's annoying not able to select all text in an input (it has a button anyways)
        // event.preventDefault();
        // annotator.selectText($('.sentences').get(0));
        // return false;
    // });
} 
