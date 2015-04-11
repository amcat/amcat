"use strict";

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

String.prototype.capitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
}

function serializeForm(form){
    var formData = $(form).serializeObject();

    $.map($("input[type=checkbox]", form), function(input){
        var inputName = $(input).attr("name");
        formData[inputName] = input.checked;
    });

    return formData;
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


var AGGR_HASH_FUCNTIONS = {
    "equals": function (a, b) {
        return (a.id === undefined) ? (a === b) : (a.id === b.id && a.label === b.label);
    },
    "hashCode": function (aggr) {
        return (aggr.id === undefined) ? aggr.toString() : (aggr.id + "_" + aggr.label);
    }
}

/**
 * Provides convience functions for aggregation-data returned by server
 * @param data returned by server (json)
 */
function _Aggregation(data){
    //////////////////////
    // PUBLIC FUNCTIONS //
    //////////////////////
    this.transpose = function(){
        var aggr_dict = new Hashtable(AGGR_HASH_FUCNTIONS);

        var temp_column;
        this.aggr.each(function(row, row_data){
            row_data.each(function(column, article_count){
                temp_column = aggr_dict.get(column);

                if (temp_column === null){
                    aggr_dict.put(column, [[row, article_count]]);
                } else {
                    temp_column.push([row, article_count]);
                }
            });
        });

        var aggr_list = [];
        aggr_dict.each(function(k, v){ aggr_list.push([k, v]); });
        return Aggregation(aggr_list);
    };

    //////////////////////////////////////
    // PRIVATE INITIALISATION FUNCTIONS //
    //////////////////////////////////////
    this._getHashMap = function(){
        var aggr_dict = new Hashtable(AGGR_HASH_FUCNTIONS);

        $.map(data, (function(x_values){
            aggr_dict.put(x_values[0], new Hashtable(AGGR_HASH_FUCNTIONS));

            $.map(x_values[1], function(y_values){
                aggr_dict.get(x_values[0]).put(y_values[0], y_values[1]);
            });
        }).bind(this));

        return aggr_dict;
    }

    this._getColumns = function(aggr){
        var columns = new HashSet(AGGR_HASH_FUCNTIONS);

        $.each(aggr.values(), function(_, y_values) {
            $.each(y_values.keys(), function(_, x_key) {
                columns.add(x_key);
            });
        });

        return columns.values();
    }

    this._getColumnIndices = function(columns){
        var indices = new Hashtable(AGGR_HASH_FUCNTIONS);
        $.each(columns, indices.put);
        return indices;
    }

    ///////////////////////
    // PUBLIC PROPERTIES //
    ///////////////////////
    this.aggr = this._getHashMap();
    this.rows = this.aggr.keys();
    this.columns = this._getColumns(this.aggr);
    this.columnIndices = this._getColumnIndices(this.columns);

    ///////////////////////////////////////////
    // PUBLIC FUNCTIONS MAPPING TO HASHTABLE //
    ///////////////////////////////////////////
    this.get = this.aggr.get;
    this.size = this.aggr.size;


    return this;
}

var Aggregation = function(data){
    return _Aggregation.bind({})(data);
};

$((function(){
    var MAIN_SCRIPTS = ["summary", "aggregation", "association"];
    var DEFAULT_SCRIPT = "summary";
    var QUERY_API_URL = "/api/v4/query/";
    var SEARCH_API_URL = "/api/v4/search";
    var SELECTION_FORM_FIELDS = [
        "include_all", "articlesets", "mediums", "article_ids",
        "start_date", "end_date", "datetype", "on_date",
        "codebook_replacement_language", "codebook_label_language",
        "codebook", "query", "download"
    ];

    var SCRIPT_NAMES = {
        saveasset: "Save as set"
    };

    var HOTKEYS = {
        "ctrl_q": function(event){ $("#run-query").click(); }
    };

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
            articlesets: "sets", sets: "sets"
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

    function getSerie(aggr, x_key, x_type){
        var serie = { obj: x_key, name: value_renderer[form_data["y_axis"]](x_key) }

        if (x_type === "datetime"){
            serie.data = $.map(aggr.columns, function(column){
                return [[column, aggr.get(x_key).get(column) || 0]];
            });
        } else {
            serie.data = $.map(aggr.columns, function(column){
                return aggr.get(x_key).get(column) || 0;
            });
        }

        return serie;
    }

    var value_renderer = {
        "medium": function(medium){
            return medium.id + " - " + medium.label;
        },
        "set": function(articleset){
            return articleset.id + " - " + articleset.label;
        },
        "date": function(date){
            return moment(date).format("DD-MM-YYYY");
        },
        "total": function(total){
            return "Total";
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
        },
        set: function(form_data, value){
            return {sets: value.id}
        }
    };

    var renderers = {
        "application/json+clustermap+table": function(container, data){
            var table = renderers["text/csv+table"](container, data.csv);
            table.addClass("table-hover")

            $("tr", table).click(function(event){
                // Find column indices of relevant queries
                var columns = [];
                var tds = $("td", $(event.currentTarget)).toArray();
                tds.pop();

                $.each(tds, function(i, td){
                    if ($(td).text() == "1"){
                        columns.push(i);
                    }
                });

                // Resolve queries
                var queries = $.map(columns, function(column){
                    var query = $($("thead > th", table)[column]).text();
                    return data.queries[query];
                });

                articles_popup({query: "(" + queries.join(") AND (") + ")"});
            }).css("cursor","pointer");
        },
        "text/csv+table": function(container, data){
            var table_data = Papa.parse(data, {skipEmptyLines: true}).data;
            return renderers["application/json+table"](container, table_data);
        },
        "application/json+tables": function(container, data){
            $.map(data, function(table){
                var table_name = table[0];
                var table_data = table[1];
                var table_container = $("<div>");
                renderers["application/json+table"](table_container, table_data);
                $(table_container).prepend($("<h1>").text(table_name));
                $(container).append(table_container);
            });

            return container;
        },
        "application/json+table": function(container, table_data){
            var thead = $("<thead>").append(
                $.map(table_data[0], function(label){
                    return $("<th>").text(label);
                })
            );

            var tbody = $("<tbody>").append(
                $.map(table_data.slice(1), function(row){
                    return $("<tr>").append(
                        $.map(row, function(value){
                            return $("<td>").text(value);
                        })
                    )
                })
            );

            var table = $("<table class='table'>").append([thead, tbody])
            container.append(table);
            return table;
        },
        "application/json+crosstables": function(container, data){
            renderers["application/json+tables"](container, data);
            $("tr td:first-child", container).css("font-weight", "bold");
        },
        "application/json+clustermap": function(container, data){
            var img = $("<img>")
                .attr("src", "data:image/png;base64," + data.image)
                .attr("usemap", "#clustermap");

            var map = $("<map>").attr("name", "clustermap");

            // Store for each clickable coordinate its article id
            var area;
            $.map(data.coords, function(coord){
                area = $("<area>");
                area.attr("shape", "rect");
                area.attr("coords", coord.coords.join(","));
                area.attr("article_id", coord.article_id);
                area.data("article_id", coord.article_id);
                map.append(area);
            });

            // Add query for cluster each article is in
            $.each(data.clusters, function(_, cluster){
                $.each(cluster.articles, function(_, article_id){
                    map.find("[article_id=" + article_id + "]").data("query", cluster.query);
                });
            });

            // Register click event for each article
            $("area", map).click(function(event){
                articles_popup({term: {
                    label: $(event.currentTarget).data("query")
                }})
            });

            container.append(img).append(map);
        },
        "application/json+image+svg+multiple": function(container, data){
            console.log(data);
            console.log(typeof(data))
            $.map(data, function(table){
                var table_container = $("<div>");
                renderers["image/svg"](table_container, table[1]);
                $(table_container).prepend($("<h1>").text(table[0]));
                $(container).append(table_container);
            });

            return container;
        },
        "image/svg": function(container, data){
            return container.html(data);
        },
        "image/png+base64": function(container, data){
            container.append($("<img>").attr("src", "data:image/png;base64," + data));
        },
        /**
         * Inserts given html into container, without processing it further.
         */
        "text/html": function(container, data){
            return container.html(data);
        },
        "text/html+summary": function(container, data){
            container = renderers["text/html"](container, data);
            bottom(load_extra_summary);
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
                    heatmap_data.push([i, columnIndices[values[0].id||values[0]], values[1]])
                });
            });

            var x_renderer = value_renderer[form_data["x_axis"]];
            var y_renderer = value_renderer[form_data["y_axis"]];

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
                    categories: $.map(aggregation.getRowNames(), x_renderer)
                },
                yAxis: {
                    allowDecimals: false,
                    categories: $.map(aggregation.getColumns(), y_renderer)
                },
                series: [{
                    name: "x",
                    data: heatmap_data
                }]
            });
        },

        "text/json+aggregation+line": function(container, data){
            return renderers["text/json+aggregation+barplot"](container, data, "line");
        },


        "text/json+aggregation+scatter": function(container, data){
            return renderers["text/json+aggregation+barplot"](container, data, "scatter");
        },

        "text/json+aggregation+barplot": function(container, data, type){
            var x_type = getType(form_data["x_axis"]);
            var aggregation = Aggregation(data).transpose();
            var columns = aggregation.columns;

            type = (type === undefined) ? "column" : type;

            var chart = {
                title: "",
                chart: { zoomType: 'xy', type: type },
                xAxis: { allowDecimals: false, type: x_type},
                yAxis: { allowDecimals: false, title: "total", min: 0 },
                series: $.map(aggregation.rows, function(x_key){
                    return getSerie(aggregation, x_key, x_type);
                }),
                plotOptions: {
                    series: {
                        events:{
                            click: function(event){
                                var x_type = form_data["x_axis"];
                                var y_type = form_data["y_axis"];

                                var filters = {};
                                filters[y_type] = event.point.series.options.obj;
                                filters[x_type] = columns[event.point.x];

                                articles_popup(filters);
                            }
                        },
                    },
                }
            };

            // We need category labels if x_axis is not of type datetime
            if (x_type !== "datetime"){
                var renderer = value_renderer[form_data["x_axis"]];
                chart.xAxis.categories = $.map(columns, renderer);
            }

            container.highcharts(chart);

            // Show render warning
            var context_menu = $("g.highcharts-button > title:contains('context')", container).parent();
            var close = false;
            var notification = {
                text: 'If you decide to export an image, keep in mind the data is sent to highcharts.com' +
                ' for rendering purposes. ',
                type: 'info',
                icon: 'ui-icon ui-icon-locked',
                auto_display: false,
                history: false,
                stack: false,
                animate_speed: 0,
                opacity: 0.9,
                hide: false
            };

            $("title", context_menu).text("");
            var pnotify = new PNotify(notification);

            $(context_menu).mouseenter(function(event){
                pnotify.get().css({
                    'top': event.clientY + 12,
                    'left': event.clientX + 12 - 320
                });

                pnotify.open();
            }).mouseleave(function(){pnotify.remove()})
              .click(function(){pnotify.remove});
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
            var row_template, table, thead, tbody, renderer;
            var aggregation = Aggregation(data);

            // Adding header
            thead = $("<thead>").append($("<th>"));
            renderer = value_renderer[form_data["y_axis"]];
            $.map(aggregation.columns, function(column){
                thead.append($("<th>").text(renderer(column)).data("value", column));
            });

            // Adding rows. Using row templates to prevent lots of small inserts
            row_template = (new Array(aggregation.columns.length + 1)).join("<td></td>");
            row_template = "<tr><th></th>" + row_template + "</tr>";

            tbody = $("<tbody>");
            renderer = value_renderer[form_data["x_axis"]];

            $.map(aggregation.rows, function(row){
                var row_element = $(row_template);
                row_element.find("th").text(renderer(row)).data("value", row);

                var value;
                $.each(aggregation.columns, function(i, column){
                    // Check for float / integer. And wtf javascript, why not float type?!
                    value = aggregation.get(row).get(column) || 0;
                    value = (value % 1 === 0) ? value : value.toFixed(2);
                    row_element.find("td").eq(i).text(value);
                });

                tbody.append(row_element);
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

    function bottom(callback){
        $(window).scroll(function() {
            if($(window).scrollTop() + $(window).height() == $(document).height()) {
                $(window).off("scroll");
                callback();
            }
        });
    }

    function load_extra_summary(){
        $(".result .loading").show();
        var data = $(".result .row.summary").data("form");
        data["aggregations"] = false;
        data["offset"] = $(".result .articles > li").length;

        $.ajax({
            type: "POST", dataType: "json",
            url: get_api_url("summary"),
            data: data,
            headers: { "X-Available-Renderers": get_accepted_mimetypes().join(",") },
            traditional: true,
        }).done(function(data){
            // Form accepted, we've been given a task uuid
            Poll(data.uuid).result(function(data){
                $(".result .loading").hide();
                var articles = $(".articles > li", $(data));
                if (articles.length === 0) return;
                $(".result .articles").append(articles);
                bottom(load_extra_summary);
            });
        })

    };

    /**
     * Renders popup with a list of articles, based on given filters.
     * @param filters mapping { type -> filter }. For example:
     *        { medium : 1, date: 1402005600000 }
     */
    function articles_popup(filters){
        var data = $.extend({}, form_data);

        $.each(filters, function(type, value){
            if (elastic_filters[type] !== undefined){
                $.extend(data, elastic_filters[type](form_data, value));
            } else {
                data[type] = value;
            }
        });

        // HACK: If a specific set is requested by a user (by clicking on a table cell,
        // for example), override global articleset filter.
        if (filters.set !== undefined){
            delete data["articlesets"];
        }

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
        date_inputs.prop("disabled", true).addClass("hidden");
        $.each(dates_enabling[datetype_input.val()], function(i, selector){
            $("#dates").find("input[name=" + selector + "]").prop("disabled", false).removeClass("hidden");
        });

        if (datetype_input.val() == "all"){
            $("#dates .formatting-help").hide();
        } else {
            $("#dates .formatting-help").show();
        }
    }

    function script_changed(event){
        $(".query-submit .btn").addClass("disabled");
        $("#scripts .active").removeClass("active");
        $(event.target).addClass("active");

        var url = get_api_url($(event.target).attr("name"));

        $.ajax({
            "type": "OPTIONS", url: url, dateType: "json"
        }).done(script_form_loaded).error(function(){
            show_error("Could not load form due to unkown server error. Try again after " +
            "refreshing this page (F5).");
        });

        script_form.text("Loading script form..");
    }

    function script_form_loaded(data){
	$("#script-line").show();
        if (data.help_text) {
            $("#script-help").text(data.help_text);
            $("#script-help").show();
        } else {
	    $("#script-help").hide();
	}

        // Determine fields which are *NOT* in the normal selection form.
        // Btw: who the hello thought it would be a good idea to let inArray
        // return an *index*?!
        var fields = $.map(data.form, function(_, key){
            return $.inArray(key, SELECTION_FORM_FIELDS) === -1 ? key : undefined;
        });

        script_form.html("");
        $.each(fields, function(i, field_name){
            var row = $("<div>").addClass("row");
            var label = $("<label class='col-md-5'>").text(data.labels[field_name]);
            var widget = $("<div class='col-md-7'>").html(data.form[field_name]);

            var id = widget.children().first().attr("id");
            label.attr("for", id)

            script_form.append(row.append(label).append(widget));

            // Add help text
            var help_text = data.help_texts[field_name];
            if (help_text){
                var icon = $("<i class='glyphicon glyphicon-question-sign'>");
                widget.append(icon);
                icon.tooltip({title: help_text})
            }

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
        return $.inArray(outputType.split(";")[0], get_accepted_mimetypes()) === -1;
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
    function run_query(event) {
        event.preventDefault();
        $(window).off("scroll");
        $(".error").removeClass("error").tooltip("destroy");
        $("#global-error").hide();
        PNotify.removeAll();

        loading_dialog.modal({keyboard: false, backdrop: 'static'});
        progress_bar.css("width", 0);
        message_element.text(message_element.attr("placeholder"));

        form_data = $("form").serializeObject();
        $(".result .panel-body").html("<i>No results yet</i>");

        var script = scripts_container.find(".active")[0].id.replace("script_","")

        $.ajax({
            type: "POST", dataType: "json",
            url: get_api_url(script),
            data: serializeForm($("form")),
            headers: {
                "X-Available-Renderers": get_accepted_mimetypes().join(",")
            },
            traditional: true
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

    /**
     * Massages given data into a format easily parseable by renderers.
     */
    function prepare_data(data){
        // 'Total' is actually a 1D aggregation; we're fitting the data below to
        // look like it is a 2D aggregation.
        if (form_data["y_axis"] === "total"){
            data = $.map(data, function(values){
                return [[values[0], [["Total", values[1]]]]]
            })
        }

        return data;
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
                renderer(body, prepare_data(data));
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

    self.init_shortcuts = function initialise_shortcuts(){
        $.each(HOTKEYS, function(keys, callback){
            console.log(keys)
            $(document).delegate('*', 'keydown.' + keys, function(event){
                event.preventDefault();
                event.stopPropagation();
                callback(event);
            });
        })
    };


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
            var main_buttons = [];
            var other_buttons = [];

            $.each(data, function(name){
                if (MAIN_SCRIPTS.indexOf(name) === -1){
                    other_buttons.push(name);
                } else {
                    main_buttons.push(name);
                }
            });

            main_buttons.sort();
            main_buttons.reverse();
            other_buttons.sort();

            var button;
            $.each(main_buttons, function(i, name){
                button = $("<span>");
                button.attr("class", "btn btn-sm btn-default script");
                button.attr("id", "script_" + name);
                button.attr("name", name);
                button.text((SCRIPT_NAMES[name] || name).capitalize());
                $("#scripts .main-scripts").prepend(button);
            });

            var a;
            $.each(other_buttons, function(i, name){
                a = $("<a class='script' href='#'></a>");
                a.attr("id", "script_" + name);
                a.attr("name", name);
                a.text((SCRIPT_NAMES[name] || name).capitalize());

                $("#scripts .other-scripts").append(
                    $("<li class='dropdown'>").append(a)
                );
            });

            $("#scripts .main-scripts").show()
            $("#scripts .loading").hide();
            $("#scripts .script").click(script_changed);
            $("#script_summary").click();
        });
    }

    $(function(){
        init_dates();
        init_scripts();
        init_shortcuts();

        $("#run-query").click(run_query);
        $("#content > form").submit(run_query);
    });
}).bind({}));

