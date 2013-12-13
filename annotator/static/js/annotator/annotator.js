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

var annotator = {};


var STATUS_NOTSTARTED = 0;
var STATUS_INPROGRESS = 1;
var STATUS_COMPLETE = 2;
var STATUS_IRRELEVANT = 9;
var API_URL = "/api/v4/";

var EMPTY_INTVAL = "null";

annotator.article_id = 0;
annotator.sentences = null;
annotator.datatable = null;

annotator.articlecodings = {};
annotator.articlecodings.articleCodingForm = null;

annotator.commentAndStatus = {};

annotator.previousWidth = 0; // browser width


annotator.resetArticleState = function () { // set state of article to unmodified
    annotator.unitcodings.deletedRows = []; // list with codedsentence ids
    annotator.unitcodings.modifiedRows = []; // list with codedsentence ids
    annotator.articlecodings.modified = false;
    annotator.unitcodings.modified = false;
    annotator.commentAndStatus.modified = false;
};

annotator.get_api_url = function () {
    return annotator._get_api_url(annotator.project_id, annotator.codingjob_id);
};

annotator._get_api_url = function (project_id, codingjob_id) {
    return API_URL + "projects/" + project_id + "/codingjobs/" + codingjob_id + "/";
};


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

/*
 * Given model data ( [{ id : 5, prop1 : "asd", .. }] ), create a mapping with
 * the prop as key, and the object as value.
 */
annotator.map_ids = function (model_data, prop) {
    prop = (prop === undefined) ? "id" : prop;

    var _result = {};
    $.each(model_data, function (i, object) {
        _result[object[prop]] = object;
    });
    return _result;
};

annotator.resolve_id = function(obj, target_models, prop){
    var val = obj[prop];
    obj[prop] = (val === null) ? null : target_models[val];
};

/*
 * Some model objects contain foreign keys which are represented by
 * and id. This function resolves those ids to real objects.
 *
 * @param models: model objects which contain a foreign key
 * @param target_models: model objects which are targeted by the FK
 * @param prop: foreign key property
 */
annotator.resolve_ids = function(models, target_models, prop){
    $.each(models, function(obj_id, obj){
        annotator.resolve_id(obj, target_models, prop);
    });
};

/************* Article codings *************/
annotator.articlecodings.get_codingschemafield = function(input){
    var id = $(input).attr("id").split("article_codingschemafield_")[1];
    return annotator.fields.schemas[id];
};

/*
 * Sets intval attribute and sets correct label
 */
annotator.on_autocomplete_change = function(event, ui){
    var label, intval = EMPTY_INTVAL;

    console.log(ui, this)

    if (ui.item !== null){
        intval = ui.item.get_code().code;
        label = ui.item.label;
    }

    $(this).attr("intval", intval).val(label||"");
};

/*
 * Most of the times a 'choices' property is defined on schemafield
 * and it can be used directly. In case of a codebook split, however,
 * the available choices of the second input field are determined
 * by the first.
 *
 * This function contains the logic for ^ and can be given to
 * jQuery autocomplete as a 'source' parameter (indirectly, as
 * it takes two extra arguments input_element and choices).
 */
annotator.get_autocomplete_source = function(input_element, choices, request, callback){
    // Are we a codebook descendant?
    if (input_element.hasClass("codebook_descendant")){
        var parent_id = input_element.parent().find("input.codebook_root").attr("intval");
        if (parent_id === EMPTY_INTVAL) return callback([]);

        parent_id = parseInt(parent_id);
        choices = $.grep(choices, function(item){
            return item.get_code().code === parent_id;
        })[0].descendant_choices;
    }

    // Only display first 20 results (for performance)
    callback($.ui.autocomplete.filter(choices, request.term).slice(0, 20));
};

