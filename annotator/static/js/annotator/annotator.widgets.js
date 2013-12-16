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

/*
 * Widgets represent codingschemafields in the DOM. For each type, a property
 * on `widgets` is registered which can be used to generate html elements,
 * get and set values. Furthermore, general functions are available which
 * don't require the caller to know anything about the schematypes.
 */


function get_input(widget){
    if (widget.hasClass("coding")) return widget;
    return widget.find(".coding");
}

widgets = (function(self){
    self.EMPTY_INTVAL = "null";
    self.SCHEMATYPES = {
        1: "text",
        2: "number",
        5: "codebook",
        7: "boolean",
        9: "quality"
    };

    /* WIDGET TYPES */
    /* A widget must implement three methods: get_html, get_value and set_value. The
     * documentation for the methods is given below, as well as a default implementation. */
    self.default = {
        /*
         * Returns exactly one element which is henceforth known as a 'widget'. It is later
         * passed to get_value and set_value.
         */
        get_html : function(schemafield, _intval){
            var widget = $("<input>").addClass("coding");
            return (_intval) ? widget.attr("intval", self.EMPTY_INTVAL) : widget;
        },

        /*
         * Depending on the type, will return an intval or strval.
         *
         * @param container: jQuery/DOM element
         * @return: null / int / string
         */
        get_value : function(widget){
            var value = get_input(widget).attr("intval");

            if (value === undefined){
                return get_input(widget).val();
            } else if (value == self.EMPTY_INTVAL) {
                return null;
            }

            return parseInt(value);
        },

        /* Takes a CodingValue object and initialises the widget to this value */
        set_value : function(widget, codingvalue, _intval){
            widget = get_input(widget);

            if(_intval){
                widget.attr("intval", (codingvalue.intval === null) ? self.EMPTY_INTVAL : codingvalue.intval);
                widget.val(codingvalue.intval);
            } else {
                widget.val(codingvalue.strval);
            }
        }
    };

    /* TEXT TYPE */
    self.text = $.extend({}, self.default);

    /* BOOLEAN TYPE */
    self.boolean = $.extend({}, self.default, {
        get_html : function(){
            return self.default.get_html(null, true).attr("type", "checkbox").change(function(){
                $(this).attr("intval", $(this).prop("checked") ? 1 : 0);
            });
        },
        set_value : function(widget, codingvalue){
            self.default.set_value(widget, codingvalue, true);
            widget.prop("checked", !!codingvalue.intval);
        }
    });

    /* NUMBER TYPE */
    self.number = $.extend({}, self.default, {
        get_html : function(){
            return self.default.get_html(null, true).attr("type", "number").change(function(){
                var value = parseInt($(this).val());
                $(this).attr("intval", isNaN(value) ? self.EMPTY_INTVAL : value);
            });
        }
    });

    /* QUALITY TYPE */
    self.quality = $.extend({}, self.default, {
        get_html : function(){
            var widget = self.default.get_html(null, true);

            widget.attr("type", "number");
            widget.attr("step", 0.5).attr("min", -1).attr("max", 1);
            widget.change(function(){
                var target = $(this);
                var value = parseFloat(target.val());
                target.attr("intval", Math.round(value * 10));
            });

            return widget;
        }

    });

    /* CODEBOOK TYPE */
    self.codebook = $.extend({}, self.default, {
        get_html : function(schemafield){
            var html = $("<span>");

            if(schemafield.split_codebook){
                var root = $("<input>");
                var descendant = $("<input>");
                var hidden = $("<input>").attr("intval", self.EMPTY_INTVAL).hide();

                root.addClass("codebook_root").attr("placeholder", "Root..").attr("intval", self.EMPTY_INTVAL);
                descendant.addClass("codebook_descendant").attr("placeholder", "Descendant..");
                descendant.attr("intval", self.EMPTY_INTVAL);
                hidden.addClass("codebook_value").addClass("coding");

                console.log(schemafield);
                autocomplete.set(root, schemafield.choices);
                autocomplete.set(descendant, schemafield.choices);

                descendant.on("autocompletechange", function(event, ui){
                    hidden.attr("intval", (ui.item === null) ? self.EMPTY_INTVAL : ui.item.get_code().code);
                    hidden.trigger("change");
                });

                html.append(root).append(descendant).append(hidden);
            } else {
                var input = $("<input>").attr("intval", self.EMPTY_INTVAL).addClass("coding");
                autocomplete.set(input, schemafield.choices);
                html.append(input);

            }

            return html;
        },
        set_value : function(widget, codingvalue){
            self.default.set_value(widget, codingvalue, true);
            if (codingvalue.intval === null) return;

            var schemafield = annotator.models.schemas[widget.attr("codingschema_id")];
            var code = schemafield.codebook.codes[codingvalue.intval];

            // Find parent-choice
            var parent_choice = $.grep(schemafield.choices, function(choice){
                return choice.get_code() == code.parent;
            })[0];

            // Find child choice
            var code_choice = $.grep(parent_choice.descendant_choices, function(choice){
                return choice.get_code() == code;
            })[0];

            // And we've got the labels!
            $(".codebook_root", widget).val(parent_choice.label);
            $(".codebook_descendant", widget).val(code_choice.label);
        }

    });

    self.get_widget_type = function(schemafield){
        return self[self.SCHEMATYPES[schemafield.fieldtype]];
    };

    /* GENERAL FUNCTIONS */
    /* Generates an array of dom elements based on a list of schemafields. */
    self.get_html = function(schemafields, sentence){
        return $.map(schemafields, function(schemafield){
            var widget, widget_type;

            widget_type = self.get_widget_type(schemafield);
            widget = widget_type.get_html(schemafield);
            widget.attr("schemafield_id", schemafield.id);
            widget.attr("sentence_id", (sentence === null) ? undefined : sentence.id);
            widget.addClass("coding-container");

            return widget;
        });
    };

    /* Generates 'label' element based on a schemafield and a widget */
    self.get_label_html = function(schemafield, widget){
        var input = widget.find("input.coding");
        return $("<label>").attr("for", input.attr("id")).text(schemafield.label);
    };

    /* Returns existing widget(s) */
    self.find = function(schemafield, sentence){
        var scope = $((sentence === null) ? "#article-coding" : "unitcoding-table-part");
        var selector = "[schemafield_id={0}]";

        if (sentence === null){
            selector += ":not([sentence_id])";
        } else {
            selector += "[sentence_id={1}]";
        }

        return scope.find(selector.f(schemafield.id, (sentence !== null) ? sentence.id : 0));
    };

    /*
     * Same as get_value, but returns as CodingValue object.
     */
    self.get_codingvalue = function(container) {
        var sentence = annotator.state.sentences[container.attr("sentence_id")] || null;
        var coding = annotator.state.codings[(sentence === null) ? "null" : sentence.id];
        var field = annotator.models.schemafields[container.attr("schemafield_id")];
        var value = self.get_value(container);

        return {
            sentence: sentence, coding: coding, field : field,
            strval: (value !== null && typeof(value) !== "number") ? value : null,
            intval: (value === null || typeof(value) === "number") ? value : null
        }

    };

    /*
     * Get value of coding. This function looks for an input element with
     * class 'coding', which can either have an attribute 'intval' which
     * will be returned (or null, if EMPTY_INTVAL is set). Else, it will
     * return a string which is equal to the inner value of the input element.
     *
     * @param container: jQuery/DOM element
     * @return: null / int / string
     */
    self.get_value = function(container){
        var field = annotator.models.schemafields[container.attr("schemafield_id")];
        return self.get_widget_type(field).get_value(container);
    };

    return self;
})({});