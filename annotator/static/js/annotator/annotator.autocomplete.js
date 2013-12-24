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

        // Only display first 20 results (for performance)
        return callback($.ui.autocomplete.filter(choices, request.term).slice(0, 20));
    };

    /*
     * Generate a list of choices for autocomplete, based on a list of codes and the
     * language id for the label.
     */
    self.get_choices = function(codes, language_id){
        language_id = language_id || self.AUTOCOMPLETE_LANGUAGE;
        var get_code = function(){ return this };

        var labels = $.map(codes, function(code){
            return {
                // We can't store code directly, as it triggers an infinite
                // loop in some jQuery function (autocomplete).
                get_code : get_code.bind(code),
                intval : code.code,
                label : code.labels[language_id],
                value : code.labels[language_id],
                descendant_choices : self.get_choices(code.descendants)
            }
        });

        labels.sort(function(a, b){
            return a.ordernr - b.ordernr;
        });

        return labels;
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