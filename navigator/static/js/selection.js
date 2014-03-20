/*
###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################
*/

function curry (fn, scope) {
    var scope = scope || window;
    var args = [];

    for (var i=2, len = arguments.length; i < len; ++i) {
        args.push(arguments[i]);
    };

    return function() {
	    fn.apply(scope, args);
    };
}

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

amcat.selection = {};

amcat.selection.setMessage = function (msg, type) {
    type = (type === undefined) ? "info" : type;
    var dialog = $("#select-message").removeClass().addClass("message alert alert-{0}".f(type)).show();

    if (typeof(msg) === "string"){
        dialog.text(msg);
    } else {
        dialog.html(msg);
    }
};

amcat.selection.hideMessage = function () {
    return $('#select-message').hide();
};

amcat.selection.current_polls = {};
amcat.selection.modal_html =
    '<div class="message"></div>' +
    '<div class="progress">' +
        '<div class="progress-bar" role="progressbar" aria-valuenow="0" valuemin="0" aria-valuemax="100" style="width:0%;"></div>' +
    '</div>';

amcat.selection.modal = null;

amcat.selection.set_progress = function(percent){
    $(".progress-bar", amcat.selection.modal).attr("aria-valuenow", percent);
    $(".progress-bar", amcat.selection.modal).css("width", percent + "%");
};

amcat.selection.poll = function(task_uuid, callback, timeout, download){
    if (amcat.selection.modal === null){
        amcat.selection.modal = $("<div>").html(amcat.selection.modal_html).dialog({
            autoOpen : false, modal : true
        });
    }

    var modal = amcat.selection.modal;
    modal.dialog("open");

    $.ajax({
        url : "/api/v4/task?uuid=" + task_uuid,
        dataType : "json",
        success : function(data){
            var new_timeout = (timeout >= 3000) ? timeout : timeout + 500;
            var href = "/api/v4/taskresult/" + task_uuid;

            task = data["results"][0];
            if (!task["ready"] && task["status"] === "INPROGRESS" && task["progress"] !== null){
                $(".message", modal).text(task.progress.message);
                amcat.selection.set_progress(task.progress.completed);
                window.setTimeout(curry(amcat.selection.poll, this, task_uuid, callback, new_timeout, download), timeout);
            } else if (!task["ready"]){
                window.setTimeout(curry(amcat.selection.poll, this, task_uuid, callback, new_timeout, download), timeout);
            } else if (task["ready"] && task["status"] != "SUCCESS"){
                var msg = $("<div>");
                msg.append($("<a class='failure'>").attr("href", href).text("View error."));

                $.ajax({
                    url : href,
                    dataType : "text",
                    error: function (jqXHR, textStatus) {
                        $(".failure", msg).replaceWith($("<b>").text(jqXHR.responseText));
                        msg.parent().removeClass("alert-info").addClass("alert alert-danger");
                    }
                });

                msg.append($("<p class='failure-details'>").text("Task: {0}, status {1}. ".f(task_uuid, task["status"])));

                amcat.selection.setMessage(msg, "danger");
                amcat.selection.set_progress(0);
                modal.dialog("close");
            } else {
                if (download == true){
                    window.location = href;
                    modal.dialog("close");
                    return;
                }

                $.ajax({
                    url : "/api/v4/taskresult/" + task_uuid,
                    success : callback,
                    error : function(qXHR){
                        amcat.selection.setMessage('Error: ' + qXHR.responseText, "danger");
                    }
                });

                amcat.selection.set_progress(0);
                modal.dialog("close");
            }
        },
        error : function() {
            amcat.selection.setMessage('Error: polling task ' + task_uuid + ' failed.', "danger");
            amcat.selection.set_progress(0);
            modal.dialog("close");
        }
    });

};

amcat.selection.callWebscript = function(name, data, callBack, download){
    amcat.selection.hideMessage().show();
    var url = amcat.selection.apiUrl + 'webscript/' + name + '/run?delay=&project=' + amcat.selection.get_project();

    $.ajax({
      type: 'POST',
      url: url,
      success: function(data){
          amcat.selection.poll(data["task_uuid"], callBack, 200, download);
      },
      error: function(jqXHR, textStatus){
        console.log('error form data', textStatus);
        amcat.selection.setMessage('Error loading action ' + textStatus, "danger");
      },
      data:data,
      dataType: 'json'
    });
}


