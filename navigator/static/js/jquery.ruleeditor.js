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

_keymap = {
    37 : "left",
    38 : "up",
    39 : "right",
    40 : "down",
    74 : "down",    // J
    75 : "up",      // K
    72 : "left",    // H
    76 : "right",   // L
    9 : "tab",      // Tab
    27 : "done",    // Esc
    73 : "start",   // I
    13 : "start",   // Enter
    46 : "delete",  // Enter
    83 : "save",    // s
    45 : "insert",  // insert
    65 : "insert",  // a
}

jQuery.fn.ruleeditor = function(api_url, schemaid, projectid){
    // Prevent scoping issues
    var self = this;

    // Set constants
    self.API_URL = api_url;
    self.SCHEMA_ID = schemaid;
    self.PROJECT_ID = projectid;
    self.LOADING_STEPS = 7;
    self.KEYCODE_ENTER = 13;
    self.ERROR_COLOUR = "#f2dede"; // Taken from bootstrap.css
    self.INFO_COLOUR = "#d9edf7";
    self.N_COLS = 4;

    // Debug variables
    self.initialising_done = false;
    
    // Get UI elements
    self.bar = $("[name=loading] .bar");
    self.btn_save = $(".btn[name=save]");
    self.btn_add_field = $(".btn[name=add-field]");
    self.btn_undo = $(".btn[name=undo]");
    self.btn_redo = $(".btn[name=redo]");
    self.table = $("table[name=schema]");

    // Pnotify balloon
    self.current_message = null;

    // JSON data
    self.rules;
    self.fieldtypes; // Types of each field (apply --> ModelChoice, etc.)

    self.model_choices = {
        action : [], // CodingRuleAction
        field : [], // CodingSchemaField
    }

    // Statekeeping values
    self.loading_percent = 0;
    self.editing = false;
    self.active_cell = { x: 0, y : 0 };

    // PRIVATE FUNCTIONS //
    self._set_progress = function(){
        $.each(self.bar, function(i, el){
            el.style.width = self.loading_percent + "%";
        });

        if (self.loading_percent >= 99.5){
            $("[name=loading]").remove();
            self.initialising_done();
        }
    }

    self._reverse_dict_lookup = function(dict, val){
        var res = [];

        $.each(dict, function(k, v){
            if (v == val){
                res.push(k);
            }
        });

        return res;
    };

    self._dictlist_lookup = function(dictlist, attr, value){
        /*
         * Search a list of dictionaries. Return first dict where
         *
         *  dict[attr] == value
         *
         * Throws an exception when no dictionary matches the given
         * values
         */
        for(var i=0; i < dictlist.length; i++){
            if(dictlist[i][attr] == value){
                return dictlist[i];
            }
        }

        throw "Value '" + value + "' not found in dictlist";
    }

    self._find_parent = function(el, tagName){
        /*
         * Traverse upwards in the DOM tree, until an element of
         * type `tagName` is found. Returns null if no element
         * matches this condition.
         *
         * If no tagName is given, return parent of el.
         */
        if (tagName === undefined){
            return $(el).parent()||null;
        }

        // Traverse upwards
        while ((el = $(el).parent()).length){
            if (el.get(0).tagName.toLowerCase() == tagName.toLowerCase()){
                return el;
            }
        }

        return null;
    }

    self._get_api_url = function(resource, filters){
        filters = (filters === undefined) ? {} : filters;

        // Request json and do not paginate response
        filters['paginate'] = 'false';
        filters['format'] = 'json';
        filters['page_size'] = '9999';

        // Calculate url 
        return self.API_URL + resource + "?" +
                self.encode_url_params(filters);
    }

    self._create_delete_button = function(){
        var btn = $(
            "<div class='delete btn btn-mini btn-danger'>" +
            "<i class='glyphicon glyphicon-trash'></i>" +
            "</div>"
        );

        btn.click(self.delete_button_clicked);
        return btn;
    }

    self._get_tr_by_fieldnr = function(fieldnr){
        var trs = $("tbody tr", self.table);

        for (var i=0; i < trs.length; i++){
            if ($(trs[i]).children(":eq(1)").text() == fieldnr){
                return $(trs[i]);
            }
        }

        throw "Error: No field with fieldnr " + fieldnr + " found!"
    }

    // PUBLIC FUNCTIONS //
    self.increase_progress = function(){
        self.loading_percent += 100 / self.LOADING_STEPS;
        self._set_progress();
    }

    self._escape = function(str){
        return str.replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');
    }

    self.encode_url_params = function(params){
        var res = "";

        $.each(params, function(key, val){
            res += "&";
            res += escape(key);
            res += "=";
            res += escape(val);
        });

        if (res.length > 0){
            return res.substr(1, res.length);
        }

        return res;
    }


    self.api_get = function(resource, callback_success, filters, callback_error){
        // Handle default function parameters
        callback_error = (callback_error === undefined) ? self.standard_error : callback_error;

        var url = self._get_api_url(resource, filters)
        $.getJSON(url).success(callback_success).error(callback_error);

        // console.log("Getting " + url);
    }

    self.api_post = function(resource, callback_success, data, filters, callback_error){
        // Handle default function parameters
        callback_error = (callback_error === undefined) ? self.standard_error : callback_error;

        $.post(
            self._get_api_url(resource, filters),
            data, callback_success, 'json'
        ).error(callback_error);

        console.log("Getting (POST) " + self._get_api_url(resource, filters));
    }

    self.api_options = function(resource, callback_success, filters, callback_error) {
	// Handle default function parameters
        callback_error = (callback_error === undefined) ? self.standard_error : callback_error;
	url = self._get_api_url(resource, filters);

	console.log("HTTP OPTIONS "+url);
	
	$.ajax({
	    type: "OPTIONS",
	    url: url,
	    success: callback_success
	});
	    

    }

    self.add_row = function(field, add_to_state){
        /*
         * Add a row to the table. This also means that an entry is created
         * in the state-keeping variables. Arguments left empty, are filled
         * with 'null'.
         */
        var tr, td, name, type, choices, serialiser;
        field = (field === undefined) ? {} : field;

        var defaults = {
            "delete" : self._create_delete_button,
        }

        tr = $("<tr>").attr("id", field.id);

        // Add each field to table
        var new_state = {};
        $.each($("th", self.table), function(i, el){
            var field_name = $(el).attr("name");

            td = $("<td>");
            if (defaults[field_name] && field[field_name] === undefined) {
                new_state[field_name] = defaults[field_name]();
                td.append(new_state[field_name]);
            } else {
                type = self.fieldtypes[field_name];
                choices = self.model_choices[field_name];
                serialiser = jQuery.fn.djangofields.get(type, "serialise");
                new_state[field_name] = field[field_name] || null;
                td.append(serialiser(new_state[field_name], choices));
            }

            tr.append(td.dblclick(self.cell_clicked));
        });

        delete new_state['delete'];
        if (add_to_state){
            self.rules.push(new_state);
            new_state.tr = tr.get(0);
        }

        $("tbody", self.table).append(tr);
        return tr.get(0);
    }

    self.initialise_table = function(){
        // Add each field to table
        $.each(self.rules, function(i, rule){
            rule.tr = self.add_row(rule);
        });

        $("tbody", self.table).css("cursor", "pointer");
    }

    self.initialise_buttons = function(){
        self.btn_save.removeClass("disabled");
        self.btn_save.click(self.btn_save_clicked);
        self.btn_add_field.removeClass("disabled");
        self.btn_add_field.click(self.btn_add_field_clicked);
        $("html").click(self.document_clicked);
    }

    self.initialise_shortcuts = function(){
        document.addEventListener('keydown', function(event) {
            self[_keymap[event.keyCode] + "_pressed"](event);
        });

        self.update_active_cell();
    }

    /*
     * Repaints active cell.
     * 
     * @return: active cell (jQuery element)
     */
    self.update_active_cell = function(){
        // Remove all active cell markups
        $("td.active", self.table).removeClass("active");
        return $(self.get_active_cell()).addClass("active");
    }

    /* Moves n cells forward. Does not wrap around top and bottom borders. */
    self.move_cells = function(n){
        var n_rows = $("tr", self.table).length - 1;
        var new_pos = (self.active_cell.x + self.active_cell.y * self.N_COLS) + n;

        // Make sure it doesn't overflow / underflow.
        if (new_pos < 0 || new_pos >= n_rows * self.N_COLS){
            return;
        }

        self.active_cell.x = Math.floor(new_pos % self.N_COLS); // Kung-fu fighting.. javascript!
        self.active_cell.y = Math.floor(new_pos / self.N_COLS);

        var cell = self.update_active_cell();

        // Check if the active cell is visible, and if not scroll page
        if (cell.offset().top <= document.body.scrollTop){
            window.scrollBy(0,-4*cell.height());
        } else if (cell.offset().top + cell.height() >= document.body.scrollTop + window.innerHeight) {
            window.scrollBy(0,4*cell.height());
        }
    }

    self.down_pressed = function(event){
        if(self.editing) return;
        self.move_cells(self.N_COLS);
        event.preventDefault();
    }

    self.up_pressed = function(event){
        if(self.editing) return;
        self.move_cells(-self.N_COLS);
        event.preventDefault();
    }

    self.left_pressed = function(event){
        if(self.editing) return;
        self.move_cells(-1);
    }

    self.right_pressed = function(event){
        if(self.editing) return;
        self.move_cells(1);
    }

    self.insert_pressed = function(event){
        if(self.editing) return;
        event.preventDefault();
        self.btn_add_field.click();

        self.active_cell.y = self.rules.length - 1;
        self.active_cell.x = 0;
        self.update_active_cell();
        $(self.get_active_cell()).dblclick();
    }

    self.delete_pressed = function(event){
        var row = $(self.get_active_cell()).parent();

        if(self.editing){
            $(".select-nil", row).click();
        } else {
            $(".delete", row).click();
            self.update_active_cell();
        }

    }

    self.done_pressed = function(event){
        $("html").click();
    }

    self.save_pressed = function(event){
        if(event.ctrlKey){
            event.preventDefault();
            self.btn_save.click();
        }
    }

    self.tab_pressed = function(event){
        event.preventDefault();
        $("html").click();

        if(event.shiftKey){
            self.left_pressed(event);
        } else {
            self.right_pressed(event);
        }

        $(self.get_active_cell()).dblclick();
    }

    self.start_pressed = function(event){
        if(self.editing) return;
        event.preventDefault();
        $(self.get_active_cell()).dblclick();
    }

    self.undefined_pressed = function(event){
        // Other key pressed. Handle?
    }

    self.initialising_done = function(){
        /* This function is called when all data is ready */
        if (self.initialising_done === true){
            console.log("Initialising twice?");
        }

        self.initialise_table();
        self.initialise_buttons();
        self.initialise_shortcuts();
        self.initialising_done = true;
    }

    // CALLBACK FUNCTIONS //
    self.td_hovered = function(event){
        /*
         * This function needs to be bound to an array:
         *
         *   [type, messages]
         *
         * @param type: type of message to be displayed (info / error)
         * @type type: string
         *
         * @param messages: messages to be displayed
         * @type messages: array with jQuery objects or strings
         */
        var type = this[0];
        var msgs = this[1];

        if (self.current_message == null){
            self.current_message = $;
        }

        if (msgs.length != 1){
            self.current_message.pnotify({
                "title" : "Whoops.",
                "text" : "Multiple error messages per cell are not yet supported.",
                "type" : "error",
                "shadow" : false,
                nonblock: true,
                hide: false,
                closer: false,
                sticker: false
            });
            return;
        }

        self.current_message = self.current_message.pnotify({
            "title" : type, "type" : type, "text" : self._escape(msgs[0]), "shadow" : false, 
            nonblock: true, hide: false,closer: false, sticker: false
        });

    }

    self.save_callback = function(all_errors){
        // Errors found?
        var errors_found = false;
        $.each(all_errors.fields, function(){ errors_found = true; }); 

        // Should we redirect?
        if (this == true && !errors_found){
            // Uncomment line below to enable redirecting
            //window.location = all_errors['schema_url'];
            //return;
            $.pnotify({
                "title" : "Done",
                "text" : "Schema saved succesfully.",
                "type" : "success",
                "delay" : 500
            });
        }
        
        // Enable save button
        self.btn_save.text("Save");
        self.btn_save.removeClass("disabled");

        var info_msg = "To investigate encountered errors, " +
                         "hover over red-marked areas";

        // Uncolour each td
        $.each($("td", self.table), function(i, td){
            $(td).css("background-color", "");
            $(td).off("hover");

            if (errors_found){
                $(td).hover(self.td_hovered.bind(
                    ["info", [info_msg]]
                ));
            }
        });

        if(!errors_found && self.current_message !== null){
           self.current_message.pnotify_remove(); 
           self.current_message = null;
        } else if (errors_found) {
            self.td_hovered.bind(["info", [info_msg]])();            
            $.pnotify({
                "title" : "Schema cannot be saved.",
                "text" : "Errors occured while checking this schema for errors.",
                "type" : "error",
            });
        }
    
        // Colour tds with error
        var tr, th, td;
        $.each(all_errors.fields, function(fieldnr, errors){
            tr = self._get_tr_by_fieldnr(fieldnr);

            $.each(errors, function(field_name, error){
                th = $("th[name=" + field_name + "]", self.table).get(0);

                td = tr.children().get(th.cellIndex);

                $(td).off("hover");
                $(td).css("background-color", self.ERROR_COLOUR);
                $(td).hover(self.td_hovered.bind(["error", error]));
            });
        });
    }

    self.standard_error = function(data){
        console.log(data);
    }
    
    // EVENTS //
    self.delete_button_clicked = function(event){
        // Delete row
        $(event.currentTarget).parent().parent().remove();
        self.update_active_cell();
    }

    self.btn_save_clicked = function(event){
        self.save();
    }

    self.btn_add_field_clicked = function(event){
        self.add_row({
            "label" : "New rule (" + self.rules.length + ")",
            "condition" : "()"
        }, true);

        self.save(false);
    }

    self._get_fieldnr = function(td){
        return parseInt($(td).parent().children(":first-child").text()) - 1;
    }

    self.document_clicked = function(event){
        /*
         * This function unfocuses widgets if needed
         */
        if (self.widget_clicked || !self.editing){
            self.widget_clicked = false;
            return;
        }

        self.widget_focusout();
    }

    self.get_td = function(x, y){
        var tr = $("tbody > tr", self.table)[y];
        return $("td", tr)[x+1];
    }

    self.get_active_cell = function(){
        return self.get_td(self.active_cell.x, self.active_cell.y);
    }

    self.cell_clicked = function(event){
        var target = $(event.currentTarget);
        var th = $($("th", self.table)[target[0].cellIndex]);
        var tr = self._find_parent(target, "tr").get(0);
        var field = self._dictlist_lookup(self.rules, "tr", tr);

        // Check wether field is editable
        if (th.attr("editable") != "true" || self.editing){
            // Field is not editable or we're already editing
            return;
        }

        // Get widget
        var field_name = th.attr("name");
        var field_choices = self.model_choices[field_name];

        var value = field[field_name];
        var type = self.fieldtypes[field_name];
        var widget = jQuery.fn.djangofields.get(type, "to_widget")(value, field_choices);

        // Does this field allow a null value? If so, add a 'null' button
        var cont = null;
        if (th.attr("null") == "true"){
            var btn_null = $(" <div class='btn btn-primary select-nil'>∅</div>");
            btn_null.click(self.widget_null_clicked);

            cont = $("<div name='null-form' class='form-inline'>");
            cont.append(widget);
            cont.append("<span> </span>");
            cont.append(btn_null);
        }

        // Insert widget
        target.contents().remove();
        target.append(cont||widget);
        widget.keyup(self.widget_keyup);

        // Focus textinput widgets
        widget.focus();

        // To prevent unfocusing (clicking table) when user
        // actually clicks widget
        (cont||widget).click(function(){
            self.widget_clicked = true;
        });

        self.editing = widget;
    }

    self.widget_focusout = function(event, value){
        var td = self._find_parent(self.editing, "td")
        var th = $($("th", self.table)[td[0].cellIndex]);
        var tr = self._find_parent(td, "tr").get(0);
        var field = self._dictlist_lookup(self.rules, "tr", tr);

        // Get value
        var field_name = th.attr("name");
        var field_choices = self.model_choices[field_name];
        var type = self.fieldtypes[field_name];

        if (value === undefined){
            // Value was not overidden
            value = jQuery.fn.djangofields.get(type, "from_widget")
                     (self.editing, field_choices);
        }

        if (field_name === "label"){
            var found = false;
            $.each(self.rules, function(i, field){
                if (field.tr === tr) return;
                if (field.label.toLowerCase() === value.toLowerCase()) found = true;
            });

            if(found){
                $.pnotify({
                    "title" : "Duplicate",
                    "text" : "There is already a field named '" + value + "'. Are you sure you wan't to continue?",
                    "type" : "warning"
                });
            }
        }


        // Set value to state
        field[field_name] = value;

        // Remove widget
        td.contents().remove();
        td.append(jQuery.fn.djangofields.get(type, "serialise")(value, self.model_choices[field_name]));

        self.save(false);
        self.editing = false;
    }

    self.widget_null_clicked = function(event){
        self.widget_focusout(event, null);
    }

    // OPTIONS INITIALISED //
    self.codingschemafield_options_initialised = function(options){
        self.increase_progress();
    }

    self.codingrule_options_initialised = function(options){
        self.fieldtypes = options["fields"];
        self.increase_progress();
    }

    self.codingruleaction_options_initialised = function(options){
        // ??
        self.increase_progress();
    }

    // API_GETS INITIALISED //
    self.codingrules_initialised = function(rules){
        self.rules = rules["results"];
        self.increase_progress();
    }

    self.codingruleactions_initialised = function(actions){
        self.model_choices["action"] = actions["results"];
        self.increase_progress();
    }

    self.codingschemafields_initialised = function(schemafields){
        self.model_choices["field"] = schemafields["results"];
        self.increase_progress();
    }

    // MAIN FUNCTIONS //
    self.main = function(){
        // Get all rules and their fieldtypes of this schema
        self.api_options("codingrule", self.codingrule_options_initialised);
        self.api_get("codingrule", self.codingrules_initialised, {"codingschema__id" : self.SCHEMA_ID});

        // Get actions which can be selected in 'apply' box
        self.api_get("codingruleaction", self.codingruleactions_initialised);
        self.api_options("codingruleaction", self.codingruleaction_options_initialised);

        // Get schemafields belonging to this schema
        self.api_get("codingschemafield", self.codingschemafields_initialised, {"codingschema__id" : self.SCHEMA_ID});
        self.api_options("codingschemafield", self.codingschemafield_options_initialised);

        // Initialising 'done'
        self.increase_progress();
    }

    self.save = function(commit){
        /*
         * Save current state to server. If commit is false, it will only
         * check for errors.
         *
         * @param commit: commit state to database
         * @type commit: boolean (default: true)
         */
        // If commit is not given, it is true
        commit = (commit === undefined) ? true : commit;

        var rule, rules = [];
        $.each($("tbody tr", self.table), function(i, tr){
            rule = self._dictlist_lookup(self.rules, "tr", tr);
            rules.push($.extend({}, rule));
            delete rules[i]["tr"];

            if (rules[i].id === null){
                delete rules[i]["id"];
            }
        });

        // Send data to server for checking / comitting
        $.post(
            window.location + '?commit=' + commit, {
                rules : JSON.stringify(rules)                
            },
            self.save_callback.bind(commit)
        );

        // Disable save button
        self.btn_save.text("Checking..");
        self.btn_save.addClass("disabled");
    }

    return self;
}

