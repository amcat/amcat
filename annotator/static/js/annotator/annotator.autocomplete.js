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

autocomplete = (function(self){
    // TODO: Fetch from server
    self.AUTOCOMPLETE_LANGUAGE = 0;

    /*
     * Sets intval attribute and sets correct label
     */
    self.on_change = function(event, ui){
        var label, intval = widgets.EMPTY_INTVAL;

        if (ui.item !== null){
            intval = ui.item.intval;
            label = ui.item.label;
        }

        $(this).attr("intval", intval).val(label||"");
        $(this).trigger("change");
    };

    self.is_exact_match = function(term){
        return function(el){
            return el.label.toLowerCase() === term.toLowerCase();
        }
    };

    self.startswith_match = function(term){
        var test = new RegExp("^{0}.+$".f(self.escape_regexp(term)), "i");
        return function(el){
            return test.test(el.label);
        }
    };

    self.escape_regexp = function(str) {
        // http://stackoverflow.com/questions/3446170/escape-string-for-use-in-javascript-regex
        return str.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&");
    };

    /*
     * Most of the times a 'choices' property is defined on schemafield
     * and it can be used directly. In case of a codebook split, however,
     * the available choices of the second input field are determined
     * by the first.
     *
     * This function contains the logic for ^ and can be given to
     * jQuery autocomplete as a 'source' parameter (indirectly, as
     * it takes two extra arguments input_element and choices).
     */
    self.get_source = function(input_element, choices, request, callback){
        // Are we a codebook descendant?
        if (input_element.hasClass("codebook_descendant")){
            var parent_id = input_element.parent().find("input.codebook_root").attr("intval");
            if (parent_id === widgets.EMPTY_INTVAL) return callback([]);

            parent_id = parseInt(parent_id);
            choices = $.grep(choices, function(item){
                return item.get_code().code === parent_id;
            })[0].descendant_choices;
        }


        // We would like to present the user with options in the following order (as per issue #55):
        // - Exact match
        // - Startswith match
        // - Rest
        // Furthermore, the returned list should be alphabetically sorted.
        var filtered = $.ui.autocomplete.filter(choices, request.term);
        var do_sort = $(input_element).prop("autocomplete_sort");

        if (do_sort === true || do_sort === undefined){
            filtered.sort(function(a, b){
                a = a.label.toLowerCase();
                b = b.label.toLowerCase();

                if (a < b) return -1;
                if (a > b) return 1;
                return 0;
            });
        }

        var exact = $.grep(filtered, self.is_exact_match(request.term));
        var startswith = $.grep(filtered, self.startswith_match(request.term));
        var rest = $.grep(filtered, function(el){
            // Yes, inArray returns an index.. :|
            return $.inArray(el, exact) === -1 && $.inArray(el, startswith) === -1;
        });

        return callback(([]).concat(exact, startswith, rest).slice(0, 100));
    };

    /*
     * Deprecated behaviour alert: this function tries to fetch a label matching
     * the coders current language. If no label is found, a guess is made and the
     * first available label is returned.
     */
    self.get_label = function(code){
        var language_id = annotator.language_id;
        var label = code.labels[language_id];
        if (label !== undefined) return label;

        // No label found with current coder language. Fetch first available label.
        $.each(code.labels, function(lid, lbl){
            label = lbl;
            return false;
        });

        if (label === undefined){
            // Damnit no labels at all.
            return "";
        }

        return label;
    };

    /*
     * Generate a list of choices for autocomplete, based on a list of codes and the
     * language id for the label.
     */
    self.get_choices = function(codes){
        var get_code = function(){ return this };

        return $.map(codes, function (code) {
            var lbl = self.get_label(code);

            return {
                // We can't store code directly, as it triggers an infinite
                // loop in some jQuery function (autocomplete).
                get_code: get_code.bind(code),
                intval: code.code,
                label: lbl,
                value: lbl,
                descendant_choices: self.get_choices(code.descendants)
            }
        });
    };

    self.set = function(input_element, choices){
        return input_element.autocomplete({
            source : function(request, callback){
                self.get_source(input_element, choices, request, callback);
            },
            autoFocus: true,
            minLength: 0,
            change : self.on_change,
            select : self.on_change,
            delay: 5
        }).focus(function(){
            var value = $(this).val();
            $(this).autocomplete("option", "autoFocus", value !== "");
            $(this).autocomplete("search", value);
        });
    };

    return self;
})({});