annotator.set_autocomplete = function(input_element, choices){
    return input_element.autocomplete({
        source : function(request, callback){
            annotator.get_autocomplete_source(input_element, choices, request, callback);
        },
        autoFocus: true,
        minLength: 0,
        change : annotator.on_autocomplete_change,
        select : annotator.on_autocomplete_change,
        delay: 5
    }).focus(function(){
        $(this).autocomplete("search", "");
    });
};

annotator.get_codebook_html = function(schemafield){
    var html = $("<div>");

    if(schemafield.split_codebook){
        var root = $("<input>");
        var descendant = $("<input>");
        var hidden = $("<input>").attr("intval", EMPTY_INTVAL).hide();

        root.addClass("codebook_root").attr("placeholder", "Root..").attr("intval", EMPTY_INTVAL);
        descendant.addClass("codebook_descendant").attr("placeholder", "Descendant..");
        descendant.attr("intval", EMPTY_INTVAL);
        hidden.addClass("codebook_value").addClass("coding");

        annotator.set_autocomplete(root, schemafield.choices);
        annotator.set_autocomplete(descendant, schemafield.choices);

        descendant.on("autocompletechange", function(event, ui){
            hidden.attr("intval", (ui.item === null) ? EMPTY_INTVAL : ui.item.get_code().code);
            hidden.trigger("change");
        });

        html.append(root).append(descendant).append(hidden);
    } else {
        var input = $("<input>").attr("intval", EMPTY_INTVAL).addClass("coding");
        annotator.set_autocomplete(input, schemafield.choices);
        html.append(input);

    }

    return html;
};

annotator.get_boolean_html = function(){
    return $("<input class='coding' type='checkbox'>").attr("intval", EMPTY_INTVAL).change(function(event){
        var input = $(event.currentTarget);
        input.attr("intval", input.is(":checked") ? 1 : 0).addClass("coding");
    });
};

annotator.get_quality_html = function(){
    return $("<input class='coding' type='number' step='0.5' min='-1' max='1'>")
        .attr("intval", EMPTY_INTVAL).addClass("coding")
        .change(function(event){
            var target = $(event.currentTarget);
            var value = parseFloat(target.val());
            target.attr("intval", Math.round(value * 10));
        });
};

annotator.get_number_html = function () {
    return $("<input class='coding' type='number'>").attr("intval", EMPTY_INTVAL).change(function (event) {
        var target = $(event.currentTarget);
        var value = parseInt(target.val());
        target.attr("intval", isNaN(value) ? EMPTY_INTVAL : value);
    });
};

/*
 * Generates, given a schemafield-object, an HTML element for the given
 * field. This includes autocompletes.
 */
annotator.articlecodings.get_schemafield_html = function (schemafield) {
    var widget, container;

    // Get 'base' input field, which will be wrapped with labels, etc.
    if (schemafield.fieldtype == SCHEMATYPES.TEXT) {
        widget = $("<input class='coding'>");
    } else if (schemafield.fieldtype === SCHEMATYPES.NUMBER) {
        widget = annotator.get_number_html();
    } else if (schemafield.fieldtype === SCHEMATYPES.BOOLEAN) {
        widget = annotator.get_boolean_html();
    } else if (schemafield.fieldtype === SCHEMATYPES.QUALITY) {
        widget = annotator.get_quality_html();
    } else if (schemafield.fieldtype === SCHEMATYPES.CODEBOOK){
        widget = annotator.get_codebook_html(schemafield);
    } else {
        throw "Unknown schemafieldtypeid: " + schemafield.fieldtype;
    }


    container = $("<td>").addClass("coding-container").attr("codingschemafield_id", schemafield.id);

    return $("<tr>")
        .append($("<td>").append($("<label>").text(schemafield.label)))
        .append(container.append(widget));
};

annotator.articlecodings.get_schemafields_html = function(schemafields, coding){
    var values = {};
    $.each(coding.values, function (coding_id, coding) {
        values[coding.field.id] = coding;
    });

    var html = $("<table>");
    $.each(schemafields, function(schema_id, schemafield){
        html.append(annotator.articlecodings.get_schemafield_html(schemafield));
    });
    return html;
};

