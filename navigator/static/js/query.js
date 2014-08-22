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
function _Aggregation(data){
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
                // Some objects are (notably mediums and articlesets) are
                // represented as an object with properties 'id' and 'label'.
                columns[value[0].id || value[0]] = value[0];
            });
        });

        return $.map(columns, function(column){ return column; });
    };

    /**
     * Return mapping { column_name -> column_index }
     */
    this.getColumnIndices = function(){
        var columns = this.getColumns();
        var column_indices = {};

        $.each(columns, function(i, column){
            column_indices[column.id || column] = i;
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

Aggregation = function(data){
    return _Aggregation.bind({})(data);
};

$((function(){
    var DEFAULT_SCRIPT = "summary";
    var QUERY_API_URL = "/api/v4/query/";
    var SEARCH_API_URL = "/api/v4/search";
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

    /**
     * Convert form field / values to their search API counterpart. For
     * example:
     *     mediums -> mediumid
     *     query -> q
     * @param filters
     */
    function getSearchFilters(filters){
        var new_filters = {};

        var field_map = {
            mediums: "mediumid", query: "q", article_ids: "ids",
            start_date: "start_date", end_date: "end_date",
            articlesets: "sets"
        };

        var value_map = {
            ids: function(aids){ return $.map(aids.split("\n"), $.trim); },
            start_date: value_renderer.date,
            end_date: value_renderer.date
        };

        $.each(field_map, function(k, v){
            if (filters[k] === null || filters[k] === undefined || filters[k] === ""){
                return;
            }

            new_filters[v] = filters[k];
            if (value_map[v] !== undefined){
                new_filters[v] = value_map[v](new_filters[v]);
            }
        });

        return new_filters;
    }

    var value_renderer = {
        "medium": function(medium){
            return medium.id + " - " + medium.label;
        },
        "date": function(date){
            return moment(date).format("DD-MM-YYYY");
        },
        "total": function(total){
            return total;
        },
        "term": function(term){
            return term.id;
        }
    };

    var elastic_filters = {
        date: function(form_data, value){
            var range = QueryDates.merge([
                QueryDates.get_range_from_form(form_data),
                QueryDates.get_range(value, form_data["interval"])
            ]);

            return {
                datetype: "between",
                start_date: range.start_date,
                end_date: range.end_date
            };
        },
        medium: function(form_data, value){
            return {mediums: [value.id]};
        },
        total: function(){
            return {};
        },
        term: function(form_data, value){
            return {query: value.label};
        }
    };

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
        "text/json+aggregation+heatmap": function(container, data){
            var aggregation = Aggregation(data);
            var heatmap_data = [];
            var columnIndices = aggregation.getColumnIndices();

            $.each(data, function(i, row){
                $.each(row[1], function(_, values){
                    heatmap_data.push([i, columnIndices[values[0]], values[1]])
                });
            });

            container.highcharts({
                title: "",
                chart: { type: 'heatmap' },
                colorAxis: {
                    min: 0,
                    minColor: '#FFFFFF',
                    maxColor: Highcharts.getOptions().colors[0]
                },
                xAxis: {
                    allowDecimals: false,
                    type: "datetime",
                    categories: aggregation.getRowNames()
                },
                yAxis: {
                    allowDecimals: false,
                    type: "datetime",
                    categories: aggregation.getColumns()
                },
                series: [{
                    name: "x",
                    data: heatmap_data
                }]
            });
        },

        "text/json+aggregation+graph": function(container, data){
            var x_type = getType(form_data["x_axis"]);
            var chart = {
                title: "",
                chart: { type: 'column', zoomType: 'xy' },
                xAxis: { allowDecimals: false, type: x_type },
                yAxis: { allowDecimals: false, title: "total" },
                series: $.map(data, function(serie){
                    return {
                        type: 'column',
                        name: value_renderer[form_data["y_axis"]](serie[0]),
                        data: serie[1]
                    }
                })
            };

            // We need category labels if x_axis is not of type datetime
            var renderer = value_renderer[form_data["x_axis"]];
            if (x_type === 'category'){
                chart.xAxis.categories = $.map(Aggregation(data).getColumns(), renderer);
            }

            container.highcharts(chart);
        },

        /**
         * Renders aggregation as table. Each 'th' element has a data property 'value',
         * which can be used to access the original server data for that particular
         * element. For example, for a medium:
         *
         *    { id: 1, label: "test" }
         *
         * or a date:
         *
         *    1371160800000
         */
        "text/json+aggregation+table": function(container, data){
            var row_template, columns, column_indices, table, thead, tbody, row, renderer;

            var aggregation = Aggregation(data);
            columns = aggregation.getColumns();
            column_indices = aggregation.getColumnIndices();

            // Adding header
            thead = $("<thead>").append($("<th>"));
            renderer = value_renderer[form_data["y_axis"]];
            $.map(columns, function(column){
                thead.append($("<th>").text(renderer(column)).data("value", column));
            });

            // Adding rows. Using row templates to prevent lots of small inserts
            row_template = (new Array(columns.length + 1)).join("<td>0</td>");
            row_template = "<tr><th></th>" + row_template + "</tr>";

            tbody = $("<tbody>");
            renderer = value_renderer[form_data["x_axis"]];
            $.map(data, function(serie){
                row = $(row_template);
                row.find("th").text(renderer(serie[0])).data("value", serie[0]);

                var index;
                $.map(serie[1], function(value){
                    index = column_indices[value[0].id || value[0]];
                    row.find("td").eq(index).text(value[1]);
                });

                tbody.append(row);
            });

            // Putting it together
            table = $("<table class='aggregation dataTable'>");
            table.append(thead).append(tbody);
            container.html(table);

            // Register click event (on table)
            table.click(function(event){
                var td = $(event.target);
                if (td.prop("tagName") === "TD"){
                    var x_type = form_data["x_axis"];
                    var y_type = form_data["y_axis"];

                    var col = td.closest('table').find('thead th').eq(td.index());
                    var row = td.parent().children().eq(0);

                    var filters = {};
                    filters[x_type] = row.data('value');
                    filters[y_type] = col.data('value');
                    articles_popup(filters);
                }
            });

            return table;
        }
    };

    /**
     * Renders popup with a list of articles, based on given filters.
     * @param filters mapping { type -> filter }. For example:
     *        { medium : 1, date: 1402005600000 }
     */
    function articles_popup(filters){
        var data = $.extend({}, form_data);

        $.each(filters, function(type, value){
            $.extend(data, elastic_filters[type](form_data, value));
        });

        var dialog = $("#articlelist-dialog").modal("show");
        var table = dialog.find(".articlelist").find(".dataTables_scrollBody table");

        if (table.length > 0){
            table.DataTable().destroy();
        }

        amcat.datatables.create_rest_table(
            dialog.find(".articlelist").html(""),
            SEARCH_API_URL + "?" + $.param(getSearchFilters(data), true)
        )

    }

    function datetype_changed(){
        date_inputs.prop("disabled", true);
        $.each(dates_enabling[datetype_input.val()], function(i, selector){
            $("#dates").find("input[name=" + selector + "]").prop("disabled", false);
        });
    }

    function script_changed(){
        $(".query-submit .btn").addClass("disabled");
        var url = get_api_url($("select", scripts_container).val());
        $.ajax({
            "type": "OPTIONS", url: url, dateType: "json"
        }).done(script_form_loaded).error(function(){
            // TODO: fill in error
            show_error("Hallo =D");
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

        $(".query-submit .btn").removeClass("disabled");
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

    function form_invalid(data){
        // Add error class to all
        $.each(data, function(field_name, errors){
            $("[name=" + field_name + "]", $("form"))
                .addClass("error")
                .prop("title", errors[0])
                .data("toggle", "tooltip")
                .tooltip();

            if (field_name === '__all__'){
                var ul = $("#global-error").show().find("ul").html("");
                $.each(errors, function(i, error){
                    ul.append($("<li>").text(error));
                });
            }
        });

        loading_dialog.modal("hide");
        show_error("Invalid form. Please change the red input fields" +
            " to contain valid values.", true)
    }

    /*
     * Called when 'run query' is clicked.
     */
    function run_query() {
        $(".error").removeClass("error").tooltip("destroy");
        $("#global-error").hide();
        PNotify.removeAll();

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
        }).fail(function(jqXHR, textStatus, errorThrown){
            if(jqXHR.status === 400){
                // Form not accepted or other type of error
                form_invalid(JSON.parse(jqXHR.responseText));
            } else {
                // Unknown error
                show_jqXHR_error(jqXHR, errorThrown);
            }

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

    function show_jqXHR_error(jqXHR, error, hide){
        show_error(
            "Unknown error. Server replied with status code " +
            jqXHR.status + ": " + error
        );

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