amcat.selection.getFormDict = function(){
    return amcat.getFormDict($('#hidden-form'));
}


/************************ Main initialization ************************/


$(document).ready(function(){
    amcat.selection.hideMessage();
    
    $('#id_projects').multiselect({
       selectedList: 6,
       noneSelectedText:'Select a Project',
       header:'',
       height:'auto',
       minWidth: 360,
       close: function(){
        //console.log('project close', $(this).val());
        var projectids = $(this).val();
        amcat.selection.setArticleSetAndMediaSelect(projectids);
       }
    }).multiselectfilter({filter: amcat.multiselectCheckIfMatches});
    
    amcat.selection.projectidsCache = $('#id_projects').val() || '';
    
    $('#id_articlesets').multiselect({
       selectedList: 6,
       minWidth: 360,
       noneSelectedText:'All Article Sets',
       header:'',
       height:'auto',
    }).multiselectfilter({filter: amcat.multiselectCheckIfMatches}); 
    
    $('#id_datetype').multiselect({
       selectedList: 1,
       noneSelectedText:'',
       minWidth:90,
       multiple:false,
       header:false,
       height:'auto',
       //classes:'datemenu',
       close: function(){
          var val = $('#id_datetype').val();
          console.log(val);
          if(val == 'all'){
            $('#date-start, #date-end').hide();
            $('#date-on').hide();
          } else if(val == 'on'){
            $('#date-start, #date-end').hide();
            $('#date-on').show();
          } else if(val == 'before'){
            $('#date-start').hide();
            $('#date-on').hide();
            $('#date-end').show();
          }else if(val == 'after'){
            $('#date-start').show();
            $('#date-end').hide();
            $('#date-on').hide();
          }else if(val == 'between'){
            $('#date-start, #date-end').show();
            $('#date-on').hide();
          }
       },
    });
    
    $('#id_mediums').multiselect({
       selectedList: 6,
       minWidth: 360,
       noneSelectedText:'All Mediums',
       header:'',
       height:'auto',
    }).multiselectfilter({filter: amcat.multiselectCheckIfMatches});
    
    
    $('#id_columns').multiselect({
       selectedList: 6,
       noneSelectedText:'Select Columns',
       header:false,
       height:200,
       minWidth:300
    });
    
    $("#tabs").tabs();
    
    
    $('#form-submit').button();
    $('#webscripts').buttonset();
    // $('#save-query-button').button();
    // $('#load-query-button').button();
    // $('#show-query-form-button').button().click(function(){
        // $('#query-form').show();
        // $(this).hide();
    // });
    
    $('.output-options').hide();
    
    $('#webscripts input').live('click', function(){
        $('.output-options').hide();
        $('#options-' + $(this).attr('id')).show();
    });
    
    
    $('#webscripts input:first, #webscripts label:first').trigger('click');
    //$('').trigger('click');
    //$('#options-list').show();
    
    
    $("#date-start > input").datepicker({
        changeMonth: true,
        changeYear: true,
        autoSize:true,
        dateFormat: 'dd-mm-yy',
        defaultDate: '-3m',
        firstDay:1,
        maxDate:'+1y',
        showOn:'focus',
    });
    $("#date-end > input").datepicker({
        changeMonth: true,
        changeYear: true,
        autoSize:true,
        dateFormat: 'dd-mm-yy',
        firstDay:1,
        maxDate:'+1y',
        showOn:'focus',
    });
    $("#date-on > input").datepicker({
        changeMonth: true,
        changeYear: true,
        autoSize:true,
        dateFormat: 'dd-mm-yy',
        firstDay:1,
        maxDate:'+1y',
        showOn:'focus'
    });
    
    
    $('#selectionform').submit(amcat.selection.onFormSubmit);
    $('iframe').load(amcat.selection.loadIframe);
    
    $('#help-link').click(amcat.selection.showQuerySyntaxHelp);
    
})

amcat.selection.get_project = function(){
    // This is fugly, I'm sorry..
    return (/[0-9]+/).exec(window.location.pathname)[0];
}

