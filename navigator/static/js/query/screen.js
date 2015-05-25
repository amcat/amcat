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

var API = null;

define([
    "jquery", "query/multiselect-defaults", "query/utils/serialize",
    "query/renderers", "query/utils/poll", "query/api", "pnotify",
    "pnotify.nonblock", "query/query",
    "query/utils/format", "jquery.hotkeys", "jquery.depends", "bootstrap",
    "bootstrap-multiselect", "bootstrap-tooltip"
    ], function($, MULTISELECT_DEFAULTS, serializeForm, renderers, Poll, api, PNotify){
    var self = {};
    var form = $(this);

    var query_screen = $("#query-screen");

    var USER = $("#query-form").data("user");
    var PROJECT = query_screen.data("project");
    var SETS = $("#query-form").data("sets");
    API = api(PROJECT, SETS);

    var DEFAULT_SCRIPT = "summary";
    var SAVED_QUERY_API_URL = "/api/v4/projects/{project_id}/querys/{query_id}";
    var QUERY_API_URL = "/api/v4/query/";
    var SEARCH_API_URL = "/api/v4/search";
    var CODEBOOK_LANGUAGE_API_URL = "/api/v4/projects/{project_id}/codebooks/{codebook_id}/languages/";
    var SELECTION_FORM_FIELDS = [
        "include_all", "articlesets", "mediums", "article_ids",
        "start_date", "end_date", "datetype", "on_date",
        "codebook_replacement_language", "codebook_label_language",
        "codebook", "query", "download"
    ];

    var HOTKEYS = {
        "ctrl_q": function(event){ $("#run-query").click(); },
        "ctrl_r": function(event){ $("#new-query").click(); },
        "ctrl_shift_s": function(event){
            $("#save-query-dialog .save:visible").click();
            $("#save-query-as").click();
        },
        "ctrl_s": function(event){
            var save_query = $("#save-query");

            if (!save_query.hasClass("disabled")){
                save_query.click();
            } else {
                $("#save-query-as").click();
            }
        },
        "ctrl_o": function(event){
            $("#load-query > button").click();

        }
    };

    var dates_enabling = {
        'all': [],
        'on': ['on_date'],
        'after': ['start_date'],
        'before': ['end_date'],
        'between': ['start_date', 'end_date']
    };

    var datetype_input = $("#id_datetype");
    var date_inputs = $("#dates").find("input");
    var scripts_container = $("#scripts");
    var script_form = $("#script-form");
    var loading_dialog = $("#loading-dialog");
    var message_element = loading_dialog.find(".message");
    var progress_bar = loading_dialog.find(".progress-bar");
    var form_data = null;

    var saved_query = {
        id: $("#query-form").data("query"),
        name: null,
        private: true,
        user: null
    };

    /**
     * Massages given data into a format easily parseable by renderers.
     */
    self.prepare_data = function prepare_data(data){
        // 'Total' is actually a 1D aggregation; we're fitting the data below to
        // look like it is a 2D aggregation.
        if (form_data["y_axis"] === "total"){
            data = $.map(data, function(values){
                return [[values[0], [["Total", values[1]]]]]
            })
        }

        return data;
    };

    self.get_accepted_mimetypes = function get_accepted_mimetypes(){
        return $.map(renderers, function(_, mimetype){ return mimetype; });
    };

    self.hashchange = function hashchange(event){
        var hash;

        if(!location.hash || !location.hash.slice(1)){
            hash = DEFAULT_SCRIPT;
        } else {
            hash = location.hash.slice(1);
        }

        console.log(hash);

        $("#script_" + hash).click();
    };

    self.codebook_changed = function codebook_changed(event){
        var codebook_id = $(event.currentTarget).val();

        var url = CODEBOOK_LANGUAGE_API_URL.format({
            project_id: PROJECT,
            codebook_id: codebook_id
        });

        var keywordsAndIndicators = $("#keywords,#indicators");
        keywordsAndIndicators.html("");
        keywordsAndIndicators.multiselect("rebuild");

        if (codebook_id === ""){
            return;
        }

        keywordsAndIndicators.multiselect("setOptions", {
            nonSelectedText: "Loading options.."
        });

        keywordsAndIndicators.multiselect("rebuild");

        $.getJSON(url, function(languages){
            var options = $.map(languages.results, function(language){
                return '<option value="{id}">{label}</option>'.format(language);
            });

            keywordsAndIndicators.html(options.join(""));
            keywordsAndIndicators.multiselect("rebuild");
            keywordsAndIndicators.multiselect("setAllSelectedText", options[0].label);

            $("#keywords").multiselect("setOptions", {nonSelectedText: "Keyword language"});
            $("#indicators").multiselect("setOptions", {nonSelectedText: "Indicator language"});

            $.map(keywordsAndIndicators, function(select){
                var initial = $(select).data("initial");

                if (initial){
                    $(select).multiselect("select", initial[0]);
                }

                $(select).data("initial", null);
            });
        })
    };

    self.run_query = function run_query(event) {
        event.preventDefault();
        $(window).off("scroll");
        $(".error").removeClass("error").tooltip("destroy");
        $("#global-error").hide();
        PNotify.removeAll();

        loading_dialog.modal({keyboard: false, backdrop: 'static'});
        progress_bar.css("width", 0);
        message_element.text(message_element.attr("placeholder"));

        form_data = serializeForm($("#query-form"), SETS);
        $("#result .panel-body").html("<i>No results yet</i>");

        var script = scripts_container.find(".active")[0].id.replace("script_","");

        $.ajax({
            type: "POST", dataType: "json",
            url: API.get_api_url(script),
            data: form_data,
            headers: {
                "X-Available-Renderers": self.get_accepted_mimetypes().join(",")
            },
            traditional: true
        }).done(function(data){
            // Form accepted, we've been given a task uuid
            self.init_poll(data.uuid);
        }).fail(self.fail);
    };

    self.script_changed = function script_changed(event){
        var name = $(event.target).attr("name");
        $(".query-submit .btn").addClass("disabled");
        $("#scripts").find(".active").removeClass("active");
        $(event.target).addClass("active");

        event.preventDefault();

        window.history.replaceState(null, null, '#' + name);

        var url = API.get_api_url(name);

        $.ajax({
            "type": "OPTIONS", url: url, dateType: "json"
        }).done(script_form_loaded).error(function(){
            show_error("Could not load form due to unkown server error. Try again after " +
            "refreshing this page (F5).");
        });

        script_form.text("Loading script form..");
    };

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
            label.attr("for", id);

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

            $(".depends", widget).depends();
        });

        $("select[multiple=multiple]", $("#script-form")).multiselect(MULTISELECT_DEFAULTS);

        $.map($("select", $("#script-form")), function(el){
            if ($(el).attr("multiple") === "multiple") return;
            $(el).multiselect({ disableIfEmpty: true });
        });

        if (saved_query.loading){
            fill_form();
            saved_query.loading = false;
        }


        var post_func = post_script_loaded[window.location.hash.slice(1)];
        if(post_func) post_func();

        $("#loading-dialog").modal("hide");
        $(".query-submit .btn").removeClass("disabled");
    }

    self.datetype_changed = function datetype_changed(){
        date_inputs.prop("disabled", true).addClass("hidden");
        $.each(dates_enabling[datetype_input.val()], function(i, selector){
            $("#dates").find("input[name=" + selector + "]").prop("disabled", false).removeClass("hidden");
        });

        if (datetype_input.val() == "all"){
            $("#dates").find(".formatting-help").hide();
        } else {
            $("#dates").find(".formatting-help").show();
        }
    };

    var post_script_loaded = {
        "aggregation": function(){
            $("#script-form [name=relative_to]").depends({
                fetchData: function(options, elements, url){
                    var form_data = serializeForm($("#query-form"), SETS);
                    var y_axis = form_data["y_axis"];
                    form_data.output_type = "application/json";

                    if (y_axis === "total"){
                        $("#script-form [name=relative_to]").multiselect("disable").multiselect("setOptions", {
                            nonSelectedText: "None selected"
                        }).multiselect("rebuild");
                        return;
                    } else {
                        $("#script-form [name=relative_to]").multiselect("enable");
                    }

                    $.ajax({
                        type: "POST", dataType: "json",
                        url: API.get_api_url("statistics"),
                        data: form_data,
                        traditional: true
                    }).done(function(data){
                        // Form accepted, we've been given a task uuid
                        Poll(data.uuid).result(function(data){
                            data = data[({
                                medium: "mediums",
                                term: "queries",
                                "set": "articlesets"
                            })[y_axis]];

                            var ldata = [{id: "", label: "--------"}];
                            $.each(data, function(id, label){
                                if (y_axis === "term"){
                                    ldata.push({id: id, label: id});
                                } else {
                                    ldata.push({id: id, label: label});
                                }
                            });

                            ldata = (ldata.length === 1) ? [] : ldata;
                            options.onSuccess(options, elements, {results: ldata});
                        });
                    }).fail(self.fail);
                }
            });

            $("#script-form [name=relative_to]").parent().append(
                $("<button data-toggle='tooltip' title='Refresh options manually' class='btn btn-default'>").append(
                    $("<i class='glyphicon glyphicon-refresh'>")
                ).tooltip().click(function(event){
                    event.preventDefault();
                    $("[name=y_axis]").change();
                })
            );

        }
    };

    self.fail = function fail(jqXHR, textStatus, errorThrown){
        if(jqXHR.status === 400){
            // Form not accepted or other type of error
            form_invalid(JSON.parse(jqXHR.responseText));
        } else {
            // Unknown error
            show_jqXHR_error(jqXHR, errorThrown);
        }

        $("#loading-dialog").modal("hide");
        progress_bar.css("width", "0%");
    };

    self.init_poll = function init_poll(uuid){
        var poll = Poll(uuid, {download: self.download_result()});

        poll.done(function(){
            progress_bar.css("width", "100%");
            message_element.text("Fetching results..")
        }).fail(function(data, textStatus, _){
            show_error("Server replied with " + data.status + " error: " + data.responseText);
            $("#loading-dialog").modal("hide");
            progress_bar.css("width", "0%");
        }).result(function(data, textStatus, jqXHR){
            var contentType = jqXHR.getResponseHeader("Content-Type");
            var body = $("#result").find(".panel-body").html("");
            var renderer = renderers[contentType];

            if(renderer === undefined){
                show_error("Server replied with unknown datatype: " + contentType);
            } else {
                renderer(form_data, body, self.prepare_data(data));
            }

            $("#result").attr("class", window.location.hash.slice(1));
        }).always(function() {
            loading_dialog.modal("hide");
            progress_bar.css("width", 0);
        }).progress_bar(message_element, progress_bar);
    };

    /**
     * Should we offer the user to download the result? I.e., can we expect the server to
     * inlcude the 'attachment' header?
     *
     * @returns boolean
     */
    self.download_result = function download_result(){
        var download = $("#query-form [name=download]").is(":checked");

        if (download){
            // User explicitly indicated wanting to download
            return true;
        }

        // If we cannot render the selected output type, we should offer download option
        var outputType = $("#query-form [name=output_type]").val();
        return $.inArray(outputType.split(";")[0], self.get_accepted_mimetypes()) === -1;
    }


    self.show_jqXHR_error = function show_jqXHR_error(jqXHR, error, hide){
        show_error(
            "Unknown error. Server replied with status code " +
            jqXHR.status + ": " + error
        );

    };

    self.show_error = function show_error(msg, hide){
        new PNotify({type: "error", hide: (hide === undefined) ? false : hide, text: msg});
    };



    ////////////////////////////////////////////////
    //           INITIALISE FUNCTIONS             //
    ////////////////////////////////////////////////
    self.init_dates = function init_dates(){
        datetype_input
            // Enable / disable widgets
            .change(self.datetype_changed)
            // Compatability fix for Firefox:
            .keyup(self.datetype_changed)
            // Check initial value
            .trigger("change");
    };

    self.init_scripts = function init_scripts(){
        // Load default or chosen scripts
        $(window).bind('hashchange', self.hashchange);
        $("#load-query").removeClass("disabled");

        if (saved_query.id !== null){
            init_saved_query(saved_query.id);
        } else {
            $(window).trigger("hashchange");
        }
    };

    self.init_shortcuts = function initialise_shortcuts(){
        $.each(HOTKEYS, function(keys, callback){
            $(document).delegate('*', 'keydown.' + keys, function(event){
                event.preventDefault();
                event.stopPropagation();
                callback(event);
            });
        })
    };

    self.init = function init(){
        $("#codebooks").change(self.codebook_changed);
        $("#run-query").click(self.run_query);
        $("#content").find("> form").submit(self.run_query);
        $("#scripts").find(".script").click(self.script_changed);

        //$("#delete-query").click(delete_query);
        //$("#save-query-dialog").find(".save").click(save_query.bind({confirm: false}));
        //$("h4.name").click(save_query.bind({confirm: true, method: "patch"}));
        //$("#save-query").click(save_query_clicked);
        //$("#change-articlesets").click(change_articlesets_clicked);
        //$("#change-articlesets-confirm").click(change_articlesets_confirmed_clicked);

        /*$("#load-query").find("> button").click(function() {
            window.setTimeout(function () {
                $("#load-query").find("input.multiselect-search").focus();
            });
        });*/

        /*$("#new-query").click(function(event){
            event.preventDefault();

            var url = get_window_url(SETS, window.location.hash.slice(1));

            if (window.location.search + window.location.hash === url){
                window.location.reload();
            } else {
                window.location = url;
            }

            $("#loading-dialog").modal({keyboard: false, backdrop: "static"});
            $("#loading-dialog").find(".message").text("Refreshing..");
        });*/

        self.init_dates();
        self.init_scripts();
        self.init_shortcuts();
    };

    return self;
});
