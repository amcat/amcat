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

var amcat = {}

if (!window.console){
    window.console = {log: function() {}, assert: function() {}, error: function() {}, debug: function(){}, trace: function(){}, info: function(){}};
}

if(!window.console.debug){
    window.console.debug = window.console.log; // fix for IE 7 (maybe 8?) debugging
}
if(!window.console.trace){
    window.console.trace = function(){window.console.log('trace not supported');};
}



/* Replace input-box with loading-image when clicked */
 $(function(){
	$("input[type=submit].nonajax").click(function(event){
		$(event.currentTarget).hide();
		$(event.currentTarget).parent().append('<img src="/media/img/misc/ajax-loading.gif" />');
	});
});


/* Enable multiselect */
$(function(){
   $.each($("select.multiselect"), function(i, el){
      el = $(el).multiselect({
         minWidth : 300,
         multiple : el.multiple,
         header : '',
         selectedList : 5
      }).multiselectfilter({filter: amcat.multiselectCheckIfMatches});

   });
   
});

function confirm_dialog(event) {
        event.preventDefault();
       
        var dialog = $('' +
            '<div class="modal hide fade">' +
                '<div class="modal-header">' +
                        '<button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>' +
                        '<h3 class="noline">Irreversible action</h3>' +
                '</div>' +
                '<div class="modal-body">' +
                '<p>' + $(event.currentTarget).attr("data-confirm")  + '</p>' +
                '</div>' +
                '<div class="modal-footer">' +
                    '<a href="#" class="btn cancel-button">Cancel</a>' +
                    '<a href="' +  $(event.currentTarget).attr("href") + '" class="btn btn-danger">Proceed</a>' +
                '</div>' +
            '</div>').modal("show");

        $(".cancel-button", dialog).click((function(){
            this.modal("hide");
        }).bind(dialog))
}


/* For <a> with a class 'confirm', display confirmation dialog */
$(function(){$("a.confirm").click(confirm_dialog);});


amcat.multiselectCheckIfMatches = function(event, matches){
    // used in the multiselects. Shows error message when no match is found in the filtering
    if( !matches.length ){
       $(event.target).multiselect('widget').find('.ui-multiselect-filter-msg').text('No matches found!');
    } else {
        $(event.target).multiselect('widget').find('.ui-multiselect-filter-msg').empty();
    }
}


amcat.doDatatableServerRequest = function(sSource, aoData, fnCallback, serverData){
    var values = serverData;
    var dataTableValues = {}

    $.each(aoData, function(i, obj){
        dataTableValues[obj.name] = obj.value;
    });

    values['start'] = dataTableValues['iDisplayStart'];
    values['length'] = dataTableValues['iDisplayLength'];
    values['sortColumnNr'] = dataTableValues['iSortCol_0']; 
    values['sortOrder'] = dataTableValues['sSortDir_0'];
    values['sEcho'] = dataTableValues['sEcho'];
    values['search'] = dataTableValues['sSearch'];

    var data = $.param(values, true);
    
    $.ajax( {
        dataType: 'json',
        type: "POST",
        url: sSource,
        data: data,
        success: function(data, textStatus, jqXHR){
            //data['sEcho'] = dataTableValues['sEcho'];
            console.log(data);
            fnCallback(data, textStatus, jqXHR);
        },
        error:function(jqXHR, textStatus, errorThrown){
            console.error(textStatus, errorThrown);
            throw new Exception('Error loading additional data');
        }            
    } );
}


amcat.createTableHeaders = function(columns){
    var thead = $('<thead />');
    var theadtr = $('<tr />').appendTo(thead);
    $.each(columns, function(i, col){
        theadtr.append($('<th>').text(col));
    });
    return thead;
}