amcat.selection.onFormSubmit = function(event){
    amcat.selection.setMessage('Loading...');
    $('#query-time').empty();
    $('#select-result').empty();
    $('#form-errors').empty();
    $('iframe').hide();
    
    var name = $('input[name=webscriptToRun]:checked').attr("id"); // name of selected webscript to run
    amcat.selection.callWebscript(name, $("#selectionform").serialize(), amcat.selection.loadIframe);

    event.preventDefault();
    return true;
}


amcat.selection.loadIframe = function(data){ // this is the form submit response
    amcat.selection.hideMessage();
    $('iframe').hide();

    window.clearTimeout(amcat.selection.loadIframeTimeout);

    var json = data;
    if (data.html === undefined){
        json = {};
        if (typeof data == "string") {
            json_string = data;
        } else {
            json_string = $(this).contents().text();
        }

        try{
            json = jQuery.parseJSON(json_string);
        } catch(e){
            $('iframe').show().css('width','900px').css('height','600px');
            $('#select-result').html('<div class="error">Received an invalid JSON response</div>');
            return;
        }

    }

    if(json.html){
        $('#select-result').html(json.html);
        if($("#dialog-message").dialog('isOpen') == true){
            $("#dialog-message").dialog('close');

            if (json.doNotAddActionToMainForm !== true){            
                amcat.selection.addActionToMainForm(json.webscriptClassname, json.webscriptName);
            }
        }
    } else {
        if($("#dialog-message").dialog('isOpen') == true){
            //nothing needed?
        } else {
            $('#select-result').empty();
        }
    }

    if(json.error){
        var el = $("#dialog-message").dialog('isOpen') == true ? $('#dialog-message-status') : $('#select-result');
        console.log(json.error, el);
        el.show().html('<div class="error">Error found</div>').append($('<div />').text(json.error.message));
        if(json.error.fields){
            var ul = el.append('<ul />')
            for(var field in json.error.fields) {
                var errors = json.error.fields[field]
                ul.append($('<li />').text(field + ': ' + errors.join(', ')));
            }
        }
        if($("#dialog-message").dialog('isOpen')){
            amcat.selection.setDialogButtons();
        }
    }

    if(json.queries){
        //console.log('queries', json.queries);
        $.each(json.queries, function(i, query){
            //console.log(query[0], query[1]);
        });
    }

    if(json.querytime){
        $('#query-time').text(json.querytime + ' seconds')
    }
}





/************************ Action script functions ************************/


amcat.selection.addActionToMainForm = function(webscriptClassName, label){
    $("#webscripts").buttonset('destroy');
    $('#radio-additional-label').prev().remove();
    $('#radio-additional-label').remove();
    $("#webscripts").append($('<input />', {'type':"radio", id:webscriptClassName, name:"webscriptToRun", value:webscriptClassName, 'checked':true}));
    $("#webscripts").append($('<label />', {'for':webscriptClassName, 'id':'radio-additional-label'}).text(label));
    $("#webscripts").buttonset(); 
    var url = amcat.selection.apiUrl + 'webscript/' + webscriptClassName + '/form?project=' + amcat.selection.get_project();

    $.ajax({
      type: 'GET',
      url: url,
      success: function(data, textStatus, jqXHR){
        console.log('received form data for', webscriptClassName);//, data.substring(0,1000) + '..');
        $('.output-options').hide();
        $('#options-radio-additional').html(data).show();
      },
      error: function(jqXHR, textStatus){
        console.log('error form data', textStatus);
        amcat.selection.setMessage('Error loading action form ' + textStatus, "danger");
      },
      dataType: 'html'
    });
}

amcat.selection.submitAction = function(webscriptClassName, download){
    $('#dialog-message-content').children().appendTo('#hidden-form-extra'); // move form elements to hidden form (to submit everything)

    var output = $('#hidden-form select[name=output]').val();
    //console.log('output', output);
    if(output == undefined || output == 'json-html'){ // if output == csv for instance, these buttons should remain visible
        $('#dialog-message-status').html('<div class="loading">Loading..</div>');
        $("#dialog-message").dialog('option', 'buttons', {});
    }

    amcat.selection.callWebscript(webscriptClassName, $("#hidden-form").serialize(), amcat.selection.loadIframe, download);
    $("#dialog-message").dialog("close");

}

