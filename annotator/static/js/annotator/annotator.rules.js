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

rules = (function(self){
    self.OPERATORS = {
        OR: "OR", AND: "AND", EQUALS: "EQ",
        NOT_EQUALS: "NEQ", NOT: "NOT",
        GREATER_THAN: "GT", LESSER_THAN: "LT",
        GREATER_THAN_OR_EQUAL_TO: "GTE",
        LESSER_THAN_OR_EQUAL_TO: "LTE"
    };

    self.ACTIONS = {
        RED: "display red",
        NOT_CODABLE: "not codable",
        NOT_NULL: "not null"
    };

    /*
     * Get container of coding, given an input-field which represents a coding.
     *
     * @type el: jQuery element
     * @requires: el.hasClass("coding")
     */
    self.get_container_by_input = function(el){
        // Work through hierarchy until we found either a coding-container or
        // the root of this document.
        while (!el.hasClass("coding-container") && (el=el.parent()).length){ }

        if (!el.length){
            throw "No coding-container found for this element."
        }

        return el;
    };

    /*
     *
     */
    self.add = function(html){
        $("input.coding", html).change(self.coding_changed);
    };

    /*
     * Called when a coding has changed and the rules need to be reevaluated.
     */
    self.coding_changed = function(event){
       var container, sentence, schemafield, rules;

       container = self.get_container_by_input($(event.currentTarget));
       sentence = container.attr("sentence_id");
       sentence = (sentence === undefined) ? null : annotator.sentences[sentence];
       schemafield = annotator.fields.schemafields[container.attr("schemafield_id")];

       rules = self.get_field_codingrules()[schemafield.id];

       if (rules === undefined) {
           console.log("No codingrules for field " + schemafield.id);
           return;
       }

       // Check each rule
       var apply = [], not_apply = [];
       $.each(rules, function (i, rule) {
           (self.applies(sentence, schemafield, rule.parsed_condition)
               ? apply : not_apply).push(rule);
       });

       // If a rule not applies, reset their error-state
       $.each(not_apply, function (i, rule) {
           // We mark all input fields in the container belonging to the rule destination
           var inputs = widgets.find(rule.field, sentence).find("input");

           inputs.css("borderColor", "");
           inputs.prop("disabled", false);
           inputs.attr("null", true);
           inputs.attr("placeholder", "");
       });

       $.each(apply, function (i, rule) {
           var inputs = widgets.find(rule.field, sentence).find("input");

           if (rule.field === null || rule.action === null) return;

           var action = rule.action.label;
           if (action === self.ACTIONS.RED) {
               inputs.css("borderColor", "red");
           } else if (action === self.ACTIONS.NOT_CODABLE) {
               inputs.prop("disabled", true);
           } else if (action === self.ACTIONS.NOT_NULL) {
               inputs.attr("null", false);
               inputs.attr("placeholder", "NOT NULL");
           }
       });
    };

    /*
     * Return true if rule applies, false if it is not.
     *
     * @type rule: object
     * @param rule: CodingRule.parsed_condition
     * @type schemafield: Schemafield
     * @type sentence: Sentence object
     */
    self.applies = function (sentence, schemafield, rule) {
        // Create partially applied applies function
        var ra = function (rule) {
            self.applies(sentence, schemafield, rule)
        };

        var truth, assert = function (cond) {
            if (!cond) throw "AssertionError";
        };

        var input_value = widgets.get_value(widgets.find(schemafield, sentence));

        if (rule.type === null) {
            // Empty rule. "Waardeloos waar".
            return true;
        }

        // Resolve other types
        if (rule.type === self.OPERATORS.OR) {
            return ra(rule.values[0]) || ra(rule.values[1]);
        }

        if (rule.type === self.OPERATORS.AND) {
            return ra(rule.values[0]) && ra(rule.values[1]);
        }

        if (rule.type === self.OPERATORS.NOT) {
            return !ra(rule.value);
        }

        if (rule.type === self.OPERATORS.LESSER_THAN) {
            return input_value < rule.values[1];
        }

        if (rule.type === self.OPERATORS.GREATER_THAN) {
            return input_value > rule.values[1];
        }

        if (rule.type === self.OPERATORS.GREATER_THAN_OR_EQUAL_TO) {
            return input_value >= rule.values[1];
        }

        if (rule.type === self.OPERATORS.LESSER_THAN_OR_EQUAL_TO) {
            return input_value <= rule.values[1];
        }

        // rule.type must equal either EQUALS or NOT_EQUALS. Furthermore
        // rule.values[0] must be a codingschemafield and rule.values[1]
        // a value.
        assert(rule.values[0].type === "codingschemafield");
        assert(typeof(rule.values[1]) !== typeof({}));

        truth = input_value == rule.values[1];
        return (rule.type === self.OPERATORS.EQUALS) ? truth : !truth;
    };

    /*
     * Get a field_id --> [rule, rule..] mapping.
     */
    self.get_field_codingrules = function () {
        if (self.field_codingrules !== undefined) {
            return self.field_codingrules;
        }

        var codingrule_fields = {};
        $.each(annotator.fields.codingrules, function (i, rule) {
            var self = this;
            codingrule_fields[rule.id] = [];

            /*
             * Return a list with all nodes in parsed condition tree.
             */
            self.walk = function (node) {
                if (node === undefined) {
                    node = self.parsed_condition;
                }
                var nodes = [node];

                if (node.values !== undefined) {
                    $.merge(nodes, self.walk(node.values[0]));
                    $.merge(nodes, self.walk(node.values[1]));
                } else if (node.value !== undefined) {
                    $.merge(nodes, self.walk(node.value));
                }

                return nodes;
            };

            $.each(self.walk(), function (i, node) {
                if (node.type === "codingschemafield") {
                    if (codingrule_fields[rule.id].indexOf(node.id) === -1) {
                        codingrule_fields[rule.id].push(node.id);
                    }
                }
            });
        });

        // Reverse dictionary
        var field_codingrules = {};
        $.each(codingrule_fields, function (rule_id, fields) {
            $.each(fields, function (i, field_id) {
                var rules = field_codingrules[field_id] = field_codingrules[field_id] || [];
                if (rules.indexOf(rule_id) === -1) rules.push(parseInt(rule_id));
            });
        });

        $.each(field_codingrules, function(field_id, rules){
            field_codingrules[field_id] = $.map(rules, function(rule_id){
                return annotator.fields.codingrules[rule_id];
            });
        });

        self.field_codingrules = field_codingrules;
        return field_codingrules;
    };

    return self;
})({});