/*
 * Called when codings
 */
annotator.articlecodings.codings_fetched = function(){

    // Check whether there is an articleschema for this codingjob
    if (annotator.fields.codingjob.articleschema === null) return;

    // Get schemafields belonging to this articleschema
    var articleschema = annotator.fields.codingjob.articleschema;
    var schemafields = filter(function(f){ return f.codingschema === articleschema }, annotator.fields.schemafields);
    schemafields.sort(function(f1, f2){ return f1.fieldnr - f2.fieldnr });

    var empty_coding = {
        id: null,
        codingschema: articleschema,
        article: annotator.article_id,
        sentence: null,
        comments: null,
        codingjob: annotator.fields.codingjob
    };

    // Collect article codings. If no codings are available, create a
    // new empty one.
    var codings = filter(function(c){ return c.sentence === null }, annotator.codings);
    if (codings.length === 0) codings.push(empty_coding);

    // Create html content
    var article_coding_el = $("#article-coding");
    article_coding_el.html(annotator.articlecodings.get_schemafields_html(schemafields, codings[0]));
    annotator.fields.add_rules(article_coding_el);
};

annotator.articlecodings.onchange = function (el) {
    console.debug('article coding', el.attr('name'), 'changed to', el.val());
    annotator.articlecodings.modified = true;
    annotator.set_codings_modified(true);
};


/************* state saving *************/
annotator.before_unload = function(){
    return 'You have unsaved changes. Are you sure you would like to close this page?'
};

annotator.set_codings_modified = function (enable) {
    $(window).unbind("beforeunload");
    $('#save-button, #save-button2').button("option", "disabled", !enable);

    if (enable){
        $(window).bind("beforeunload", annotator.before_unload);
    }
};

/*********** Comment & article status ***************/
annotator.commentAndStatus.onArticleStatusChange = function () {
    annotator.commentAndStatus.modified = true;
    annotator.set_codings_modified(true);
};


annotator.commentAndStatus.onCommentChange = function () {
    annotator.commentAndStatus.modified = true;
    annotator.set_codings_modified(true);
};


/************* Storing data *************/


annotator.setDialogSuccessButtons = function () {
    $("#dialog-save").dialog('option', 'buttons', {
        "Continue Editing": function () {
            annotator.resetArticleState();
            annotator.set_codings_modified(false);
            $(this).dialog("close");
        },
        "Go to next article": function () {
            annotator.resetArticleState();
            annotator.set_codings_modified(false);
            $(this).dialog("close");
            annotator.articletable.select_next_row();
        }
    });
    $('.ui-dialog-buttonpane button:first').focus();
};


annotator.setDialogFailureButtons = function () {
    $("#dialog-save").dialog('option', 'buttons', {
        "Return to Article": function () {
            // annotator.resetArticleState();
            // annotator.set_codings_modified(false);
            $(this).dialog("close");
        }
    });
    $('.ui-dialog-buttonpane button:first').focus();
};