amcat.createTable = function(jqueryElement, url, columns, additionalServerData, additionalDataTableOptions, oncreate){
    var columnTitles = $.map(columns, function(col, i){ return col[1]});
    var columnFields = $.map(columns, function(col, i){ return col[0]});
    var columnDict = $.map(columns, function(col, i){ return col.length > 2 ? col[2] : {}});

    var serverData = {};
    serverData['columns'] = columnFields.join(',');
    serverData['length'] = 5000;
    serverData['output'] = 'datatables';
    $.extend(serverData, additionalServerData);
    
    jqueryElement.html('<div class="loading">Loading table</div>');
    
    var data = $.param(serverData, true);
    $.ajax( {
        dataType: 'json',
        type: "POST",
        url: url,
        data: data,
        success: function(data, textStatus, jqXHR){
            jqueryElement.html('<table cellpadding="0" cellspacing="0" border="0" class="display"></table>');

            var columns = data['aoColumns'];
            $.each(columns, function(i, col){
                col['sTitle'] = columnTitles[i];
                $.extend(col, columnDict[i]);
            });

            var dataTableOptions = {
                'aoColumns':columns,
                'aaData': data['aaData'],
                "bScrollInfinite": true,
                "bLengthChange": false,
                "iDisplayLength":100,
                "sScrollY": "500",
                "bScrollCollapse": true,
                "bFilter": true,
                "bSort": true,
                "bInfo": false,
                'bAutoWidth':false,
                "bProcessing": false,
                "bServerSide": false
            }

            $.extend(dataTableOptions, additionalDataTableOptions);
            var dataTable = $('table', jqueryElement).dataTable(dataTableOptions);

            if('rowlink' in additionalDataTableOptions){
                dataTable.fnSetRowlink(additionalDataTableOptions['rowlink']).fnDraw();
            }

            $('.export-button', jqueryElement).click(function(){
                amcat.showTableExportForm($(this), url);
            });

            if(oncreate){
                oncreate(dataTable);
            }
        },
        error:function(jqXHR, textStatus, errorThrown){
            console.error(textStatus, errorThrown);
            throw new Exception('Error loading additional data');
        }            
    } );
}


amcat.showTableExportForm = function(buttonEl, url){
    buttonEl.after($('<div id="dialog-export" title="Export Table"></div>'));
    $('#dialog-export').dialog({
        autoOpen: true,
        height: 300,
        width: 350,
        modal: true,
        buttons: {
            "Export": function() {
                alert('export');
            },
            Cancel: function(){
                $(this).dialog('close');
            }
       }
   })
}

amcat.check_fetch_results = function(state){
    /*
     * Check (label) results gathered so far. If all labels are
     * fetched, build table.
     *
     * (Ugly code below..)
     */
    var done = true;

    $.each(state.ajax_call_results.options, function(fieldname, data){
        if (done === false) return;

        if (data === null | state.ajax_call_results.labels[fieldname] === null){
            done = false;
        }
    });

    if (done === false) return;
    
    // All request finisched begin formatting!

    /* Inline function :-(, so we don't waste globals  */
    var re = /\{([^}]+)\}/g;
    var format = function(s, args) {
      /* Python(ish) string formatting:
      * >>> format('{0}', ['zzz'])
      * "zzz"
      * >>> format('{x}', {x: 1})
      * "1"
      */
      return s.replace(re, function(_, match){ return args[match]; });
    }

    /*
     * For every fieldname do:
     *   For every row do:
     *     format according to given label
     */
    $.each(state.ajax_call_results.labels, function(fieldname, labels){
        $.each(state.data.results, function(i, obj){
            if (labels[obj[fieldname]] !== undefined){
                obj[fieldname + "_id"] = obj[fieldname];

                obj[fieldname] = format(
                    state.ajax_call_results.options[fieldname].label,
                    labels[obj[fieldname]]
                );
            }
        });
    });

    state.callback(state.data);
}

amcat.single_fetch_finished = function(data, textStatus, jqXHR){
    /*
     * Called when new labels are fetched.
     */
    var fieldname = this[0];
    var state = this[1];

    var data_by_id = {};
    $.each(data, function(i, obj){
	if (obj != null)
            data_by_id[obj.id] = obj;
    });



    state.ajax_call_results.labels[fieldname] = data_by_id;
    amcat.check_fetch_results(state);
}

