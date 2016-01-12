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

define(["jquery", "bootstrap"], function() {
    "use strict";
    var amcat = {};


    function confirm_dialog(event) {
        event.preventDefault();

        var dialog = $('' +
            '<div class="modal fade" tabindex="-1">' +
            '<div class="modal-dialog"><div class="modal-content"><div class="modal-header">' +
            '<button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>' +
            '<h3 class="noline">Irreversible action</h3>' +
            '</div>' +
            '<div class="modal-body">' +
            '<p>' + $(event.currentTarget).attr("data-confirm") + '</p>' +
            '</div>' +
            '<div class="modal-footer">' +
            '<a href="#" class="btn cancel-button">Cancel</a>' +
            '<a href="' + $(event.currentTarget).attr("href") + '" class="btn btn-danger">Proceed</a>' +
            '</div>' +
            '</div></div></div>').modal("show");

        // Submit form if button has type=submit
        var btn = $(event.currentTarget);
        if (btn.is("[type=submit]")) {
            dialog.find("a.btn-danger").click(function (event) {
                event.preventDefault();
                btn.closest("form").submit();
            });
        }

        $(".cancel-button", dialog).click((function () {
            this.modal("hide");
        }).bind(dialog))
    }

    function bind_confirm_dialogs() {
        /* For <a> with a class 'confirm', display confirmation dialog */
        $(function () {
            $("a.confirm").click(confirm_dialog);
        });
    }

    function bind_layout_switcher() {
        /* Switch layouts */
        $(function () {
            $("#layout-switcher").click(function (event) {
                event.preventDefault();
                // Switch classes, etc.
                $(".container,.container-fluid").toggleClass("container container-fluid");
                $("#layout-switcher").find("i").toggleClass("glyphicon-resize-small glyphicon-resize-full");
                $("body").focus();

                // Resize datatables
                try{
                    $.each($.fn.dataTable.tables(), function(i, table){
                        var settings = $(table).DataTable().settings()[0];
                        settings.oApi._fnAdjustColumnSizing(settings);
                    });
                }
                catch(TypeError){
                    console.warn("Datatables not loaded");
                }
                // Make change permanent. TODO: Make it an API call.
                $.get("/?fluid=" + $("body > .container-fluid").length)
            });
        });
    }

    amcat.main = function(){
        bind_confirm_dialogs();
        bind_layout_switcher();

    };



    return amcat;
});
