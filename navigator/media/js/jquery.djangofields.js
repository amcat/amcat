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

jQuery.fn.djangofields = {
    /*
     * This 'module' is used  to (de)serialise and widgitise json values
     * based on given 'Django Field' types. Each field-'class' consists
     * of four functions:
     *
     *  to_widget: converts a value to an HTML-value
     *  from_widget: coverts a widget to a value
     *  serialise: converts a value to a displayable value (jQuery element)
     *  deserialise: converts a displayable value to a value (obj)
     *
     * Each function takes two arguments: a value (widget, obj, etc) and
     * 'choices'. The second one may be empty depending on the fieldtype.
     *
     */
    get : function(fieldtype, func){
        var fieldcls = jQuery.fn.djangofields[fieldtype];

        if (fieldcls === undefined){
            throw "Error: fieldclass " + fieldtype + " does not exist!";
        }

        // If no function can be found on the specific FieldClass, return
        // function from BaseField.
        return fieldcls[func] || jQuery.fn.djangofields.BaseField[func];
    },
    BaseField : {
        to_widget : function(current_value, choices){
            return $("<input type='text' value='" + (current_value||'') + "' />");
        },
        from_widget : function(widget, choices){
            return widget.attr("value");
        },
        serialise : function(obj, choices){
            if (obj === null){
                return $("<span>null</span>").attr("class", "badge");
            }

            return $(document.createTextNode(obj));
        },
        deserialise : function(str, choices){
            throw "Error: Not yet implemented";
        }
    },
    CharField : {
        // Same as Basefield
    },
    IntegerField : {

    },
    BooleanField : {
        serialise : function(obj){
            var icon = (obj) ? "ok" : "remove";
            return $("<i class='icon-" + icon + "'>");
        },
        to_widget : function(val){
            var checkbox = $("<input type='checkbox'>");
            return (val) ? checkbox.attr("checked", "checked") : checkbox;
        },
        from_widget : function(widget){
            return widget.attr("checked") == "checked";
        }
    },
    ModelChoiceField : {
        serialise : function(obj, choices){
            if (obj === null){
                return jQuery.fn.djangofields.BaseField.serialise(obj);
            }

            for (var i=0; i < choices.length; i++){
                if (choices[i].id == obj){
                    return choices[i].name;
                }
            }

            console.log(choices);
            throw "Error: could not find '" + obj + "' in available choices!";            
        },
        to_widget : function(val, choices){
            var select = $("<select>");

            var option;
            $.each(choices, function(i, choice){
                option = $("<option>").attr("value", i);
                option.append(document.createTextNode(choice.name));

                if(val == choice.id){
                    option = option.attr("selected", "selected");
                }

                select.append(option);
            });

            return select;
        },
        from_widget : function(val, choices){
            return choices[parseInt(val.attr("value"))].id;
        }
    }
};


