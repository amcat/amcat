define([
    "jquery", "renderjson", "query/utils/aggregation",
    "query/utils/poll", "moment", "query/utils/articlemodal", "query/valuerenderers",
    "highcharts/highcharts", "highcharts.data",
    "highcharts.heatmap", "highcharts.exporting",
    "papaparse", "highlight"
    ], function($, renderjson, Aggregation, Poll, moment, articles_popup, value_renderers){
    var renderers = {};

    function getType(axis){
        return (axis === "date") ? "datetime" : "category";
    }

    function getSerie(form_data, aggr, x_key, x_type){
        var serie = { obj: x_key, name: value_renderers[form_data["y_axis"]](x_key) };

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

    function bottom(callback){
        $(window).scroll(function() {
            if($(window).scrollTop() + $(window).height() == $(document).height()) {
                $(window).off("scroll");
                callback();
            }
        });
    }

    function get_accepted_mimetypes() {
        return $.map(renderers, function (_, mimetype) {
            return mimetype;
        });
    }

    function load_extra_summary(){
        $("#result").find(".loading").show();
        var data = $("#result").find(".row.summary").data("form");
        data["aggregations"] = false;
        data["offset"] = $("#result").find(".articles > li").length;

        $.ajax({
            type: "POST", dataType: "json",
            url: API.get_api_url("summary"),
            data: data,
            headers: { "X-Available-Renderers": get_accepted_mimetypes().join(",") },
            traditional: true
        }).done(function(data){
            // Form accepted, we've been given a task uuid
            Poll(data.uuid).result(function(data){
                $("#result").find(".loading").hide();
                var articles = $(".articles > li", $(data));
                if (articles.length === 0) return;
                $("#result").find(".articles").append(articles);
                bottom(load_extra_summary);
            });
        })

    }

    return $.extend(renderers, {
        "application/json+debug": function(form_data, container, data){
            renderjson.set_icons('', '');
            renderjson.set_show_to_level("all");
            var text = $(renderjson(data)).text().replace(/{...}|\[ ... \]/g, "");
            var code = $("<code class='json'>").text(text);
            $(container).append($('<pre style="background-color:#f8f8ff;">').append(code));
            hljs.highlightBlock($("pre", container).get(0));
        },
        "application/json+clustermap+table": function(form_data, container, data){
            var table = renderers["text/csv+table"](container, data.csv);
            table.addClass("table-hover");

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

                articles_popup().show(form_data, {
                    query: "(" + queries.join(") AND (") + ")"
                });
            }).css("cursor","pointer");
        },
        "text/csv+table": function(form_data, container, data){
            var table_data = Papa.parse(data, {skipEmptyLines: true}).data;
            return renderers["application/json+table"](form_data, container, table_data);
        },
        "application/json+tables": function(form_data, container, data){
            $.map(data, function(table){
                var table_name = table[0];
                var table_data = table[1];
                var table_container = $("<div>");
                renderers["application/json+table"](form_data, table_container, table_data);
                $(table_container).prepend($("<h1>").text(table_name));
                $(container).append(table_container);
            });

            return container;
        },
        "application/json+table": function(form_data, container, table_data){
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

            var table = $("<table class='table table-striped'>").append([thead, tbody]);
            container.append(table);
            return table;
        },
        "application/json+crosstables": function(form_data, container, data){
            renderers["application/json+tables"](form_data, container, data);
            $("tr td:first-child", container).css("font-weight", "bold");
        },
        "application/json+clustermap": function(form_data, container, data){
            var img = $("<img>")
                .attr("src", "data:image/png;base64," + data.image)
                .attr("usemap", "#clustermap");

            var map = $("<map>").attr("nam  e", "clustermap");

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
                articles_popup().show(form_data, {term: {
                    label: $(event.currentTarget).data("query")
                }})
            });

            container.append(img).append(map);
        },
        "application/json+image+svg+multiple": function(form_data, container, data){
            $.map(data, function(table){
                var table_container = $("<div>");
                renderers["image/svg"](form_data, table_container, table[1]);
                $(table_container).prepend($("<h1>").text(table[0]));
                $(container).append(table_container);
            });

            return container;
        },
        "image/svg": function(form_data, container, data){
            return container.html(data);
        },
        "image/png+base64": function(form_data, container, data){
            container.append($("<img>").attr("src", "data:image/png;base64," + data));
        },
        /**
         * Inserts given html into container, without processing it further.
         */
        "text/html": function(form_data, container, data){
            return container.html(data);
        },
        "text/html+summary": function(form_data, container, data){
            renderers["text/html"](form_data, container, data);
            bottom(load_extra_summary);
        },

        /**
         * Renders aggregation as stacked column chart
         *   http://www.highcharts.com/demo/heatmap
         */
        "text/json+aggregation+heatmap": function(form_data, container, data){
            var aggregation = Aggregation(data);
            var heatmap_data = [];
            var columnIndices = aggregation.getColumnIndices();

            $.each(data, function(i, row){
                $.each(row[1], function(_, values){
                    heatmap_data.push([i, columnIndices[values[0].id||values[0]], values[1]])
                });
            });

            var x_renderer = value_renderers[form_data["x_axis"]];
            var y_renderer = value_renderers[form_data["y_axis"]];

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

        "text/json+aggregation+line": function(form_data, container, data){
            return renderers["text/json+aggregation+barplot"](form_data, container, data, "line");
        },


        "text/json+aggregation+scatter": function(form_data, container, data){
            return renderers["text/json+aggregation+barplot"](form_data, container, data, "scatter");
        },

        "text/json+aggregation+barplot": function(form_data, container, data, type){
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
                    return getSerie(form_data, aggregation, x_key, x_type);
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

                                articles_popup().show(form_data, filters);
                            }
                        }
                    }
                }
            };

            // We need category labels if x_axis is not of type datetime
            if (x_type !== "datetime"){
                var renderer = value_renderers[form_data["x_axis"]];
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
        "text/json+aggregation+table": function(form_data, container, data){
            var row_template, table, thead, tbody, renderer;
            var aggregation = Aggregation(data);

            // Adding header
            thead = $("<thead>").append($("<th>"));
            renderer = value_renderers[form_data["y_axis"]];
            $.map(aggregation.columns, function(column){
                thead.append($("<th>").text(renderer(column)).data("value", column));
            });

            // Adding rows. Using row templates to prevent lots of small inserts
            row_template = (new Array(aggregation.columns.length + 1)).join("<td></td>");
            row_template = "<tr><th></th>" + row_template + "</tr>";

            tbody = $("<tbody>");
            renderer = value_renderers[form_data["x_axis"]];

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
            table = $("<table class='aggregation dataTable table-striped'>");
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
                    articles_popup().show(form_data, filters);
                }
            });

            return table;
        }
    });
});