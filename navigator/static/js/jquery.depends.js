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
 * Depends allows dropdowns to dynamically fetch their options, depending on related
 * input fields. The dropdown is constructed normally, but takes a properties as options:
 *
 *  - data-depends-url: the url with data for this dropdown
 *  - data-depends-value: string or function determining the value property of each <option>
 *  - data-depends-label: string or function determining the text property of each <option>
 *  - data-depends-on: list of other elements this dropdown depends on. An onchange is
 *  registered on each of these elements, and each trigger an update.
 *
 *  For example, you could initialise a widget the following way in Python:
 *
 *     "data-depends-on": json.dumps(["project"]),
 *     "data-depends-url": "/api/v4/projects/{project}/favourite_articlesets.json",
 *     "data-depends-value": "{id}",
 *     "data-depends-label": "{name} (id: {id})",
 *
 *  The plugin takes various options:
 *
 *  - onChange
 *  - fetchData
 *  - onSuccess
 *  - afterSuccess
 *  - toOptions
 */
(function($){
    $.fn.depends = function(options){
        var defaults = {
            getFormatter: function(options, elements, callback){
                var formatter = {};

                $.map(elements.dependsOnElements, function(el){
                    formatter[el.attr("name")] = el.val();
                });

                return callback(formatter);
            },

            /**
             *
             * @param options
             * @param elements
             * @param event
             */
            onChange: function(options, elements, event){
                options.getFormatter(options, elements, function(formatter){
                    elements.select.html("").multiselect("setOptions", {
                        nonSelectedText: "Loading options.."
                    }).multiselect("rebuild");

                    options.fetchData.bind(options.onSuccess)(
                        options, elements, elements.url.format(formatter)
                    );
                });
            },

            /**
             *
             * @param options
             * @param elements
             * @param url
             * @returns {*}
             */
            fetchData: function(options, elements, url) {
                return $.getJSON(url).success((function(data){
                    this(options, elements, data);
                }).bind(this));
            },

            /**
             *
             * @param options
             * @param elements
             * @param data
             */
            onSuccess: function(options, elements, data){
                var optionsElements = options.toOptions(data, options, elements);
                elements.select.html("").append(optionsElements).multiselect("setOptions", {
                    nonSelectedText: "None selected",
                    disableIfEmpty: true
                }).multiselect("rebuild");

                options.afterSuccess.bind(defaults.afterSuccess)(options, elements);
            },

            /**
             *
             * @param options
             * @param elements
             */
            afterSuccess: function(options, elements){
                // Hack for dynamically loading scripts in combination with saved queries
                var select = elements.select;

                if (select.data("initial")) {
                    const data = select[0].multiple ? select.data("initial") : select.data("initial")[0];
                    select.multiselect("select", data);
                }

                select.data("initial", null);
                select.trigger("depends-load");
            },

            /**
             *
             * @param data
             * @param options
             * @param elements
             * @returns {*}
             */
            toOptions: function(data, options, elements){
                return $.map(data.results, function(option){
                    var el = $("<option>");
                    el.attr("value", elements.value.format(option));
                    el.text(elements.label.format(option));
                    return el;
                });
            }
        };

        options = $.extend({}, defaults, options, {defaults: defaults});

        return this.each(function() {
            var elements = {
                select: $(this),
                form: $(this).closest("form"),
                dependsOn: $(this).data("depends-on"),
                url: $(this).data("depends-url"),
                label: $(this).data("depends-label"),
                value: $(this).data("depends-value")
            };

            var dependsOn = function(event){
                console.log("Dependency changed", elements.select[0].id, event.target.id);
                options.onChange.bind(defaults.onChange)(options, elements, event);
            };

            var dependsOnElements = $.map(elements.dependsOn, function(name){
                return $("[name={name}]".format({name: name}));
            });

            $.map(dependsOnElements, function(el){
                el.change(dependsOn)
            });

            elements.dependsOnElements = dependsOnElements;
            dependsOnElements[0].change();

        });
    };
}(jQuery));