annotator.saveCodings = function (goToNext) {
    var error = false;
    $.each($("input[null=false]"), function (i, input) {
        if (annotator.fields.get_value($(input)).length === 0) {
            annotator.showMessage('Codingschemafield ' + $("label", $(input).parent()).text() + " cannot be null");
            error = true;
        }
    });

    if (error) return;

    var storeDict = {};
    if (annotator.commentAndStatus.modified) {
        var comment = $('#article-comment').val();
        var status = $('#article-status').val();

        // set comment and status in article table
        var commentPos = annotator.articletable.articleTable.fnGetPosition($('#article-table-container').find('.row_selected td:nth-child(8)').get(0));
        var statusPos = annotator.articletable.articleTable.fnGetPosition($('#article-table-container').find('.row_selected td:nth-child(7)').get(0));
        annotator.articletable.articleTable.fnUpdate(comment, commentPos[0], commentPos[1]);
        annotator.articletable.articleTable.fnUpdate($('#article-status').find('option:selected').text(), statusPos[0], statusPos[1]);

        // console.debug('set comment', comment, aPos, aData[aPos[1]]);
        storeDict['commentAndStatus'] = {'comment': comment, 'status': status};
    }
    if (annotator.articlecodings.modified) {
        storeDict['articlecodings'] = {}; //amcat.getFormDict($('#article-coding-form'));
        $('#article-coding-form').find('input:text').each(function (j, input) {
            input = $(input);

            if (input.attr("skip_saving")) return;


            var value = input.val();
            var field = annotator.fields.getFieldByInputName(input.attr('name'));
            if (field.isOntology && field.split_codebook) {
                if (input.attr("root") === undefined) {
                    input = $('[root="' + input.get(0).id + '"]');
                }
            }
            var validationResult = annotator.validateInput(input, field);


            if (validationResult != true) {
                input.addClass("error");
                if (validationResult != false) { // validationResult is text with error message
                    console.debug('validation', validationResult);
                    input.attr('title', validationResult);
                }
                input.bind("focus", function () {
                    $(this).removeClass("error")
                });
                valid = false;
            } else {
                input.removeClass("error");
                storeDict['articlecodings'][input.attr('name')] = input.parent().children(":hidden").val() ? parseInt(input.parent().children(":hidden").val()) : input.val(); //{'text':input.val(), 'id':input.parent().children(":hidden").val(), 'name':input.attr('name')};
            }
        });
        console.log(storeDict['articlecodings']);
    }

    if ($('#unitcoding-table').length > 0 && annotator.unitcodings.modified) {
        var valid = true;
        var formjson = {'delete': annotator.unitcodings.deletedRows, 'modify': [], 'new': []};
        var hasAnyValue = false;
        $('#unitcoding-table').find('tbody tr').each(function (i, row) {
            var rowjson = {};
            rowjson['codingid'] = $(row).find('input[name=codingid]').val();
            //console.debug('check row', rowjson['codingid'])
            if (rowjson['codingid'] == undefined) return; // for row with sentence text
            $(row).find('input:text').each(function (j, input) {
                //console.debug(input);
                input = $(input);
                var value = input.val();
                var field = annotator.fields.getFieldByInputName(input.attr('name'));
                if (value.length > 0) {
                    hasAnyValue = true;
                }

                if (field.isOntology && field.split_codebook) {
                    console.log(input);
                    if (input.attr("root") === undefined) {
                        input = $('[root="' + input.get(0).id + '"]');
                    }
                    console.log(input);
                }

                //console.log(value, field, input.attr('name'));
                var validationResult = annotator.validateInput(input, field);

                if (validationResult != true) {
                    console.log(validationResult);
                    annotator.markInputError(input, validationResult || '');
                    valid = false;
                } else {
                    input.removeClass("error");
                    rowjson[input.attr('name')] = input.parent().children(":hidden").val() || input.val();//{'text':input.val(), 'id':input.parent().children(":hidden").val(), 'name':input.attr('name')};
                }
            });
            if (!valid) return;
            if ($.inArray(rowjson.codingid, annotator.unitcodings.modifiedRows) != -1) {
                formjson['modify'].push(rowjson);
            } else if (rowjson.codingid.substring(0, 3) == 'new') {
                formjson['new'].push(rowjson);
            } else { // unmodified sentence
                //console.debug('unmodified codedsentence', rowjson.codingid);
            }
        });
        if (!valid && $('#unitcoding-table').find('tbody tr').length == 1 && hasAnyValue == false) {
            //valid = true; // if there is only one row without any values added, it is still a valid sentence table (since completely empty)
            console.debug('ignoring empty sentence table');
        }
        else if (valid && (formjson['delete'].length > 0 || formjson['modify'].length > 0 || formjson['new'].length > 0)) {
            //$("#dialog-save").dialog("open");
            console.debug('valid sentence coding form');
            //var data = JSON.stringify(formjson);
            //console.debug(annotator.unitcodings.codedarticle_id, formjson);
            storeDict['unitcodings'] = formjson;


        } else if (!valid) {
            console.debug('invalid sentence coding form');
            $('#message-dialog-msg').text('Unable to save: An invalid entry has been found in Sentence Codings');
            $('#message-dialog').dialog('open');
            return;
        }
    }

    $("#dialog-save-msg").html('Saving...');
    $("#dialog-save").dialog("open");
    var data = JSON.stringify(storeDict);
    if (data == '{}') { // empty dict
        console.debug('no codings data to send');
        //return;
    }

    $.ajax({
        type: 'POST',
        url: "article/" + annotator.article_id + "/storecodings",
        data: data,
        success: function (json, textStatus, jqXHR) {
            console.debug('saved!' + json.response);
            if (json.response == 'ok') {
                annotator.resetArticleState();
                $("#dialog-save-msg").html('<h3>Successfully saved codings!</h3>');
                if (goToNext) {
                    $("#dialog-save").dialog("close");
                    annotator.articletable.select_next_row();
                } else {
                    for (var oldid in json.codedsentenceMapping) {
                        $('input[name="codingid"][value="' + oldid + '"]').val(json.codedsentenceMapping[oldid]);
                        console.debug('mapping sentenceid', oldid, 'to', json.codedsentenceMapping[oldid]);
                    }

                    annotator.set_codings_modified(false);
                    annotator.setDialogSuccessButtons();
                }
            } else {
                var errorMsg = '<h3>Error while saving, invalid form</h3>';
                if (json.id && json.fields) {
                    errorMsg += '<p>The fields in error are marked in red</p>';
                }
                if (json.message) {
                    errorMsg += '<p>' + json.message + '</p>'; // TODO: escape HTML, security issue
                }
                console.debug(errorMsg);
                $("#dialog-save-msg").html(errorMsg);
                annotator.setDialogFailureButtons();
                if (json.id) {
                    if (json.id == 'articlecodings') {
                        $.each(json.fields, function (name, errors) {
                            var el = $('input[name=' + name + ']');
                            annotator.markInputError(el, errors[0]);
                        });
                    } else if (json.id == 'commentAndStatus') {
                        $.each(json.fields, function (name, errors) {
                            var el = $('input[name=' + name + ']');
                            annotator.markInputError(el, errors[0]);
                        });
                    } else {
                        var row = $('input[value=' + json.id + ']').parents('tr').first();
                        $.each(json.fields, function (name, errors) {
                            var el = $('input[name=' + name + ']', row);
                            console.log(name, errors, el);
                            annotator.markInputError(el, errors[0]);
                        });
                    }
                }
            }
        }, error: function (jqXHR, textStatus, errorThrown) {
            console.debug('error!' + textStatus);
            $("#dialog-save-msg").html('<h3>Error while saving, server error</h3><p>' + textStatus + '</p><br />');
            annotator.setDialogFailureButtons();
        },
        dataType: 'json'
    });
};