amcat.selection.setDialogButtons = function(){
    $("#dialog-message").dialog('option', 'buttons', {
        Ok: amcat.selection.submitActionWrapper,
        Cancel: function(){
            $(this).dialog('close');
        }
    });
}

amcat.selection.actionClick = function(webscriptClassName, el, download){
    var url = amcat.selection.apiUrl + 'webscript/' + webscriptClassName + '/form?project=' + amcat.selection.get_project();
    amcat.selection.submitActionWrapper = function(){
        amcat.selection.submitAction(webscriptClassName, download);
    }
    $('#dialog-message-status').empty();
    $.ajax({
      type: 'GET',
      url: url,
      success: function(data, textStatus, jqXHR){
        console.log('received form data for', webscriptClassName);//, data.substring(0,1000) + '..');
        $('#dialog-message-content').html(data);
        $("#dialog-message").dialog({
			modal: true,
            resizable: false,
            //height: 400,
            title: $(el).text(), // title of dialog should be the name of the script, which is found on the button text
			width: 450
		});
        amcat.selection.setDialogButtons();
      },
      error: function(jqXHR, textStatus){
        console.log('error form data', textStatus);
        amcat.selection.setMessage('Error loading action ' + textStatus, "danger");
      },
      dataType: 'html'
    });
}


/************************ Datatable functions ************************/

amcat.selection.sortLabels = function(a, b){ // very basic natural sort
    a = a.toLowerCase();
    var asplit = a.split(/([0-9]+)/g);
    b = b.toLowerCase();
    var bsplit = b.split(/([0-9]+)/g);
    for(var i=0; i<asplit.length; i++){
        var diff = parseInt(asplit[i], 10) - parseInt(bsplit[i], 10);
        if(isNaN(diff)){
            diff = asplit[i].localeCompare(bsplit[i]);
        }
        if(diff != 0){
            return diff;
        }
    }
    return 0;
}

jQuery.fn.dataTableExt.oSort['objid-asc']  = function(a,b) {
    return amcat.selection.sortLabels(a,b);
};
jQuery.fn.dataTableExt.oSort['objid-desc']  = function(a,b) {
    return amcat.selection.sortLabels(b,a);
};



/************************ Form functions ************************/


amcat.selection.projectidsCache = '';

amcat.selection.setArticleSetAndMediaSelect = function(projectids){
    if(!projectids || amcat.selection.projectidsCache.toString() == projectids.toString()){ // do not load data if nothing has changed or no project is selected
        return;
    }
    amcat.selection.projectidsCache = projectids;
    
    $('#id_articlesets, #id_mediums').find('option').remove();//.end().append('<option value="">Loading..</option>'); // remove the old options
    var msg;
    if(!projectids){
        msg = 'Please select a project first';
    } else {
        msg = 'Loading...';
    }
    $('#id_articlesets').multiselect('widget').find('.ui-multiselect-filter-msg').text(msg);
    $('#id_mediums').multiselect('widget').find('.ui-multiselect-filter-msg').text(msg);
    $("#id_articlesets, #id_mediums").multiselect('refresh');
    
    
    // TODO: switch to new API
    var seturl = amcat.selection.apiUrl + 'article%20sets?format=json&';
    $.each(projectids, function(i, projectid){
        seturl += 'project__id=' + parseInt(projectid) + '&';
    });
    
    var setOptions = function(jsonArray, selectEl){
        selectEl.find('option').remove(); // remove existing options
        jsonArray.sort(function(a, b){return a.id - b.id});
        $.each(jsonArray, function(i, obj){
            selectEl.append($('<option />').val(obj.id).text(obj.id + ' - ' + obj.name));
        });
        selectEl.multiselect('refresh');
        selectEl.multiselect('widget').find('.ui-multiselect-filter-msg').empty();
    }
    
    $.ajax({
      type: 'GET',
      url: seturl,
      success: function(jsonArray, textStatus, jqXHR){
         setOptions(jsonArray, $('#id_articlesets'));
      },
      error: function(jqXHR, textStatus){
        console.log('set error', textStatus);
        amcat.selection.setMessage('Error loading set data', "danger");
      },
      dataType: 'json'
    });
    
    var mediaurl = amcat.selection.apiUrl + 'media?format=json&';
    $.each(projectids, function(i, projectid){
        mediaurl += 'article__project__id=' + parseInt(projectid) + '&';
    });
    
    $.ajax({
      type: 'GET',
      url: mediaurl,
      success: function(jsonArray, textStatus, jqXHR){
            setOptions(jsonArray, $('#id_mediums'));
      },
      error: function(jqXHR, textStatus){
        console.log('medium error', textStatus);
        amcat.selection.setMessage('Error loading medium data', "danger");
      },
      dataType: 'json'
    });
}

