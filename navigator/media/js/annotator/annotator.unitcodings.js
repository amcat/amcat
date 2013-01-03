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



annotator.unitcodings = {};
annotator.unitcodings.sentenceTable = null;
annotator.unitcodings.codedarticleid = 0;
annotator.unitcodings.newrowid = 0; // counter for new rows
annotator.unitcodings.fieldList = null;



annotator.unitcodings.writeSentenceCodingsTable = function(){
    annotator.unitcodings.createUnitCodingsTable(annotator.articleid)
    
    // no row selected, so disable these buttons
    annotator.unitcodings.enableToolbarButtons(false);
}

annotator.unitcodings.createUnitCodingsTable = function(articleid){
    $('#unitcoding-table').html('<tr><td></td></tr>');
    $('#unitcoding-table-loading').remove();
    $('<div class="table-loading" id="unitcoding-table-loading">Loading...</div>').insertAfter('#unitcoding-table');
    var url = "../codingjob/" + annotator.codingjobid + "/article/" + annotator.articleid + "/unitcodings";
    $.ajax({
        "url": url,
        "success": annotator.unitcodings.processUnitCodingsJson,
        "error": function(jqXHR, textStatus, errorThrown){
            console.log('Error loading URL', url);
            $('#unitcoding-table-loading').html('<div class="error">Error loading data for table from <a href="' + url + '">' + url + '</a></div>');
        },
        "dataType": "json"
    });
}

annotator.unitcodings.processUnitCodingsJson = function(json, showAllRows){
    annotator.unitcodings.emptyUnitcodingHtml = $(json.unitcodingFormTablerow);

    var theaderrow = $('<tr />');
    var theader = $('<thead />').append(theaderrow);
    var tbody = $('<tbody />');
    $.each(json.unitcodings.headers, function(i, header){
        if(i == 0) return; // ignore ID column
        theaderrow.append($('<th />').text(header));
    });
    theaderrow.append($('<th />').text(''));// last column is for 'add row' button

    //console.log(theaderrow, theader);
    $.each(json.unitcodings.rows, function(i, rowData){
        var row = $(json.unitcodingFormTablerow);
        $.each(rowData, function(j, col){
            if(j == 0){ // ID column
                $('input[name=codingid]', row).val(col);
            } else if(j == 1){ // unitid, needs to be converted to paragraph nr + sentence nr
                var sentence = annotator.findSentenceById(col);
                //console.log('sentence', sentence, col);
                col = sentence.unit;
                $('input[name=unit]', row).val(col);
            } else {
                $('input:text:eq(' + (j-1) + ')', row).val(col);
            }
        });
        //row.append($('<td />').append(annotator.unitcodings.createAddRowButtonHtml(rowData[0])));
        //console.log('adding row', row);
        tbody.append(row);
    });
    
    $('#unitcoding-table').empty().append(theader).append(tbody);
    //console.log($('#unitcoding-table'));
    annotator.unitcodings.setEventsOnUnitCodingRows($('#unitcoding-table'));
    
    $('#unitcoding-table-loading').remove();
    
    //annotator.unitcodings.initFixedHeader();

    
    if(json.unitcodings.rows.length == 0){ //no rows
        annotator.unitcodings.addSingleUnitCodingRow();
    }
}


// annotator.unitcodings.createAddRowButtonHtml = function(codingid){
    // return '<button class="add-row-button" title="Add a new row">Add</button><input type="hidden" name="codingid" value="' + codingid + '" />';
// }


annotator.unitcodings.showSentenceCodings = function(){
    //$('#coding-title').html('Sentence Codings');
    if(annotator.unitcodings.containsUnitSchema){
        $('#unitcoding-table-part').show();
        annotator.unitcodings.writeSentenceCodingsTable();
    }
}




annotator.unitcodings.hideSentenceCodings = function(){
    if(annotator.unitcodings.fixedheader){ // hack to keep DataTables fixedheader plugin working even if table is recreated
        $('.fixedHeader').remove();
        $(window).unbind('.fixedHeader');
        annotator.unitcodings.fixedheader.fnGetSettings().aoCache = [];
    }
    $('#unitcoding-table-part').hide();
}



/************* Sentence table *************/


annotator.unitcodings.onAddRowButtonClick = function(event, unitid){ //unitid is optional argument for new row unit value
    console.debug('click addrow', unitid);
    annotator.unitcodings.removeSentenceTextRow();
    
    var newRow = annotator.unitcodings.getEmptyUnitCodingRow(); // new data
    annotator.unitcodings.setEventsOnUnitCodingRows(newRow);
    
    var parentTr = $(this).parents('tr');
    parentTr.after(newRow);
    
    
    var newUnit = unitid || parentTr.find('input:first').val(); //specified unitid or same as current row
    var unitInput = newRow.find('input:first');
    unitInput.val(newUnit); // set unit value
    unitInput.focus();
}