annotator.markInputError = function (input, errorText) {
    input.addClass("error");
    input.attr('title', errorText);
    input.bind("focus", function () {
        $(this).removeClass("error")
    });
};


annotator.validateInput = function (input, field) {
    /* this will check if the text value of input and the related hidden input contain valid data (based on the allowed items of the field)
     it will also set the hidden value if it is outdated */
    var items = field.items;

    if (items.length == 0) {
        console.log('no items for autocomplete');
        return true;
    }

    var value = input.val();

    if (value == '') {
        input.parent().children(":hidden").val(''); // if text input is empty, hidden field should be cleared
        return true;
    }

    var id = input.parent().children(":hidden").val(); // value of hidden input

    var found = [];
    for (var i = 0; i < items.length; i++) {
        // martijn: why is label used as identifier??
        if (value === items[i].label) {
            if (id == items[i].value) return true;
            found.push(items[i]);
        }
    }

    if (found.length == 0) {
        return 'Value not found in list of allowed values';
    }

    if (found.length > 1) {
        return "More than one label found for " + value;
    }

    input.parent().children(":hidden").val(found[0].value);
    return true;

    // This is actually the correct response, but id's dont' get filled when initialising
    // this can happen.
    return "Hidden ID not correct, but label is. Bug?"
};


/************* General functions *************/



