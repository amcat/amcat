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
function log(txt){
    console.log(txt);
}

/**
 * Shamelessly stolen from: http://stackoverflow.com/a/1186309
 */
$.fn.serializeObject = function()
{
    var o = {};
    var a = this.serializeArray();
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
};

/**
 * Provides convience functions for aggregation-data returned by server
 * @param data returned by server (json)
 * @param form_data form data at the time of submitting query
 */
function _Aggregation(form_data, data){
    /**
     * Get column names from aggregation data. Can be used as 'categories'
     * on a heapmap.
     *
     * @returns {*}
     */
    this.getColumns = function(){
        var columns = {};
        $.each(data, function(_, serie){
            $.each(serie[1], function(_, value){
                columns[value[0]] = null;
            });
        });

        return $.map(columns, function(_, column_name){
            return column_name;
        });
    };

    /**
     * Return mapping { column_name -> column_index }
     */
    this.getColumnIndices = function(){
        var columns = this.getColumns();
        var column_indices = {};
        $.each(columns, function(i, column_name){
            column_indices[column_name] = i;
        });
        return column_indices;
    };

    /**
     * Returns row names (first column of each row)
     */
    this.getRowNames = function(){
        return $.map(data, function(serie){
            return serie[0];
        });
    };

    return this;
}

Aggregation = function(form_data, data){
    return _Aggregation.bind({})(form_data, data);
};

