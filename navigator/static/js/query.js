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

$((function(){
    var QUERY_API_URL = "/api/v4/query/";
    var SELECTION_FORM_FIELDS = [
        "include_all", "articlesets", "mediums", "article_ids",
        "start_date", "end_date", "datetype", "on_date",
        "codebook_replacement_language", "codebook_label_language",
        "codebook", "query"
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

    var PROJECT = query_screen.data("project");
    var SETS = query_screen.data("sets");

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
        });
    }

    function get_api_url(action){
        action = (action === undefined) ? "" : action;
        var base_url = QUERY_API_URL + action + "?format=json&";
        return base_url + "project=" + PROJECT + "&sets=" + SETS.join(",");
    }

    /*
     * Called when 'run query' is clicked.
     */
    function run_query() {
        loading_dialog.modal({keyboard: false, backdrop: 'static'});
        progress_bar.css("width", 0);
        message_element.text(message_element.attr("placeholder"));

        $.ajax({
            type: "POST", dataType: "json",
            url: get_api_url(scripts_container.find("select").val()),
            data: $("form").serialize()
        }).done(function(data){
            // Form accepted, we've been given a task uuid
            init_poll(data.uuid);
        }).fail(function(){
            // Form not accepted or other type of error

        });
    }

    function init_poll(uuid){
        Poll(uuid).done(function(){
            progress_bar.css("width", "100%");
            message_element.text("Fetching results..")
        }).fail(function(){

        }).result(function(data){
            $(".result .panel-body").html(data);
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

    function show_error(msg){
        new PNotify({type: "error", hide: false, text: msg});
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
                select.append($("<option>").text(name).val(name))
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