amcat.selection.loadIframeTimeout = null;



amcat.selection.showQuerySyntaxHelp = function(){
    $("#dialog-syntax-help").dialog({
        modal: true,
        resizable: false,
        //height: 400,
        width: 700,
        buttons: {
            Ok: function(){
                $(this).dialog('close');
            }
        }
    });
    return false;
}


/************************ Aggregation script functions ************************/

amcat.selection.aggregation = {};

amcat.selection.aggregation.toggleTableGraph = function(){
    var text = $('#toggle-table-graph-button').text();
    if(text == 'Show Table'){
        amcat.selection.aggregation.createTable();
        $('#id_outputType').val('table');
        $('#toggle-table-graph-button').text("Show Graph");
    } else {
        amcat.selection.aggregation.createGraph();
        $('#id_outputType').val('graph');
        $('#toggle-table-graph-button').text("Show Table");
    }
}


amcat.selection.aggregation.createTable = function(){
    $('.output-table-wrapper').show();
    $('#output-chart').hide();
    $('#toggle-table-graph-button').button("option", "label", 'Show Graph');
    // used for table output
    
    if(amcat.selection.aggregation.createdTable == true) return;
    amcat.selection.aggregation.createdTable = true;
    
    $('#output-table').dataTable( {
        "aaData": amcat.selection.aggregation.tableData,
        "aoColumns": amcat.selection.aggregation.tableColumns,
        "bPaginate": false,
        "bLengthChange": false,
        "bFilter": false,
        "bSort": true,
        "bInfo": false
    } );
    
    // $('#output-table td').click(function(){
        // var td = $(this);
        // var x = td.parent().find('td:first');
        // var y = td
    // });
}

/*
 * Function called when a cell is clicked in aggregation-table
 */
amcat.selection.aggregation.click = function(x, y, count){
    console.log('click', x, y, count);
    var form_values = amcat.selection.getFormDict();
    var added_form_values = {};
    var title = count + ' ' + amcat.selection.aggregation.aggregationType + ' ';

    if (amcat.selection.aggregation.xAxis == "date"){
        var date_clicked = start_date = end_date = new Date(x);
        var datetype = amcat.selection.aggregation.dateType;
        if(datetype == "day"){
            added_form_values["datetype"] = "on";
            var on_date = start_date.getFullYear() + "-" + (start_date.getMonth() + 1) + "-" + start_date.getDate();
            added_form_values["on_date"] = amcat.selection.aggregation.reverseDateOrder(on_date);
            title += ' on ' + added_form_values['on_date'];
        } else if (!isNaN(x)){
            // Can't really figure out what's going on here, but it works? -- Martijn
            $.each(amcat.selection.aggregation.datesDict, function(i, dt){
                var _start = new Date(dt[0]);
                if(_start.getTime() == date_clicked.getTime()){
                    start_date = dt[0];
                    end_date = dt[1];
                }
            });
        } else {
            start_date = amcat.selection.aggregation.datesDict[x][0];
            end_date = amcat.selection.aggregation.datesDict[x][1];
        }

        // Only datetype == day results in a datetype which is not 'between'
        if (datetype != "day"){
            added_form_values["datetype"] = "between";
            added_form_values["start_date"] = amcat.selection.aggregation.reverseDateOrder(start_date);
            added_form_values["end_date"] = amcat.selection.aggregation.reverseDateOrder(end_date);
            title += ' between ' + added_form_values['start_date'] + ' and ' + added_form_values['end_date']
        }
    }

    if(amcat.selection.aggregation.xAxis == 'medium'){
        var mediumLabel = x
        var medium = parseInt(mediumLabel.split(' - ')[0], 10);
        added_form_values['mediums'] = medium;
        title += ' in medium ' + mediumLabel;
    }
    
    if(amcat.selection.aggregation.yAxis == 'medium'){
        var mediumLabel = y;
        var medium = parseInt(mediumLabel.split(' - ')[0], 10);
        added_form_values['mediums'] = medium;
        title += ' in medium ' + mediumLabel;
    }
    
    if(amcat.selection.aggregation.yAxis == 'searchTerm'){
        var query = amcat.selection.aggregation.labels[y];
        if (query === undefined) query = y;
        added_form_values['query'] = query;
        title += ' for search term &quot;' + query + '&quot;';
    }
    
    added_form_values['columns'] = ['article_id', 'date', 'medium_id', 'medium_name', 'headline'];
    added_form_values['outputTypeAl'] = 'table';
    added_form_values['output'] = 'html';
    added_form_values['length'] = 50;
    $.extend(form_values, added_form_values);
    $('.added-hidden-form-fields').remove();
    for(key in added_form_values){
        var values;
        if(typeof added_form_values[key] == "object"){
            values = added_form_values[key];
        } else {
            values = [added_form_values[key]];
        }
        $.each(values, function(i, value){
            $('#hidden-form').append($('<input />').attr({'type':'hidden', 'value':value, 'name':key, 'class':'added-hidden-form-fields'}));
        });
    }
    var data = $.param(form_values, true);
    $('#dialog-message-content').html('Loading..<div style="height:300px"></div>');
    $("#dialog-message").dialog({
        modal: true,
        resizable: false,
        title: 'Articles',
        width: 800,
        buttons:{
            Close: function(){
                $(this).dialog('close');
            }
        }
    });
    amcat.selection.callWebscript('ShowArticleList', data, function(html, textStatus, jqXHR){
        $('#dialog-message-content').html('<h3>' + title + '</h3>' + html);
     });
}