$((function(){
    var DEFAULT_SCRIPT = "summary";
    var QUERY_API_URL = "/api/v4/query/";
    var SELECTION_FORM_FIELDS = [
        "include_all", "articlesets", "mediums", "article_ids",
        "start_date", "end_date", "datetype", "on_date",
        "codebook_replacement_language", "codebook_label_language",
        "codebook", "query", "download"
    ];

    var dates_enabling = {
        'all': [],
        'on': ['on_date'],
        'after': ['start_date'],
        'before': ['end_date'],
        'between': ['start_date', 'end_date']
    };

    var query_screen = $("#query-screen");
    var datetype_input = $("#id_datetype");
    var date_inputs = $("#dates").find("input");
    var scripts_container = $("#scripts");
    var script_form = $("#script-form");
    var loading_dialog = $("#loading-dialog");
    var message_element = loading_dialog.find(".message");
    var progress_bar = loading_dialog.find(".progress-bar");

    /**
     * At each query, data will be stored here to make sure we
     * can access form data as it were at the time of querying.
     */
    var form_data = null;

    var PROJECT = query_screen.data("project");
    var SETS = query_screen.data("sets");

    function getType(axis){
        return (axis === "date") ? "datetime" : "category";
    }

    var renderers = {
        /**
         * Inserts given html into container, without processing it further.
         */
        "text/html": function(container, data){
            container.html(data);
        },

        /**
         * Renders aggregation as stacked column chart
         *   http://www.highcharts.com/demo/heatmap
         */
        "text/json+aggregation+graph": function(container, data){
            // We get our data transposed! :)
            container.highcharts({
                title: "",
                chart: { type: 'column', zoomType: 'xy' },
                plotOptions: {
                    column: {
                        stacking: 'normal',
                        dataLabels: {
                            enabled: true,
                            color: (Highcharts.theme && Highcharts.theme.dataLabelsColor) || 'white',
                            style: { textShadow: '0 0 3px black, 0 0 3px black' }
                        }
                    }
                },
                xAxis: { allowDecimals: false, type: getType(form_data["x_axis"]) },
                yAxis: { allowDecimals: false, type: getType(form_data["y_axis"]) },
                series: $.map(data, function(serie){
                    return {
                        type: 'column',
                        name: serie[0],
                        data: serie[1]
                    }
                })
            });
        },

        /**
         * Renders aggregation as table.
         */
        "text/json+aggregation+table": function(container, data){
            var row_template, columns, column_indices, table, thead, tbody, row;

            var aggregation = Aggregation(form_data, data);
            columns = aggregation.getColumns();
            column_indices = aggregation.getColumnIndices();

            // Adding header
            thead = $("<thead>").append($("<th>"));
            $.map(columns, function(column_name){
                thead.append($("<th>").text(column_name));
            });

            // Adding rows. Using row templates to prevent lots of small inserts
            row_template = (new Array(columns.length + 1)).join("<td>0</td>");
            row_template = "<tr><th></th>" + row_template + "</tr>";

            tbody = $("<tbody>");
            $.map(data, function(serie){
                row = $(row_template);
                row.find("th").text(serie[0]);

                $.map(serie[1], function(value){
                    row.find("td").eq(column_indices[value[0]] + 1).text(value[1]);
                });

                tbody.append(row);
            });

            // Putting it together
            table = $("<table class='table table-striped table-condensed table-aggregation'>");
            table.append(thead).append(tbody);
            container.html(table);
            return table;
        }
    };

    function datetype_changed(){
        date_inputs.prop("disabled", true);
        $.each(dates_enabling[datetype_input.val()], function(i, selector){
            $("#dates").find("input[name=" + selector + "]").prop("disabled", false);
        });
    }

    function script_changed(){
        var url = get_api_url($("select", scripts_container).val());
        $.ajax({
            "type": "OPTIONS", url: url, dateType: "json"
        }).done(script_form_loaded).error(function(){
            // TODO: fill in error
            show_error("");
        });

        script_form.text("Loading script form..");
    }

    function script_form_loaded(data){
        script_form.html("");

        if (data.help_text) {
            script_form.append($("<div class='well'>").text(data.help_text));
        }

        // Determine fields which are *NOT* in the normal selection form.
        // Btw: who the hell thought it would be a good idea to let inArray
        // return an *index*?!
        var fields = $.map(data.form, function(_, key){
            return $.inArray(key, SELECTION_FORM_FIELDS) === -1 ? key : undefined;
        });

        $.each(fields, function(i, field_name){
            var row = $("<div>").addClass("row");
            var label = $("<label class='col-md-3'>").text(field_name);
            var widget = $("<div class='col-md-9'>").html(data.form[field_name]);
            script_form.append(row.append(label).append(widget));

            var is_hidden = widget.find("[type=hidden]").length;
            if (is_hidden) row.css("height", 0).css("overflow", "hidden");
        });
    }

    function get_api_url(action){
        action = (action === undefined) ? "" : action;
        var base_url = QUERY_API_URL + action + "?format=json&";
        return base_url + "project=" + PROJECT + "&sets=" + SETS.join(",");
    }

    function get_accepted_mimetypes(){
        return $.map(renderers, function(_, mimetype){ return mimetype; });
    }

    /**
     * Should we offer the user to download the result? I.e., can we expect the server to
     * inlcude the 'attachment' header?
     *
     * @returns boolean
     */
    function download_result(){
        var download = $("form [name=download]").is(":checked");

        if (download){
            // User explicitly indicated wanting to download
            return true;
        }

        // If we cannot render the selected output type, we should offer download option
        var outputType = $("form [name=output_type]").val();
        return $.inArray(outputType, get_accepted_mimetypes()) === -1;
    }

    /*
     * Called when 'run query' is clicked.
     */
    function run_query() {
        loading_dialog.modal({keyboard: false, backdrop: 'static'});
        progress_bar.css("width", 0);
        message_element.text(message_element.attr("placeholder"));

        form_data = $("form").serializeObject();
        $(".result .panel-body").html("<i>No results yet</i>");

        $.ajax({
            type: "POST", dataType: "json",
            url: get_api_url(scripts_container.find("select").val()),
            data: $("form").serialize(),
            headers: {
                "X-Available-Renderers": get_accepted_mimetypes().join(",")
            }
        }).done(function(data){
            // Form accepted, we've been given a task uuid
            init_poll(data.uuid);
        }).fail(function(){
            // Form not accepted or other type of error

        });
    }

    function init_poll(uuid){
        var poll = Poll(uuid, {download: download_result()});

        poll.done(function(){
            progress_bar.css("width", "100%");
            message_element.text("Fetching results..")
        }).fail(function(data, textStatus, _){
            show_error("Server replied with " + data.status + " error: " + data.responseText);
        }).result(function(data, textStatus, jqXHR){
            var contentType = jqXHR.getResponseHeader("Content-Type");
            var body = $(".result .panel-body").html("");
            var renderer = renderers[contentType];

            if(renderer === undefined){
                show_error("Server replied with unknown datatype: " + contentType);
            } else {
                renderer(body, data);
            }

        }).always(function() {
            loading_dialog.modal("hide");
        }).progress_bar(message_element, progress_bar);
    }

    function init_dates(){
        datetype_input
            // Enable / disable widgets
            .change(datetype_changed)
            // Compatability fix for Firefox:
            .keyup(datetype_changed)
            // Check initial value
            .trigger("change");
    }

    function show_error(msg, hide){
        new PNotify({type: "error", hide: (hide === undefined) ? false : hide, text: msg});
    }

    function init_scripts(){
        $.ajax({
            dataType: "json",
            url: QUERY_API_URL
        }).error(function(event){
            show_error(
                "Could not load scripts. Try to refresh this page and "
                + "try again. If the problem persists, please contact the "
                + "administrators."
            );
        }).done(function(data){
            var select = $("<select>");

            $.each(data, function(name, url){
                var option = $("<option>").text(name).val(name);

                //if (name === DEFAULT_SCRIPT){
                //    option.attr("selected", "selected");
                //}

                select.append(option);
            });

            scripts_container.html(select);
            select.change(script_changed)
                .keyup(script_changed).trigger("change");
        });
    }

    $(function(){
        init_dates();
        init_scripts();

        $("#run-query").click(run_query);
    });
}).bind({}));

