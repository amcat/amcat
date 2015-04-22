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
/**
 * http://stackoverflow.com/questions/4974238/javascript-equivalent-of-pythons-format-function
 */
String.prototype.format = function(args){
    var this_string = '';
    for (var char_pos = 0; char_pos < this.length; char_pos++) {
        this_string = this_string + this[char_pos];
    }

    for (var key in args) {
        var string_key = '{' + key + '}'
        this_string = this_string.replace(new RegExp(string_key, 'g'), args[key]);
    }
    return this_string;
};

/**
 *
 */
(function($){
    $.fn.depends = function(){
        return this.each(function() {
            var select = $(this);

            var form = $(this).closest("form");
            var dependsOn = $(this).data("depends-on");
            var urlTemplate = $(this).data("depends-url");

            var labelProp = $(this).data("depends-label");
            var valueProp = $(this).data("depends-value");

            var dependsOnElement = $("[name={name}]".format({name: dependsOn}));

            dependsOnElement.change(function(){
                var formatter = {}
                formatter[dependsOn] = dependsOnElement.val();

                select.html("").multiselect("setOptions", {
                    nonSelectedText: "Loading options.."
                }).multiselect("rebuild");

                var url = urlTemplate.format(formatter);
                $.getJSON(url).success(function(options){
                    var optionsElements = $.map(options.results, function(option){
                        var el = $("<option>");
                        el.attr("value", valueProp.format(option));
                        el.text(labelProp.format(option));
                        return el;
                    });

                    select.html("").append(optionsElements).multiselect("setOptions", {
                        nonSelectedText: "None selected",
                        disableIfEmpty: true
                    }).multiselect("rebuild");

                    // Hack for dynamically loading scripts in combination with saved queries
                    var initial = $(select).data("initial");

                    if (initial) {
                        select.multiselect("select", initial[0]);
                    }

                    select.data("initial", null);
                })
            });

            dependsOnElement.change();
        });
    };
}(jQuery));