$.jqplot.eventListenerHooks.push(['jqplotClick', function(ev, gridpos, datapos, neighbor, plot) {
    if (neighbor) { // click on datapoint
        var count = neighbor.data[1];
        
        var y = plot.series[neighbor.seriesIndex].label;
        var x = plot.axes.xaxis.label == 'Medium' ? plot.data[neighbor.seriesIndex][neighbor.pointIndex][0] : neighbor.data[0];

        amcat.selection.aggregation.click(x, y, count);
    }
}]);


amcat.selection.aggregation.textToDate = function(dateStr){
    if(dateStr in amcat.selection.aggregation.datesDict){
        dateStr = amcat.selection.aggregation.datesDict[dateStr][0];
    }
    return Date.parse(dateStr);
}

amcat.selection.aggregation.reverseDateOrder = function(dateStr){
    if (dateStr.getFullYear) {
	return dateStr.getFullYear() + '-' + dateStr.getMonth() + '-' + dateStr.getDate();
    } else return dateStr;
}

amcat.selection.aggregation.createGraph = function(){
    $('.output-table-wrapper').hide();
    $('#output-chart').show();
    $('#toggle-table-graph-button').button("option", "label", 'Show Table');
    
    if(amcat.selection.aggregation.createdGraph == true) return;
    amcat.selection.aggregation.createdGraph = true;
    
    if(amcat.selection.aggregation.tableData.length < 2){
        $('#output-chart').html('Error: only one datepoint. Unable to create a graph for this. Please change your query');
        return;
    }
    
    var TITLE_LABEL = 'x';
    var series = [];
    var graphData = [];
    $.each(amcat.selection.aggregation.tableColumns, function(i, col){
        var id = col.mDataProp;
        if(id == TITLE_LABEL) return;
        series.push({label:col.sTitle});
        var line = [];
        $.each(amcat.selection.aggregation.tableData, function(j, row){
            var point = (amcat.selection.aggregation.xAxis == 'date') ? amcat.selection.aggregation.textToDate(row[TITLE_LABEL]) : row[TITLE_LABEL];
            line.push([point, row[id]]); // add data point
        });
        graphData.push(line);
    });
    

    if(amcat.selection.aggregation.xAxis == 'date'){
        amcat.selection.aggregation.plotLines(series, graphData);
    } else if(amcat.selection.aggregation.xAxis == 'medium'){
        amcat.selection.aggregation.plotBars(series, graphData);
    } else {
        throw new Exception('Invalid xAxis');
    }
}