annotator.selectText = function (obj) {
    annotator.deselectText();
    if (document.selection) {
        var range = document.body.createTextRange();
        range.moveToElementText(obj);
        range.select();
    } else if (window.getSelection) {
        var range = document.createRange();
        range.selectNode(obj);
        window.getSelection().addRange(range);
    }
};

annotator.deselectText = function () {
    if (document.selection) {
        document.selection.empty();
    } else if (window.getSelection) {
        window.getSelection().removeAllRanges();
    }
};


annotator.showMessage = function (text) {
    $('#message-dialog-msg').text(text);
    $('#message-dialog').dialog('open');
};


annotator.findSentenceByUnit = function (unit) {
    return filter(function(s){ return s.get_unit() == unit }, annotator.sentences)[0];
};

annotator.findSentenceById = function (sentenceid) {
    return annotator.sentences[sentenceid];
};

annotator.stripIdAttribute = function (id) { // used for sentence numbers that contain dots. does not work as 'id' attributes..
    return id.replace(/\./g, '-')
};


// This function is not yet implemented
annotator.getNextSentenceNumber = function (sentencenumber) {
    var result = null;
    $.each(annotator.sentences, function (i, sentence) {
        if (sentence.get_unit() == sentencenumber) {
            //console.debug('sentences length', annotator.sentences.length,i+1);
            if (annotator.sentences.length > i + 1) {
                result = annotator.sentences[i + 1].get_unit();
                console.log('next unit found', result);
            }
            return false;
        }
    });
    if (result == null) console.debug('next sentence not found');
    return result;
};


// This function is not yet implemented
annotator.findNextAvailableSentences = function () {
    var availableSentencenrs = [];
    var parnr = 0;
    $.each(annotator.sentences, function (i, sentence) {
        parnr = sentence.parnr;
        var nextSentencenr = parnr + '.' + (sentence.sentnr + 1);
        var exists = false;
        $.each(annotator.sentences, function (j, sentence2) {
            if (sentence2.get_unit() == nextSentencenr) {
                exists = true;
                return true;
            }
        });
        if (!exists) {
            availableSentencenrs.push(nextSentencenr);
        }
    });
    availableSentencenrs.push((parnr + 1) + '.1');
    return availableSentencenrs;
};

