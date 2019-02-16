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
    "query/renderers", "query/utils/poll", "query/api", "pnotify", "moment",
    "pnotify.nonblock", "amcat/amcat.datatables",
    "query/utils/format", "jquery.hotkeys", "jquery.depends", "bootstrap",
    "bootstrap-multiselect", "bootstrap-tooltip", "bootstrap-datepicker", "jquery.scrollTo"
    ], function($, MULTISELECT_DEFAULTS, serializeForm, renderers, Poll, api, PNotify, moment){
    // TODO: Make it prettier:
    $.fn.datepicker.defaults.format = "yyyy-mm-dd";

    var self = {};

    var form = $(this);
    var result = $("#result");
    var query_screen = $("#query-screen");

    var query_form = $("#query-form");
    var USER = query_form.data("user");
    var PROJECT = query_screen.data("project");
    var SETS = query_form.data("sets");
    var JOBS = query_form.data("jobs");
    API = api({"host": ""});


    var DEFAULT_SCRIPT = "summary";
    var FIELD_AGGREGATE_API_URL  = "/api/v4/aggregate?page_size=100000&q=*&axis1={field}";
    var TASK_API_URL = "/api/v4/tasks/?uuid={uuid}";
    var SAVED_QUERY_API_URL = "/api/v4/projects/{project_id}/querys/{query_id}/";
    var CODEBOOK_LANGUAGE_API_URL = "/api/v4/projects/{project_id}/codebooks/{codebook_id}/languages/";
    var SELECTION_FORM_FIELDS = [
        "include_all", "articlesets", "filters", "article_ids",
        "start_date", "end_date", "datetype", "on_date", "relative_date",
        "codebook_replacement_language", "codebook_label_language",
        "codebook", "query", "download", "codingjobs",
        "codingschemafield_1", "codingschemafield_value_1", "codingschemafield_include_descendants_1",
        "codingschemafield_2", "codingschemafield_value_2", "codingschemafield_include_descendants_2",
        "codingschemafield_3", "codingschemafield_value_3", "codingschemafield_include_descendants_3"
    ];

    var HOTKEYS = {
        "ctrl_q": function(){ $("#run-query").click(); },
        "ctrl_return": function(){ $("#run-query").click(); },
        //"ctrl_r": function(){ $("#new-query").click(); },
        "ctrl_shift_s": function(){
            $("#save-query-dialog").find(".save:visible").click();
            $("#save-query-as").click();
        },
        "ctrl_s": function(){
            var save_query = $("#save-query");

            if (!save_query.hasClass("disabled")){
                save_query.click();
            } else {
                $("#save-query-as").click();
            }
        },
        "ctrl_o": function(){
            $("#load-query").find("> button").click();

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
    var date_inputs = $("#dates").find("input, select:not(#id_datetype)");
    var relative_date_input = $("#id_relative_date_fake");
    var scripts_container = $("#scripts");
    var script_form = $("#script-form");
    var loading_dialog = $("#loading-dialog");
    var message_element = loading_dialog.find(".message");
    var progress_bar = loading_dialog.find(".progress-bar");
    var form_data = null;

    const filterInputs  = $("#filter-inputs");
    const filterCache = {};

    var saved_query = {
        id: query_form.data("query"),
        name: null,
        user: null
    };


    self.form_invalid = function(data){
        // Add error class to all
        let field_labels = [];
        let extra_errors = [];
        $.each(data, function(field_name, errors){
            if(field_name === "__all__"){
                for(let error of errors) {
                    extra_errors.push(error);
                }
                return;
            }
            let field = $("[name=" + field_name + "]", $("#query-form"));
            field.addClass("error")
                .prop("title", errors[0])
                .data("toggle", "tooltip")
                .tooltip();

            if (field_name === '__all__'){
                var ul = $("#global-error").show().find("ul").html("");
                $.each(errors, function(i, error){
                    ul.append($("<li>").text(error));
                });
            }
            let label = field_name;
            if(field[0].labels && field[0].labels.length > 0){
                label = field[0].labels[0].innerText;
            }
            field_labels.push(label);
        });

        loading_dialog.modal("hide");
        progress_bar.css("width", "0%");
        let field_lis = field_labels.concat(extra_errors).map(x => `<li>${x}</li>`);
        self.show_error("Invalid form. Please change the red input fields" +
            ` to contain valid values. <br>Invalid fields: <ul>${field_lis.join("")}</ul>`, true);
    };


    self.get_accepted_mimetypes = function(){
        return $.map(renderers, function(_, mimetype){ return mimetype; });
    };

    self.hashchange = function(){
        var hash;

        if(!location.hash || !location.hash.slice(1)){
            hash = DEFAULT_SCRIPT;
        } else {
            hash = location.hash.slice(1);
        }

        console.log(hash);

        $("#script_" + hash).click();
    };

    self.codebook_changed = function(event){
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

    self.run_query = function(event) {
        event.preventDefault();
        $(window).off("scroll");
        $(".error").removeClass("error").tooltip("destroy");
        $("#global-error").hide();
        PNotify.removeAll();

        loading_dialog.modal({keyboard: false, backdrop: 'static'});
        progress_bar.css("width", 0);
        message_element.text(message_element.attr("placeholder"));

        var $result = $("#result");
        var table = $result.find(".dataTables_scrollBody table");

        if (table.length > 0){
            table.DataTable().destroy();
        }

        form_data = serializeForm($("#query-form"), JOBS, SETS);
        $result.find(".panel-body").html("<i>No results yet</i>");

        var script = scripts_container.find(".active")[0].id.replace("script_","");

        $.ajax({
            type: "POST", dataType: "json",
            url: API.getActionUrl(script, PROJECT),
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

    self.script_changed = function(event){
        var name = $(event.target).attr("name");
        $(".query-submit .btn").addClass("disabled");
        $("#scripts").find(".active").removeClass("active");
        $(event.target).addClass("active");

        event.preventDefault();

        window.history.replaceState(null, null, '#' + name);

        var url = API.getActionUrl(name, PROJECT);
        const [path, data] = url.split("?");

        $.ajax({
            type: "POST",
            url: path + `?project=${PROJECT}`,
            dataType: "json",
            headers: {"X-HTTP-METHOD-OVERRIDE": "OPTIONS"},
            data: `sets=${SETS}&jobs=${JOBS}`,
            contentType: "application/x-www-form-urlencoded"
        }).done(self.script_form_loaded).error(function(){
            self.show_error("Could not load form due to unkown server error. Try again after " +
            "refreshing this page (F5).");
        });

        script_form.text("Loading script form..");
    };

    self.script_form_loaded = function(data){
        $("#script-line").show();
        if (data.help_text) {
            $("#script-help").text(data.help_text)
                .show();
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

        $("select[multiple=multiple]", script_form).multiselect(MULTISELECT_DEFAULTS);

        $.map($("select", script_form), function(el){
            if ($(el).attr("multiple") === "multiple") return;
            $(el).multiselect({ disableIfEmpty: true });
        });

        if (saved_query.loading){
            self.fill_form();
            saved_query.loading = false;
        }


        var post_func = post_script_loaded[window.location.hash.slice(1)];
        if(post_func) post_func();

        loading_dialog.modal("hide");
        $(".query-submit .btn").removeClass("disabled");

        if (document.location.search.indexOf("autorun") !== -1){
            window.setTimeout(function(){
                $("#run-query").click();
            }, 500)
        }
    };

    self.init_saved_query = function(query_id){
        var url = SAVED_QUERY_API_URL.format({project_id: PROJECT, query_id: query_id});
        loading_dialog.modal({keyboard: false, backdrop: "static"});
        loading_dialog.find(".message").text("Loading saved query..");
        progress_bar.css("width", "10%");

        $.ajax({
            type: "GET",
            dataType: "json",
            url: url + "?format=json"
        }).done(function(data){
            data.parameters = JSON.parse(data.parameters);
            saved_query = data;
            saved_query.loading = true;

            loading_dialog.find(".message").html("Retrieved <i class='name'></i>. Loading script..");
            loading_dialog.find(".message .name").text(data.name);
            progress_bar.css("width", "50%");
            self.fill_form();

            window.location.hash = "#" + data.parameters.script;
            $(window).trigger("hashchange");

            loading_dialog.modal("hide");
            progress_bar.css("width", "0%");
            self.init_delete_query_button();
            $("#query-name").text(data.name);
        }).fail(self.fail);
    };

    self.init_previous_query = function(task_uuid){
        var url = TASK_API_URL.format({uuid: task_uuid});
        loading_dialog.modal({keyboard: false, backdrop: "static"});
        loading_dialog.find(".message").text("Loading saved query..");
        progress_bar.css("width", "10%");

        $.ajax({
            type: "GET",
            dataType: "json",
            url: url
        }).done(function(data){
            console.log(data);
            saved_query.parameters = data.results[0].arguments.data;
            saved_query.loading = true;

            loading_dialog.find(".message").html("Retrieved <i class='name'></i>. Loading script..");
            loading_dialog.find(".message .name").text(data.name);
            progress_bar.css("width", "50%");

            var script = data.results[0].class_name.split(".");
            script = script[script.length - 1].replace("Action", "").toLowerCase();

            window.location.hash = "#" + script;
            $(window).trigger("hashchange");

            loading_dialog.modal("hide");
            progress_bar.css("width", "0%");
            self.init_delete_query_button();
            $("#query-name").text(data.name);

            // TODO: figure out race condition that occurs here.
            setTimeout(function() {
                self.fill_form();
                form_data = serializeForm($("#query-form"), JOBS, SETS);
                self.init_poll(task_uuid);
            }, 200);
        }).fail(self.fail);
    };

    /*
     * Called when 'run query' is clicked.
     */
    self.save_query = function(event){
        event.preventDefault();
        var dialog = $("#save-query-dialog");
        var confirm_dialog = $('#confirm-overwrite-dialog');
        var name_btn = $("[name=name]", dialog);
        var save_btn = $(".save", dialog);

        save_btn.removeClass("disabled");
        name_btn.removeClass('error');

        var dialog_visible = dialog.is(":visible") || confirm_dialog.is(":visible");

        if (this.method !== undefined){
            saved_query.method = this.method;
        }

        var method = saved_query.method.toUpperCase();
        var dialogtype = typeof(this.dialogtype) === "undefined" ? "FULL" : this.dialogtype.toUpperCase();
        if (!dialog_visible){
            name_btn.val(saved_query.name);
        }
        var form = name_btn.closest('form');

        

        if (!dialog_visible && this.confirm === true) {
            if(dialogtype === "CONFIRM-ONLY"){
                confirm_dialog.modal();
                return $('.save', confirm_dialog)[0].focus();
            }
            else{
                dialog.modal();
                return $(dialog.find("input").get(0)).focus();
            }    
        }


        // Save query in modal clicked
        var name = name_btn.val();

        // Must have non-empty name
        if (name === ""){
            return name_btn.addClass("error");
        }

        var url;
        if (method === "PATCH"){
            url = SAVED_QUERY_API_URL.format({project_id: PROJECT, query_id: saved_query.id});
        } else {
            url = SAVED_QUERY_API_URL.format({project_id: PROJECT, query_id: ''}).replace("//", "/");
        }

        var data = serializeForm($("#query-form"), JOBS, SETS);
        data["script"] = window.location.hash.slice(1);
        delete data['csrfmiddlewaretoken'];

        $.ajax({
            type: method,
            dataType: "json",
            url: url + "?format=json",
            data: {
                name: name,
                parameters: JSON.stringify(data)
            },
            headers: {
                "X-CSRFTOKEN": $.cookie("csrftoken")
            }
        }).done(function(data){
            dialog.modal("hide");
            confirm_dialog.modal("hide");
            progress_bar.css("width", "0%");
            $("#query-name").text(data.name);

            saved_query = data;
            saved_query["parameters"] = JSON.parse(saved_query["parameters"]);

            new PNotify({
                type: "success",
                text: "Query saved as <i>{name}</i>.".format(data),
                delay: 1500
            });

            $("#delete-query").removeClass("disabled");
        }).fail(self.fail);

        save_btn.addClass("disabled");
    };

    self.init_delete_query_button = function(){
        var deleteSaveBtns = $("#delete-query, #save-query");
        deleteSaveBtns.addClass("disabled");
        if (saved_query.user === USER){
            deleteSaveBtns.removeClass("disabled");
        }
    };

    self.delete_query = function(event){
        event.preventDefault();

        loading_dialog.modal({keyboard: false, backdrop: "static"});
        loading_dialog.find(".message").text("Deleting saved query..");
        loading_dialog.find(".message .name").text(saved_query.name);
        progress_bar.css("width", "20%");

        var url = SAVED_QUERY_API_URL.format({
            project_id: PROJECT,
            query_id: saved_query.id
        });

        url += "/";

        $.ajax({
            type: "DELETE",
            url: url,
            dataType: "json",
            headers: {
                "X-CSRFTOKEN": $.cookie("csrftoken")
            }
        }).done(function(){
            $("#load-query-menu li[query={id}]".format(saved_query)).remove();

            saved_query = {
                parameters: null,
                name: null,
                id: null,
                user: null
            };

            loading_dialog.modal("hide");
            progress_bar.css("width", "0%");
            self.init_delete_query_button();
            $("#query-name").html("<i>Unsaved query</i>");

            new PNotify({
                type: "success",
                text: "Query deleted.",
                delay: 1500
            });

            history.replaceState({}, document.title, "?sets={sets}#{hash}".format({
                sets: SETS.join(","),
                hash: window.location.hash.slice(1)
            }));
        }).fail(self.fail);

        $("#delete-query").addClass("disabled");
    };
    self.save_query_as_clicked = function(event){
        var args = {};
        args.confirm = true;
        args.dialogtype = "full";
        args.method = "post";
        self.save_query.bind(args)(event);
    };
    self.save_query_clicked = function(event){
        var args = {};
        if (saved_query.id === null) {
            args.confirm = true;
            args.dialogtype = "full";
            args.method = "post";
        } else {
            args.confirm = true;
            args.dialogtype = "confirm-only";
            args.method = "patch";
        }
        self.save_query.bind(args)(event);
    };
    self.change_name_clicked = function(event){
        console.log(USER);
        if(saved_query.user === USER){
            return self.save_query.bind({
                confirm: true,
                method: saved_query.id ? "patch" : "post",
                dialogtype: "full"
            })(event);
        }
    };
    self.change_articlesets_clicked = function(event){
        event.preventDefault();

        $("#change-articlesets-select").change(function(){
            var noneSelected = $(this).find('option:selected').length === 0;
            $("#change-articlesets-confirm").toggleClass('disabled', noneSelected);
        });

        $("#change-articlesets-query-dialog").modal();

    };

    self.change_articlesets_confirmed_clicked = function(){
        var options = $('#change-articlesets-select').find('option:selected');

        SETS = $.map(options, function(option){
            return parseInt($(option).val());
        });

        var url = self.get_window_url(JOBS, SETS, window.location.hash.slice(1));
        history.replaceState({}, document.title, url);
        $("#id_articlesets")
            .trigger('before_update')
            .multiselect('deselectAll', false)
            .multiselect('select', SETS)
            .multiselect('rebuild')
            .multiselect('disable');

        $("#change-articlesets-query-dialog").modal("hide");
        $("#script_{script}".format({
            script: window.location.hash.slice(1)
        })).click();
    };

    self.get_window_url = function(jobs, sets, hash){
        return "?sets={sets}&jobs={jobs}#{hash}".format({
            sets: sets.join(","),
            jobs: jobs.join(","),
            hash: hash
        });
    };

    self.fill_filters = async function(){
        let filters;
        if(saved_query.parameters.filters === undefined || saved_query.parameters.filters.length === 0){
            filters = {}
        }
        else {
            filters = JSON.parse(saved_query.parameters.filters);
        }
        filterInputs.html("");
        for(let k in filters){
            let row = $(self.add_filter_row());
            row.find(".filters-field").val(k);
            await self.update_filter_row(row);
            row.find(".filters-value").val(filters[k]).multiselect("rebuild");
            row.trigger("input");
        }
    };

    self.fill_form = function(){
        $.each(saved_query.parameters, function(name, value){
            var inputs = "input[name={name}]";
            inputs += ",textarea[name={name}]";
            inputs += ",select[name={name}]";
            inputs = $(inputs.format({name: name.replace('.', '\\.')}));

            if (inputs.length === 0 || name === "articlesets" || name === "csrfmiddlewaretoken"){
                return;
            }

            var tagName = inputs.get(0).tagName;

            if (tagName === "SELECT" && inputs.get(0).id !== 'id_codingjobs'){
                // Bootstrap (multi)select
                inputs.multiselect("deselectAll", false);

                if (!inputs.attr("multiple") || typeof(value) !== "object"){
                    value = [value];
                }

                $.map(value, function(val){
                    inputs.multiselect('select', val);
                });

                inputs.data('initial', value);
                inputs.multiselect("rebuild");
                if(!name.match(/^codingschemafield_\d+$/)){
                    inputs.trigger("change");
                }
            } else if (tagName === "INPUT" && inputs.attr("type") === "checkbox"){
                // Boolean fields
                inputs.prop("checked", value);
                inputs.trigger("change");
            } else {
                inputs.val(value);
                inputs.trigger("change");
            }
        });
        self.fill_filters();
    };


    self.datetype_changed = function(){
        let dates = $("#dates");
        date_inputs.prop("disabled", true);
        dates.find("[data-show-for]").addClass("hidden");
        dates.find(`[data-show-for~=${datetype_input.val()}]`).prop("disabled", false).removeClass("hidden");
    };

    self.relative_date_changed = function(e){
        if(!e.target.reportValidity()) return;

        let val = this.value.trim();
        let now = moment();
        let diff = parseInt(val);
        let value_parts = val.split(/\d/);
        let unit = value_parts[value_parts.length - 1].trim();
        let then = now.clone().subtract(diff, unit);
        let value = now - then;
        if(value <= 0) return;
        $("#id_relative_date").val(-value / 1000);
    };

    var post_script_loaded = {
        "aggregation": function(){
            $("#id_value1").closest(".row").hide();
            $("#id_value2").closest(".row").hide();
        },
        "codingaggregation": function(){
            $("#id_primary_use_codebook").closest(".row").before($("<hr>"));
            $("#id_secondary_use_codebook").closest(".row").before($("<hr>"));
            $("#id_value1").closest(".row").before($("<hr>"));
        }
    };

    self.fail = function(jqXHR, textStatus, errorThrown){
        if(jqXHR.status === 400){
            // Form not accepted or other type of error
            self.form_invalid(JSON.parse(jqXHR.responseText));
        } else {
            // Unknown error
            self.show_jqXHR_error(jqXHR, errorThrown);
        }

        loading_dialog.modal("hide");
        progress_bar.css("width", "0%");
    };

    self.parse_querystring = function(){
        var query_string = window.location.search.slice(1);
        if(query_string.length === 0){
            return null;
        }
        var query_strings = query_string.split("&");
        var kv_pairs = query_strings.map(function(str){return str.split("=")});
        var query = {};
        for(var i = 0; i < kv_pairs.length; i++){
            var query_part = kv_pairs[i];
            query[query_part[0]] = query_part[1];
        }
        return query;
    };

    self.on_use_in_query_clicked = function(){
        var dataTable = $("#articlelist-table").find(".dataTables_scrollBody > .dataTable").DataTable();
        var ids = dataTable.rows('.active').data().map(function(r){
            return r.id;
        });
        var query = self.parse_querystring();
        query.articles = ids.join(",");
        var querystring = "?" + $.param(query);
        var search = window.location.search;
        if(search.length > 0){
            var href = window.location.href.replace(search, querystring);
            window.open(href, "_blank");
        }
    };

    self.add_articles_to_set = function(modal, ids, set_id){
        // hackish: mock an appendtoset query to add selected articles to set
        // todo: cleaner solution using a proper api call
        var params = {
            project: PROJECT,
            sets: SETS.join(","),
            jobs: JOBS.join(","),
            format: "json"
        };
        var url = "/api/v4/query/appendtoset?" + $.param(params);

        var data = $.extend({}, form_data);
        data.article_ids = ids.join("\n");
        data.articlesets = SETS;
        data.jobs = JOBS;
        data.project = PROJECT;
        data.articleset = set_id;
        data.columns = undefined;
        $.ajax({
            "url": url,
            "type": "POST",
            "headers": {
                "X-CSRFTOKEN": csrf_middleware_token,
            },
            "dataType" : "json",
            "data": data
        }).done(function(data){
            var poll = Poll(data.uuid);
            poll.result(function(data){
               new PNotify({type: "success", text: data})
            });
            modal.modal("hide");
        }).fail(function(){
            new PNotify({ type : "error", text: "Failed to add articles to set." });
            modal.modal("hide");
        });
    };

    self.on_add_to_set = function(){
        var dataTable = $("#articlelist-table").find(".dataTables_scrollBody > .dataTable").DataTable();
        var ids = dataTable.rows('.active').data().toArray().map(function(r){
            return r.id;
        });
        var modal = $("#add_to_set_modal");
        $.ajax({
            type: "GET",
            url: "/api/v4/projects/" + PROJECT + "/articlesets/?page_size=9999&order_by=name",
            dataType: "json"
        }).success(function(data){
            var select = $("<select>");

            $.each(data.results, function(i, aset){
                var name = aset.name + " (" + aset.id + ") (" + aset.articles + " articles)";
                select.append($("<option>").prop("value", aset.id).text(name).data(aset));
            });


            // Add selector, multiselect and open filtering
            modal.find(".modal-body > p").html(select);
            select.multiselect({
                enableFiltering: true
            });
            modal.find(".modal-body > p .ui-multiselect").click();
            $(".ui-multiselect-filter input[type=search]").focus();

            // Enable 'ok' button
            modal.find(".btn-primary").removeClass("disabled").click(function(){
                $(this).addClass("disabled");
                var checked = $("> option:selected", select);
                var set_id = checked.map(function(){ return this.value; })[0];
                self.add_articles_to_set(modal, ids, set_id);
            });
            modal.modal("show");
        });
        modal.find(".btn-primary").addClass("disabled").off("click");
    };

    self.download_uri_as = function (uri, name){
        var a = $('<a>')
            .attr('href', uri)
            .attr('download', name)
            .appendTo(document.body);
        console.log(a);
        a[0].dispatchEvent(new MouseEvent("click"));
    };

    self.get_data_uri = function(data, content_type){
        data = btoa(data);
        return "data:" + content_type + ";charset=utf-8;base64," + data;
    };

    self.download_data_as = function(data, content_type, name){
        self.download_uri_as(self.get_data_uri(data, content_type), name);
    };

    self.onclick_save_image_link = function(link, image, format){
        var w = image.width;
        var h = image.height;
        var canvas = $('<canvas>').attr('width', w).attr('height', h)[0];
        var render = canvas.getContext('2d');
        render.drawImage(image, 0, 0);
        var uri = canvas.toDataURL(format.mime);
        link.attr('href', uri)
            .attr('download', $("#query-name").text() + '-graph' + format.extension);
    };

    self.get_image_save_buttons= function(image){
        var formats = [
            {mime: 'image/png', extension: '.png'},
            {mime: 'image/jpeg', extension: '.jpg'}
        ];
        var dropdown = $('<div>').addClass('dropdown');
        dropdown.append(
            $('<button>')
                .addClass('btn btn-default btn-xs dropdown-toggle')
                .css('vertical-align', 'top')
                .html('Save <span class="caret"></span>')
                .attr('data-toggle', 'dropdown')
        );
        var list = $('<ul>').addClass('dropdown-menu');
        var svgLink = $('<a>')
            .attr('href', image.attr('src'))
            .attr('download', $("#query-name").text() + '-graph.svg')
            .text('Save as: image/svg');
        list.append($('<li>').html(svgLink));

        formats.forEach(function(format){
            var li = $('<li>').append(
                $("<a>")
                    .click(function(event){
                    self.onclick_save_image_link($(this), image[0], format);
                })
                    .text('Save as: ' + format.mime)
                    .attr('href', '#')
            );
            list.append(li);
        });

        dropdown.append(list);
        dropdown.css({
            'display': 'inline',
            'vertical-align': 'top',
            'margin-left': 20
        });
        return dropdown;
    };

    self.render_complete = function(body){
        var articlelist = $("#articlelist-table");
        if(articlelist.length > 0){
            $("#articlelist-add-to-set").click(self.on_add_to_set);
            $("#articlelist-use-in-query").click(self.on_use_in_query_clicked);
        }


        var images = body.find("img.save-image");
        images.each(function(i, image){
            image = $(image);
            image.after(self.get_image_save_buttons(image));
        });
    };

    self.handle_result = function(jqXHR, data){
        if(self.download_result()){
            self.download_data_as(data, form_data.output_type, "data." + form_data.output_type.split(/[\/+;]/)[1]);
            return;
        }
        var contentType = jqXHR.getResponseHeader("Content-Type");
        var body = result.find(".panel-body").html("");
        var renderer = renderers[contentType];

        if(renderer === undefined){
            self.show_error("Server replied with unknown datatype: " + contentType);
        } else{
            renderer(form_data, body, data);
        }
        self.render_complete(body);
        result.attr("class", window.location.hash.slice(1));
        $(window).scrollTo(result, 500);

        // Reset cache messages
        $(".cache-clear").unbind("click");
        $(".cache-message").hide();
        $(".cache-clearing").hide();
        $(".cache-timestamp").text("");

        // Check for cache in HTTP headers
        if(jqXHR.getResponseHeader("X-Query-Cache-Hit") === "1"){
            var nTimestamp = jqXHR.getResponseHeader("X-Query-Cache-Natural-Timestamp");
            nTimestamp = ("nTimestamp" === "now") ? "just now" : nTimestamp;
            $(".cache-timestamp").text(nTimestamp);
            var cacheKey = jqXHR.getResponseHeader("X-Query-Cache-Key");
            $(".cache-clear").click(self.clear_cache.bind(cacheKey));
            $(".cache-message").show();
        }
    };

    self.init_poll = function(uuid){
        // TODO: remove any remaining download logic from amcat-query-js/utils/poll
        var poll = Poll(uuid /*, {download: self.download_result()}*/);

        poll.done(function(){
            progress_bar.css("width", "100%");
            message_element.text("Fetching results..")
        }).fail(function(data){
            if (data.results){
                data = data.results[0];
            }
            
            if (data.error === undefined) {
                self.show_error("Server replied with " + data.status + " error: " + data.responseText);
            } else {
                self.show_error("<b>"+data.error.exc_type+":</b><br/><pre>"+data.error.exc_message+"</pre>", false, "600px");
            }

            $("#loading-dialog").modal("hide");
            progress_bar.css("width", "0%");
        }).result(function(data, textStatus, jqXHR){
            try {
                self.handle_result(jqXHR, data)
                var root = window.location.href.split("/query/")[0];
                $("#share-result-link").val(`${root}/query/${uuid}`);
            }
            catch(e){
                loading_dialog.modal("hide");
                console.error(e);
                new PNotify({
                    "type": "error",
                    "text": e,
                    "delay": 1000
                });
            }
        }).always(function() {
            loading_dialog.modal("hide");
            progress_bar.css("width", 0);
        }).progress_bar(message_element, progress_bar);
    };

    /**
     * Clear cached query
     */
    self.clear_cache = function(event){
        event.preventDefault();
        $(".cache-message").hide();
        $(".cache-clearing").show();
        
        $.ajax("../clear-query-cache/", {
            type: "POST",
            data: {
                "cache-key": this
            },
            headers: {
                "X-CSRFTOKEN": $.cookie("csrftoken")
            }
        }).success(function(){
            $(".cache-clearing").hide();
            
            new PNotify({
                type: "success",
                text: "Cache cleared!",
                delay: 1000
            });
        }).error(function(){
            $(".cache-message").show();
            $(".cache-clearing").hide();

            new PNotify({
                type: "error",
                text: "Failed to clear cache.",
                delay: 3500
            });
        });
    };

    /**
     * Should we offer the user to download the result? I.e., can we expect the server to
     * inlcude the 'attachment' header?
     *
     * @returns boolean
     */
    self.download_result = function(){
        var download = query_form.find("[name=download]").is(":checked");

        if (download){
            // User explicitly indicated wanting to download
            return true;
        }

        // If we cannot render the selected output type, we should offer download option
        var outputType = query_form.find("[name=output_type]").val();
        return $.inArray(outputType.split(";")[0], self.get_accepted_mimetypes()) === -1;
    };

    self.show_jqXHR_error = function(jqXHR, error){
        self.show_error(
            "Unknown error. Server replied with status code " +
            jqXHR.status + ": " + error + ". Full error: \n" + jqXHR.responseText
        );

    };

    self.show_error = function(msg, hide, width){
	if (width === undefined) width = "300px"; 
        new PNotify({type: "error", hide: (hide === undefined) ? false : hide, text: msg, width: width});
    };


    self.add_filter_row = function(){
        const inputs = document.getElementById("filter-inputs");
        const template = $("#filter-row-template");
        const node = document.importNode(template.get(0).content, true);
        const v = node.querySelector('.filters-value');
        $(v).multiselect({
            enableFiltering: true,
            includeResetOption: false,
            maxHeight: 300,
            onChange(){ this.$select.trigger("input"); }
        });
        const row = node.querySelector('.filter-row');
        inputs.appendChild(node);
        return row;
    };

    self.add_filter_option =  function(row, value){
        row.children('.filters-value').append($("<option>").attr("value", value).text(value));
    };

    self.fetch_filter_values = async function (row, field) {
        if(filterCache.hasOwnProperty(field)){
            return filterCache[field];
        }

        return await new Promise(resolve => {
            let sets = SETS.map(set => "sets=" + set).join("&");
            row.children('.filters-value')[0].disabled = true;
            $.getJSON(FIELD_AGGREGATE_API_URL.format({field: field}) + "&" + sets)
                .success((data) => {
                    let aggr_field = field.replace(/\./, '__');
                    let values = [];
                    for (let r of data.results) {
                        values.push(r[aggr_field]);
                    }
                    filterCache[field] = values;
                    resolve(filterCache[field]);
                });
        });
    };

    function isEmpty(value){
        return value === "" || value === null || value === undefined;
    }

    self.update_filter_row = async function (row) {
        let field = row.children('.filters-field');
        let value = row.children('.filters-value');
        if (isEmpty(field.val())) {
            value[0].disabled = true;
            value.val(null);
            return;
        }

        let fval = field.val();
        fval = fval.indexOf("_") >= 0 ? fval : fval + ".raw";
        value.disabled = true;
        let values = await self.fetch_filter_values(row, fval);

        row.children('.filters-value').html("");
        for (let v of values) {
            self.add_filter_option(row, v);
        }
        value[0].disabled = false;
        value.multiselect("rebuild");

    };

    self.get_row_value = function(row){
        let field = row.children('.filters-field');
        let value = row.children('.filters-value');
        if(isEmpty(field.val()) || isEmpty(value.val())) {
            return null;
        }
        return {field: field.val(), values: value.val()};
    };

    self.on_filter_input = function(e){
        const filters = {};
        let row = $(e.target).closest('.filter-row');

        if(e.target.classList.contains("filters-field")) {
            self.update_filter_row(row);
        }

        for(let row of Array.from(filterInputs.find(".filter-row"))) {
            row = $(row);
            let row_value = self.get_row_value(row);

            if (row_value === null) {
                continue;
            }
            let {field, values} = row_value;

            if (!filters.hasOwnProperty(field))
                filters[field] = [];

            filters[field] = filters[field].concat(values);
        }
        self.update_filters(filters);
    };

    self.update_filters = function(filters){
        self.filters = filters;
        $("#id_filters").val(JSON.stringify(filters));
    };

    self.on_filter_click = function(e){
        if(e.target.getAttribute('data-click') === "remove"){
            $(e.target).closest('.filter-row').remove();
        }
        self.on_filter_input(e);
    };


    ////////////////////////////////////////////////
    //           INITIALISE FUNCTIONS             //
    ////////////////////////////////////////////////
    self.init_dates = function(){
        datetype_input
            // Enable / disable widgets
            .change(self.datetype_changed)
            // Compatability fix for Firefox:
            .keyup(self.datetype_changed)
            // Check initial value
            .trigger("change")
            
            .multiselect("rebuild");

        relative_date_input
            .on('input', (e) => {e.target.reportValidity()})
            .on('change', self.relative_date_changed)
            .trigger("change")
    };

    self.init_filters = function(){
        $('#id_filters').value = JSON.stringify({});
    };

    self.init_scripts = function(){
        // Load default or chosen scripts
        $(window).bind('hashchange', self.hashchange);
        $("#load-query").removeClass("disabled");

        if (saved_query.id !== null){
            self.init_saved_query(saved_query.id);
        } else {
            $(window).trigger("hashchange");
        }
    };

    self.init_shortcuts = function(){
        $.each(HOTKEYS, function(keys, callback){
            $(document).delegate('*', 'keydown.' + keys, function(event){
                event.preventDefault();
                event.stopPropagation();
                callback(event);
            });
        });
    };


    self.init = function(){
        $("#codebooks").change(self.codebook_changed);
        $("#run-query").click(self.run_query);
        $("#content").find("> form").submit(self.run_query);
        $("#scripts").find(".script").click(self.script_changed);

        $("#delete-query").click(self.delete_query);
        $("#confirm-overwrite-dialog, #save-query-dialog").find(".save").click(self.save_query.bind({confirm: false}));
        $("h4.name").click(self.change_name_clicked);
        $("#save-query").click(self.save_query_clicked);
        $("#save-query-as").click(self.save_query_as_clicked);
        $("#change-articlesets").click(self.change_articlesets_clicked);
        $("#change-articlesets-confirm").click(self.change_articlesets_confirmed_clicked);

        $("#btn-add-filter").click(self.add_filter_row);
        $("#filter-inputs")
            .on("input", self.on_filter_input)
            .click(self.on_filter_click);

        $("#load-query").find("> button").click(function() {
            window.setTimeout(function () {
                $("#load-query").find("input.multiselect-search").focus();
            });
        });

        $("#new-query").click(function(event){
            event.preventDefault();

            var url = self.get_window_url(JOBS, SETS, window.location.hash.slice(1));

            if (window.location.search + window.location.hash === url){
                window.location.reload();
            } else {
                window.location = url;
            }

            loading_dialog.modal({keyboard: false, backdrop: "static"});
            loading_dialog.find(".message").text("Refreshing..");
        });

        $("[data-copy]").click(function(e){
            var copyInput = document.getElementById($(this).data("copy"));
            copyInput.focus();
            document.execCommand("selectAll");
            document.execCommand("copy");

            e.preventDefault();
            e.stopPropagation();
        });


        var uuid = window.location.href.match(/\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/);
        if(uuid){
            self.init_previous_query(uuid[1]);
        }
        self.init_dates();
        self.init_filters();
        self.init_scripts();
        self.init_shortcuts();
    };

    return self;
});