amcat.selection.aggregation.plotBars = function(series, graphData){
    var plot1 = $.jqplot('output-chart', graphData, {
    //title:'Default Date Axis',
    legend:{
        show:true,
        placement:'outsideGrid',
        renderer: $.jqplot.EnhancedLegendRenderer
    },
    seriesDefaults:{
      renderer:$.jqplot.BarRenderer,
      rendererOptions: {
          // Put a 30 pixel margin between bars.
          //barMargin: 30,
          // Highlight bars when mouse button pressed.
          // Disables default highlighting on mouse over.
          //highlightMouseDown: true   
      }
    },
    axes:{
        xaxis:{
            label:'Medium',
            labelRenderer: $.jqplot.CanvasAxisLabelRenderer,
            tickOptions:{
                fontSize:'9pt',
                angle: 30
            },
            renderer:$.jqplot.CategoryAxisRenderer,
            tickRenderer: $.jqplot.CanvasAxisTickRenderer ,
            autoscale:true,
            pad:1
            //tickInterval:'1 month'
        },
        yaxis:{
            label:'Nxumber of ' + amcat.selection.aggregation.aggregationType,
            labelRenderer: $.jqplot.CanvasAxisLabelRenderer,
            tickOptions:{formatString:'%d'},
            min:0,
	    pad:1
        }
    },
    highlighter: {
        show: true,
        sizeAdjust: 7.5,
        tooltipContentEditor:   function(str, seriesIndex, pointIndex, plot){
            var medium = plot.data[seriesIndex][pointIndex][0]
            var value = str.split(', ')[1];
            return plot.series[seriesIndex].label + '<br />Medium: ' + medium + '<br />Number of ' + amcat.selection.aggregation.aggregationType + ': ' + value;
        }
      },
    series:series
  });
}

amcat.selection.aggregation.getTickInterval = function(numberOfPoints){
    var constant = (amcat.selection.aggregation.smallGraph == true) ? 3 : 7;
    var interval = Math.max(parseInt(numberOfPoints / constant), 1);
    if(amcat.selection.aggregation.dateType == 'quarter'){
        return (interval * 3) + ' month';
    }
    return interval + ' ' + amcat.selection.aggregation.dateType;
}

amcat.selection.aggregation.plotLines = function(series, graphData){
    
    var tickInterval = amcat.selection.aggregation.getTickInterval(graphData[0].length);
    console.log(tickInterval);

    var plot1 = $.jqplot('output-chart', graphData, {
    //title:'Default Date Axis',
    
    legend:{
        show:true,
        placement:'outsideGrid',
        renderer: $.jqplot.EnhancedLegendRenderer
    },
    axes:{
        xaxis:{
            label:'Date',
            labelRenderer: $.jqplot.CanvasAxisLabelRenderer,
            renderer:$.jqplot.DateAxisRenderer,
            tickOptions:{
                formatString:'%d-%m-%Y',
                fontSize:'9pt',
                angle: 30
            },
            tickRenderer: $.jqplot.CanvasAxisTickRenderer ,
            //autoscale:true,
            pad:0,
            padMin:0,
            padMax:0,
            tickInterval:tickInterval
            //numberOfTicks:10
        },
        yaxis:{
            label: (amcat.selection.aggregation.aggregationType=='association'?'Association':'Number of ' + amcat.selection.aggregation.aggregationType),
            labelRenderer: $.jqplot.CanvasAxisLabelRenderer,
            tickOptions:{formatString:(amcat.selection.aggregation.relative?'%1.1f':'%d')},
            min:0,
	    tickInterval: amcat.selection.aggregation.relative?0.1:null,
	    max: amcat.selection.aggregation.relative?1:null
        }
    },
    highlighter: {
        show: true,
        sizeAdjust: 8,
        tooltipContentEditor:   function(str, seriesIndex, pointIndex, plot){
            //console.log(str);
            var date = str.split(', ')[0];
            var value = str.split(', ')[1];
            return plot.series[seriesIndex].label + '<br />Date: ' + date + '<br />Number of ' + amcat.selection.aggregation.aggregationType + ': ' + value;
        }
      },
    series:series
  });

}