annotator.sentences_fetched = function (sentences) {
    var html = $('<div />');
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

annotator.confirmArticleChange = function () {
    if (annotator.articlecodings.modified || annotator.unitcodings.modified || annotator.commentAndStatus.modified) {
        return confirm('You have unsaved changes. Are you sure you would like to change article?');
    }
    return true;
};


annotator.checkWindowWidth = function () {
    var widthMessage = 'Your browser width is lower than 1000 pixels. Please use a higher resolution for a better layout.';
    if ($(window).width() < 1000) {
        if ($('#messages:contains("' + widthMessage + '")').length == 0) { // message not already visible
            $('#messages').append('<div>' + widthMessage + '</div>')
        }
    } else {
        $('#messages').find('div:contains("' + widthMessage + '")').remove();
    }
};

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

    /*** set click events of buttons ***/
    $('#save-button, #save-button2').click(function(){
        if($('#article-status').val() == STATUS_NOTSTARTED){
            $('#article-status').val(STATUS_INPROGRESS);
            annotator.commentAndStatus.onArticleStatusChange();
        }
        annotator.saveCodings();
    });
    $('#save-continue-button, #save-continue-button2').click(function(){
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
        annotator.articletable.select_next_row();
    });
    $('#delete-coding-button, #delete-coding-button2').click(function(){
        $("#dialog-confirm-delete-row").dialog("open");
    });
    $('#copy-coding-button, #copy-coding-button2').click(function(){
        annotator.unitcodings.copySelectedRow();
    });
    $('#copy-switch-coding-button, #copy-switch-coding-button2').click(function(event){
        annotator.unitcodings.copySelectedRow();
        annotator.unitcodings.switchSubjectObject();
    });
    $('#previous-article-button').click(function(){
        annotator.articletable.select_previous_row();
    });

    $('#help-button').click(function(){
        $("#dialog-help").dialog("open");
    });
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
    });


    /*** misc initialization ***/
    
    $('#article-status').change(annotator.commentAndStatus.onArticleStatusChange);
    $('#article-comment').change(annotator.commentAndStatus.onCommentChange);
    
    
    $('#next-article-button').focus();
        
    annotator.checkWindowWidth();
    annotator.fields.initialise_fields();

    $("<div id='loading_fields'>Initialising fields, please wait..</div>" ).dialog({
      dialogClass: "no-close",
      modal : true,
      title : "Loading..."
    });

    $(window).bind('resize', function () {
        if(annotator.previousWidth != $(window).width()){
            annotator.datatable.fnAdjustColumnSizing();
            //if(annotator.unitcodings.sentenceTable) annotator.unitcodings.sentenceTable.fnAdjustColumnSizing();
            
            annotator.checkWindowWidth();
            annotator.previousWidth = $(window).width();
            console.debug('resized to ' + $(window).width());
        }
    });
    
    
    /*$('#unitcoding-table').find('input:text').live('focus', annotator.unitcodings.focusCodingRow);
    $('#unitcoding-table').find('input:text').live('hover', function(){
        var el = $(this);
        if(el.val().length > 10){
            el.attr('title', el.val());
        } else if(el.hasClass('error') == false){
            el.removeAttr('title');
        }
    });*/

    $(window).bind('scroll', function(){
        if($(window).scrollTop() < 85){
            $('.article-part').css('position', 'absolute');
        } else {
            $('.article-part').css('position', 'fixed');
            $('.article-part').css('top', '5px');
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
    
    
    $(document).bind('keydown', 'ctrl+down', function (event) {
        var el = $(event.target);
        if (el.is('input, button') && el.parents('#unitcoding-table').length > 0) { // pressed in sentences table
            event.preventDefault();
            el.blur();
            el.parents('tr').find('.add-row-button').click();
            return false;
        }
    });
    $(document).bind('keydown', 'ctrl+shift+down', function(event){
         var el = $(event.target);
        if(el.is('input, button') && el.parents('#unitcoding-table').length > 0){ // pressed in sentences table
            event.preventDefault();
            el.blur();
            console.debug('ctrl + sift');
            var currentUnit = $('#unitcoding-table').find('.row_selected input:first').val();
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

    $(document).bind("keydown", "ctrl+i", function(event){
        event.preventDefault();
        $("#irrelevant-button").click();
    });

    $(document).bind("keydown", "ctrl+d", function(event){
        event.preventDefault();
        $("#save-continue-button").click();
    });
};

/*
 * For all AJAX errors, display a generic error messages. This eliminates
 * lots of boiler-plate code in functions which use AJAX calls.
 */
$(document).ajaxError(function(event, xhr, ajaxOptions) {
    var message = "An erorr occured while requesting: " + ajaxOptions.url + ". " +
                  "Server responded: '" + xhr.status + " " + xhr.statusText + "'.";
    $("<div>").text(message).dialog({
      modal: true
    });
});