annotator.unitcodings.deleteSelectedRow = function(){ // delete row from unit table
    annotator.unitcodings.removeSentenceTextRow();
    var selectedRow = $('#unitcoding-table .row_selected');
    
    var codingid = selectedRow.find('input[name=codingid]').val();
    if(codingid.substring(0,3) != 'new'){
        annotator.unitcodings.deletedRows.push(codingid);
        console.debug('deleted rows', annotator.unitcodings.deletedRows);
    }
    
    selectedRow.remove();
    annotator.unitcodings.modified = true;
    annotator.codingsAreModified(true);
    
    if($('#unitcoding-table tbody tr input').length == 0){ //no rows anymore
        annotator.unitcodings.addSingleUnitCodingRow();
    }
    
    // no row selected, so disable these buttons
    annotator.unitcodings.enableToolbarButtons(false); 
}


annotator.unitcodings.enableToolbarButtons = function(enable){
     $('#delete-coding-button, #copy-coding-button, #copy-switch-coding-button, #delete-coding-button2, #copy-coding-button2, #copy-switch-coding-button2').button("option", "disabled", !enable); 
}


annotator.unitcodings.addSingleUnitCodingRow = function(){ // used if table else would be empty
    var newRow = annotator.unitcodings.getEmptyUnitCodingRow(); // new data

    annotator.unitcodings.setEventsOnUnitCodingRows(newRow);
    
    $('#unitcoding-table tbody').html(newRow);
}


annotator.unitcodings.copySelectedRow = function(){
    var currentRow = $('#unitcoding-table .row_selected');
    currentRow.find('.add-row-button').click(); // create new row
    annotator.unitcodings.removeSentenceTextRow(); // is needed since adding a new row will most likely show it, then next() does not work correctly anymore
    var newRow = currentRow.next();
    newRow.find('input').each(function(){
        $(this).val(currentRow.find('input[name=' + $(this).attr('name') + ']').val());
    });
    newRow.find('input[name=codingid]').val('new-' + annotator.unitcodings.newrowid);
    annotator.unitcodings.newrowid++;
    annotator.unitcodings.modified = true;
    annotator.codingsAreModified(true);
    newRow.find('input:first').blur();
    newRow.find('input:first').focus();
}


annotator.unitcodings.findSentenceFieldIdByName = function(name){
    /*var result = null;
    $.each(annotator.unitcodings.fieldList, function(i, field){
        if(field.label == name){
            result = field.fieldname;
            return true;
        }
    });
    return result;*/
    var result = null;
    $.each(annotator.fields.fields, function(i, field){
        if(field.fieldname == name){
            result = 'field_' + field.id;
            return true;
        }
    });
    return result;
}

annotator.unitcodings.switchSubjectObject = function(){
    var subjectElName = annotator.unitcodings.findSentenceFieldIdByName('Subject');
    var objectElName = annotator.unitcodings.findSentenceFieldIdByName('Object');
    //console.debug(subjectElName, objectElName);
    var newRow = $('#unitcoding-table .row_selected'); // the newly copied row is the selected row (since when adding a row focus is put on new row)
    var subject = newRow.find('input[name=' + subjectElName + ']').val();
    var object = newRow.find('input[name=' + objectElName + ']').val();
    newRow.find('input[name=' + subjectElName + ']').val(object);
    newRow.find('input[name=' + objectElName + ']').val(subject);
}

annotator.unitcodings.getEmptyUnitCodingRow = function(){
    /*var rowNew = $('<tr />');
    $.each(annotator.unitcodings.fieldList, function(i, field){
        if(field.fieldname == 'addrow-9999') return true;
        rowNew.append($('<td />').append(field.construct(field.initial).html()));
    });*/
    var rowNew = annotator.unitcodings.emptyUnitcodingHtml.clone();
    //rowNew.append($('<td />').append(annotator.unitcodings.createAddRowButtonHtml('new-' + annotator.unitcodings.newrowid)));
    $('input[name=codingid]', rowNew).val('new-' + annotator.unitcodings.newrowid);
    annotator.unitcodings.newrowid++;
    return rowNew;
}



annotator.unitcodings.onAddRowButtonTab = function(event){
    if($(this).parents('tr').next().length == 0){ // last row of table, only then create new row
        event.preventDefault();
        var currentUnit = $('#unitcoding-table .row_selected input:first').val();
        var newUnit = annotator.getNextSentenceNumber(currentUnit);
        console.debug('tab on addrow button');
        $(this).trigger('click', newUnit);
    }
}

annotator.unitcodings.setEventsOnUnitCodingRows = function(el){ // el can be jQuery obj of row or full sentences table
    var addRowButton = el.find('.add-row-button');
    addRowButton.button({
        icons:{primary:'icon-add-row'}
    });
    
    addRowButton.bind('keydown', 'tab', annotator.unitcodings.onAddRowButtonTab);
    addRowButton.click(annotator.unitcodings.onAddRowButtonClick);
    
    annotator.fields.autocompletes.addAutocompletes(el);
    
    el.find('input').change(function(){annotator.unitcodings.onchangeSentenceCoding($(this))});
}