amcat.fetch_labels = function(data, textStatus, jqXHR, callback, url){
    /*
     * Modifies 'data' so includes labels. This used the HTTP OPTIONS
     * feature of django-rest-framework.
     *
     * @data, textStatus, jqXHR: normal jQuery AJAX callback arguments
     * @callback: function called when data is correctly 'labeled'
     * @url: url used to fetch data (and thus the url to fetch OPTIONS)
     */
    var state = {
        data : data,
        callback : callback,
        requests_finished : false,
        options : null,
        ajax_call_results : {
            options : {
                // fieldname : fetched_data || null
            },
            labels : {
                // fieldname : fetched_data || null
            }
        },
    };

    $.ajax({
        url : url,
        dataType : "json",
        type : "OPTIONS",
        success : (function(opts){
            state.options = opts;  

            $.each(opts.fields, (function(field, fieldtype){
                if (fieldtype !== "ModelChoiceField" | opts.models[field] === undefined){
                    return;
                }

                // Register AJAX call in state variable
                state.ajax_call_results.options[field] = null;
                state.ajax_call_results.labels[field] = null;

                var ids = [];
                $.each(state.data.results, function(i, obj){
                    // Ignore NULL values (field is optional)
                    if (obj[field] === null) return;

                    ids.push(obj[field]);
                });

                // Get labels
                $.ajax(opts.models[field], {
                    success : amcat.single_fetch_finished.bind([field, state]),
                    type : "GET",
                    data : {
                        id : ids,
                        format : "json",
                        paginate : false
                    },
                    traditional : true
                });

                // Get options
                $.ajax(opts.models[field], {
                    success : (function(data){
                        this[1].ajax_call_results.options[this[0]] = data;
                        amcat.check_fetch_results(this[1]);
                    }).bind([field, state]),
                    type : "OPTIONS"
                });

            }));

            // If no labels need to be fetched, also render table
            amcat.check_fetch_results(state);
        })
    });
}


amcat.createServerSideTable = function(jqueryElement, url, columns, serverData, additionalDataTableOptions){
    var columnTitles = $.map(columns, function(col, i){ return col[1]});
    var columnFields = $.map(columns, function(col, i){ return col[0]});
    console.log(columnTitles, columnFields);
    jqueryElement.append(amcat.createTableHeaders(columnTitles));
    serverData['columns'] = columnFields.join(',');
    var aoColumns = [];
    $.each(columns, function(i, col){
        aoColumns.push({'sName':columnFields[i]});
    });

    var dataTableOptions = {
        "bScrollInfinite": true,
        "bLengthChange": false,
		"aoColumns":aoColumns,
        "iDisplayLength":100,
        "sScrollY": "500",
        "bScrollCollapse": true,
        "bFilter": false,
        "bSort": true,
        "bInfo": false,
        "bProcessing": true,
        "bServerSide": true,
        //"iDeferLoading": 99999,
        "sAjaxSource": url,
        "fnServerData": function(sSource, aoData, fnCallback){
            amcat.doDatatableServerRequest(sSource, aoData, fnCallback, serverData)
        }
    }

    jQuery.extend(dataTableOptions, additionalDataTableOptions);
    var dataTable = jqueryElement.dataTable(dataTableOptions);

    if('rowlink' in additionalDataTableOptions){
      dataTable.fnSetRowlink(additionalDataTableOptions['rowlink']);
      console.log(' added rowlink', additionalDataTableOptions['rowlink']);
    }

    return dataTable;
}



amcat.getFormDict = function(form){
    // code from http://stackoverflow.com/questions/1184624/serialize-form-to-json-with-jquery
    var o = {};
    var a = form.serializeArray();
    $.each(a, function() {
        if (o[this.name] !== undefined) {
            if (!o[this.name].push) {
                o[this.name] = [o[this.name]];
            }
            o[this.name].push(this.value || '');
        } else {
            o[this.name] = this.value || '';
        }
    });
    return o;
}


