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
    if (widget.hasClass("codingvalue")) return widget;
    return widget.find(".codingvalue");
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
            var widget = $("<input>").addClass("codingvalue");
            return (_intval) ? widget.attr("intval", self.EMPTY_INTVAL) : widget;
        },

        /*
         * Depending on the type, will return an intval or strval.
         *
         * @param widget: jQuery/DOM element
         * @return: null / int / string
         */
        get_value : function(widget){
            var value = get_input(widget).attr("intval");

            if (value === undefined){
                return get_input(widget).val() || null;
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



    /* SENTENCE TYPE */
    self.sentence = $.extend({}, self.default, {
        get_html : function(){
            var choices = $.map(annotator.state.sentences, function(sentence){
                return {
                    value : sentence.get_unit(),
                    label : sentence.get_unit(),
                    sentence : sentence,
                    intval : -1
                }
            });

            var widget = $("<input>").addClass("sentence").change(self.sentence.change);
            autocomplete.set(widget, choices);
            return widget;
        },
        get_value: function(widget){
            var value = widget.val();
            if (value === "") return null;

            var parnr = parseInt(value.split(".")[0]);
            var sentnr = parseInt(value.split(".")[1]);

            return $.grep($.values(annotator.state.sentences), function(sentence){
                return sentence.parnr == parnr && sentence.sentnr == sentnr;
            })[0];

        },
        set_value: function(widget, sentence){
            widget.val((sentence === null) ? "" : sentence.get_unit());
        },
        change : function(){
            var sentence = self.sentence.get_value($(this));
            var coding = annotator.state.codings[$(this).closest(".coding").attr("annotator_coding_id")];
            coding.sentence = sentence;
        }

    });

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
        },
        set_value : function(widget, codingvalue){
            self.default.set_value(widget, codingvalue, true);
        }
    });

    /* FROM AND TO TYPES. These are, together with sentence, special types. From / to encode
     * subsentences and highlight them. */
    self.from = $.extend({}, self.number, {
        get_html : function(){
            return self.number.get_html().attr("placeholder", "from..").removeClass("codingvalue").addClass("from").change(function(){
                $(this).closest(".coding").trigger("sentence-changed");
            });
        }

    });

    self.to = $.extend({}, self.from, {
        get_html : function(){
            return self.from.get_html().removeClass("from").addClass("to").attr("placeholder", "to..");
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
        },
        set_value : function(widget, codingvalue){
            self.default.set_value(widget, codingvalue, true);
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
                hidden.addClass("codebook_value").addClass("codingvalue");

                autocomplete.set(root, schemafield.choices);
                autocomplete.set(descendant, schemafield.choices);

                descendant.on("autocompletechange", function(event, ui){
                    hidden.attr("intval", (ui.item === null) ? self.EMPTY_INTVAL : ui.item.get_code().code);
                    hidden.trigger("change");
                });

                html.append(root).append(descendant).append(hidden);
            } else {
                var input = $("<input>").attr("intval", self.EMPTY_INTVAL).addClass("codingvalue");
                autocomplete.set(input, schemafield.choices);
                html.append(input);

            }

            return html;
        },
        set_value : function(widget, codingvalue){
            self.default.set_value(widget, codingvalue, true);
            if (codingvalue.intval === null) return;

            var schemafield = annotator.models.schemafields[widget.attr("schemafield_id")];
            var code = schemafield.codebook.codes[codingvalue.intval];

            var find_code = function(code){
                return function(choice){
                    return choice.get_code() == code;
                }
            };

            if (!schemafield.split_codebook){
                var choice = $.grep(schemafield.choices, find_code(code))[0];
                return $(".codingvalue", widget).val(choice.label);
            }

            var root = code;
            while (root.parent !== null){
                root = root.parent;
            }

            var root_choice = $.grep(schemafield.choices, find_code(root))[0];
            var child_choice = $.grep(root_choice.descendant_choices, find_code(code))[0];

            // And we've got the labels!
            $(".codebook_root", widget).val(root_choice.label);
            $(".codebook_descendant", widget).val(child_choice.label);
        }

    });

    self.get_widget_type = function(schemafield){
        return self[self.SCHEMATYPES[schemafield.fieldtype]];
    };

    /* GENERAL FUNCTIONS */
    /* Generates an array of dom elements based on a list of schemafields. */
    self.get_html = function(schemafields){
        return $.map(schemafields, function(schemafield){
            var widget, widget_type;

            widget_type = self.get_widget_type(schemafield);
            widget = widget_type.get_html(schemafield);
            widget.attr("schemafield_id", schemafield.id);
            widget.addClass("codingvalue-container widget");

            return widget;
        });
    };

    /* Generates 'label' element based on a schemafield and a widget */
    self.get_label_html = function(schemafield, widget){
        var input = widget.find("input.codingvalue");
        return $("<label>").attr("for", input.attr("id")).text(schemafield.label);
    };

    /* Returns existing widget(s) given a schemafield and a scope
    *
    * @type scope: jQuery element
    * @requires: scope.hasClass("coding") */
    self.find = function(schemafield, scope){
        return scope.find("[schemafield_id={0}]".f(schemafield.id));
    };

    /*
     * Same as get_value, but returns as CodingValue object.
     */
    self.get_codingvalue = function(coding, sentence, widget) {
        var field = annotator.models.schemafields[widget.attr("schemafield_id")];
        var value = self.get_value(widget);

        return {
            sentence: sentence, coding: coding, field : field,
            strval: (value !== null && typeof(value) !== "number") ? value : null,
            intval: (value === null || typeof(value) === "number") ? value : null
        }

    };

    /*
     * Returns a list of codingvalues for the current coding element.
     *
     * @type coding_element: jQuery DOM element
     * @requires: coding_element.hasClass("coding")
     */
    self._get_codingvalues = function(coding_element){
        var coding = annotator.state.codings[coding_element.attr("annotator_coding_id")];
        var sentence_widget = $(".sentence", coding_element);

        // Sentence codings have a special widget with the class 'sentence' which
        // provides the sentence of the coding.
        var sentence = null;
        if (sentence_widget.length > 0){
            sentence = widgets.sentence.get_value(sentence_widget);
        }

        return $.map(coding_element.find(".widget"), function(widget){
            return self.get_codingvalue(coding, sentence, $(widget));
        })
    };

    /*
     * Returns a list of codingvalues, given a DOM element which contains
     * elements with the class 'coding'.
     *
     * @requires: !container.hasClass("coding")
     */
    self.get_coding_values = function(container){
        return $.grep($.map(container.find(".coding"), function(coding_el){
            return self._get_codingvalues($(coding_el));
        }), function(codingvalue){
            return codingvalue.strval !== null || codingvalue.intval !== null;
        });
    };

    self.set_value = function(widget, codingvalue){
        var field = annotator.models.schemafields[widget.attr("schemafield_id")];
        return self.get_widget_type(field).set_value(widget, codingvalue);
    };

    /*
     * Get value of coding. This function looks for an input element with
     * class 'coding', which can either have an attribute 'intval' which
     * will be returned (or null, if EMPTY_INTVAL is set). Else, it will
     * return a string which is equal to the inner value of the input element
     * or null if the value === ''.
     *
     * @param widget: jQuery/DOM element
     * @return: null / int / string
     */
    self.get_value = function(widget){
        var field = annotator.models.schemafields[widget.attr("schemafield_id")];
        return self.get_widget_type(field).get_value(widget);
    };

    return self;
})({});