annotator.unitcodings.onchangeSentenceCoding = function(el){
    //console.debug('sentence coding', el.attr('name'), 'changed to', el.val());
    var codingid = el.parents('tr').find('input[name=codingid]').val();
    if(codingid.substring(0,3) != 'new'){
        if($.inArray(codingid, annotator.unitcodings.modifiedRows) == -1){
            annotator.unitcodings.modifiedRows.push(codingid);
        }
        console.debug('modified rows', annotator.unitcodings.modifiedRows);
    }
    annotator.unitcodings.modified = true;
    annotator.codingsAreModified(true);
}



annotator.unitcodings.removeSentenceTextRow = function(){
    $('#unitcoding-table .sentence-text-row').remove();
}


annotator.unitcodings.setSentence = function(){
    //console.debug('call setSentence');
    var currentRow = $('#unitcoding-table .row_selected');
    
    var unit = currentRow.find('input:first').val(); // find value of unit column input
    var unitid = currentRow.find('input:first').attr('id');
    $('.article-part .selected-sentence').removeClass('selected-sentence');
    if(unit.length >= 3){
        var sentence = annotator.findSentenceByUnit(unit);
        if(sentence.text){ // valid input
            $('#sentence-' + sentence.id).addClass('selected-sentence');
            $('.sentences').scrollTo($('#sentence-' + sentence.id), {offset:-150});
            
            if(!currentRow.prev().hasClass('sentence-text-row')){ // if sentence text not already visible
                var iColspan = currentRow.find('td').length;
                var newRow = document.createElement('tr');
                var nCell = document.createElement('td');
                nCell.colSpan = iColspan;
                newRow.className = "sentence-text-row";
                nCell.innerHTML = sentence.text;
                newRow.appendChild(nCell);
                 $(newRow).insertBefore(currentRow);
            } else{
                currentRow.prev().find('td').html(sentence.text);
            }
        }
    }
}
 
annotator.unitcodings.focusCodingRow = function(){
    var currentRow = $(this).parents('tr');
    
    if($('#unitcoding-table .row_selected').get(0) == currentRow.get(0)){
        //console.debug('same row');
        annotator.unitcodings.setSentence(); // still set current sentence, since 'unit' might be changed by user
        return;
    }
    $('#unitcoding-table .row_selected').removeClass('row_selected');
    currentRow.addClass('row_selected'); //mark current row
    
    //if($('#unitcoding-table tbody tr').length > 1){ // if only one row, make sure user cannot remove this one
        //$('#delete-coding-button').button("option", "disabled", false);
    //}
    annotator.unitcodings.enableToolbarButtons(true); 
    
    if(!currentRow.prev().hasClass('sentence-text-row')) annotator.unitcodings.removeSentenceTextRow();
    
    annotator.unitcodings.setSentence();
}


annotator.unitcodings.toolbarOffset = 35; //px toolbar height


annotator.unitcodings.updateTableHeaders = function(setWidth) {
    var $table = $('#unitcoding-table');
    var $toolbar = $('#unitcoding-table-top');
    var originalHeaderRow =  $(".tableFloatingHeaderOriginal", $table);
    var floatingHeaderRow =  $(".tableFloatingHeader", $table);
    var offset = $table.offset();
    var scrollTop = $(window).scrollTop();
    //console.log(scrollTop, offset.top, (offset.top - annotator.unitcodings.toolbarOffset), offset.top + $table.height())
    if ((scrollTop >= (offset.top - annotator.unitcodings.toolbarOffset)) && (scrollTop < offset.top + $table.height())) {
        floatingHeaderRow.css("visibility", "visible");
        
        $toolbar.css('position', 'fixed');

        if(setWidth){
            // Copy cell widths from original header
            $("th", floatingHeaderRow).each(function(index) {
                var cellWidth = $("th", originalHeaderRow).eq(index).css('width');
                $(this).css('width', cellWidth);
            });

            // Copy row width from whole table
            floatingHeaderRow.css("width", $table.css("width"));
            $toolbar.css('left', '6px');
            //$table.css('padding-top', annotator.unitcodings.toolbarOffset + 'px');
            $toolbar.css("width", $table.width() + 'px');
        }
    }
    else {
        floatingHeaderRow.css("visibility", "hidden");
        $toolbar.css('position', 'static');
       // $table.css('padding-top', '0px');
    }
}

annotator.unitcodings.initFixedHeader = function(){
    var $table = $('#unitcoding-table');
    
    var originalHeaderRow = $("#unitcoding-table thead tr");
    var clonedHeaderRow = originalHeaderRow.clone(false);
    
    //console.log($table, originalHeaderRow, clonedHeaderRow);
    
    originalHeaderRow.before(clonedHeaderRow);

    clonedHeaderRow.addClass("tableFloatingHeader");
    clonedHeaderRow.css("position", "fixed");
    clonedHeaderRow.css("top", annotator.unitcodings.toolbarOffset + "px");
    clonedHeaderRow.css("left", $table.offset.left);
    clonedHeaderRow.css("visibility", "hidden");
    clonedHeaderRow.css("z-index", "9999");

    originalHeaderRow.addClass("tableFloatingHeaderOriginal");
        
    annotator.unitcodings.updateTableHeaders(true);
    $(window).scroll(annotator.unitcodings.updateTableHeaders);
    $(window).resize(function(){annotator.unitcodings.updateTableHeaders(true)});
}

