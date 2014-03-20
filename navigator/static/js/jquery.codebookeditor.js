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

Array.prototype.remove=function(s){
    var i = this.indexOf(s);

    if(this.indexOf(s) != -1){
        this.splice(i, 1);
    }
};

(function($){
    $.fn.codebookeditor = function(api_url){
        return this.each(function(){
            /*
             * A codebook editor which gets and renders the given
             * url (must point to a codebookhierarchy).
             */
            var self = this;

            /* CONSTANTS */
            self.COLLAPSE_ICON = "/media/img/navigator/collapse-small-silver.png";
            self.EXPAND_ICON = "/media/img/navigator/expand-small-silver.png";
            self.NOACTION_ICON = "/media/img/navigator/noaction-small-silver.png";
            self.API_URL = api_url;

            /* EDITOR STATE VARIABLES */
            self.read_only = $(this).attr("editable") !== "true";
            self.current_label_lang = null;
            self.codebook = null;
            self.languages = null;
            self.moving = false; // Indicates wether the user is moving a code
            self.objects = null; // Flat list of all objects
            self.root = null; // Artificial (non existent in db) root code
            self.changesets = {
               "moves" : {},
               "hides" : {},
               "reorders" : {}
            }; // Changed objects go in here
 
            /* ELEMENTS */
            self.root_el = this;
            self.searchbox = $("<input placeholder='Search..' type='text'>");

            // Buttons
            self.btn_save_changes = $(".save-changes", this);
            self.btn_edit_name = $(".edit-name", this);
            self.btn_download = $(".export", this);
            self.btn_delete = $(".delete", this);
            self.btn_reorder_by_alpha = $(".reorder-alpha", this);
            self.btn_reorder_by_id = $(".reorder-id", this);

            /* PRIVATE METHODS */
            self._escape = function (str) {
                return str.replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;');
            };

            self._search = function (node, regex) {
                var matching = [];

                if (self.highlight(node, regex)) {
                    matching.push(node);
                }

                $.each(node.children, function (i, child) {
                    matching.push.apply(matching, self._search(child, regex));
                });

                return matching;
            };


            self._set_parents = function (object) {
                /*
                 * Creates parent property on each descendents
                 */
                for (var i = 0; i < object.children.length; i++) {
                    object.children[i].parent = object;
                    self._set_parents(object.children[i]);
                }
            };

            self._is_hidden = function () {
                return this.hidden;
            };

            self._set_is_hidden_functions = function (object) {
                /*
                 *  Creates an is_hidden function on each object to
                 *  determine whether it's hidden
                 */
                object.is_hidden = self._is_hidden.bind(object);

                for (var i = 0; i < object.children.length; i++) {
                    self._set_is_hidden_functions(object.children[i]);
                }
            };

            self._initialize_languages = function (objects) {
                /*
                 * Preload all languages for label manager
                 */
                self.languages = objects.results;
            };

            self._codebook_name_initialized = function (codebook) {
                self.codebook = codebook.results[0];
                self.root.label = "Codebook: <i>" + self._escape(self.codebook.name) + "</i>";
                self.update_label(self.root);
            };

            /*
             * Removes duplicate ordernr and sets ordernr according to html elements.
             *
             * @param node: apply function to children of this node
             * @param recusive (default:true): call this function for each child
             */ 
            self._ensure_order = function (node, recursive) {
                // No ordering applicable
                if (node.children.length <= 1) return;
                recursive = (recursive === undefined) ? true : recursive;

                var seen = [], duplicate = false;
                $.each(node.children, function (i, child) {
                    if (seen.indexOf(child.ordernr) !== -1) {
                        duplicate = true;
                    }

                    seen.push(child.ordernr);
                    if (recursive) self._ensure_order(child);
                });

                if (duplicate) {
                    $.each(node.children, function (i, child) {
                        child.ordernr = i;
                        self.changesets.reorders[child.code_id] = child;
                    });
                }
            };

            self._sort_tree = function(tree){
                /*
                 * Sort all .children-arrays according to their ordernr.
                 */
                tree.children.sort(function(a,b){ return a.ordernr - b.ordernr; });
                $.map(self._sort_tree, tree.children);
            };
            
            self._initialize = function (objects) {
                /*
                 * Callback function for getJSON(api_url)
                 */
                if (self.read_only){
                    self.btn_save_changes.hide();
                    self.btn_edit_name.hide();
                    self.btn_reorder_by_alpha.hide();
                    self.btn_reorder_by_id.hide();
                }

                self.root = {
                    "label": "Codebook: ",
                    "code_id": null,
                    "hidden": false,
                    "children": objects
                };

                // Create convenience pointers
                self._set_parents(self.root);
                self._set_is_hidden_functions(self.root);
                self._sort_tree(self.root);
                self._ensure_order(self.root);
                self.objects = self._get_descendents(self.root);


                // Add main action buttons
                $(".loading-codebook", self).contents().remove();
                $(self).append($("<ul>").append(self.render_tree(self.root)).addClass("root").css("margin-left", "-30px"));

                self.searchbox.keyup(self.searchbox_keyup);

                // Remove unneeded icons from root
                $.each(["glyphicon-move", "glyphicon-eye-close", "glyphicon-tags", "glyphicon-arrow-up", "glyphicon-arrow-down"], function (i, cls) {
                    $($("." + cls, self.root_el)[0]).remove();
                });

                if (!($.isEmptyObject(self.changesets.reorders))) {
                    self.btn_save_changes_clicked();
                }

                // Get codebook name
                $.getJSON(self.API_URL + 'codebook?format=json&paginate=false&id=' +
                    $(self.root_el).attr("name"), self._codebook_name_initialized);
            };

            self._get_descendents = function (object) {
                /*
                 * Get all descendents of given object.
                 */
                var result = object.children.slice();

                for (var i = 0; i < object.children.length; i++) {
                    result.push.apply(result, self._get_descendents(
                        object.children[i])
                    );
                }

                return result;
            };

            self._expand_items = function (to_be_closed) {
                /*
                 * Expand given nodes. Close all others.
                 */
                $.each(self.objects, function (i, obj) {
                    if (to_be_closed.indexOf(obj) >= 0) {
                        self.expand(obj.dom_element);
                    } else {
                        self.collapse(obj.dom_element);
                    }
                });
            };

            self._create_options_span = function (obj) {
                var opt_span = $("<span>").addClass("options").append(
                        // Move code button
                        $("<i>").addClass("glyphicon glyphicon-move").attr("title", "Move this code")
                            .click(self.move_code_clicked.bind(obj))
                    ).append(
                        // Unhide button
                        $("<i>").addClass("glyphicon glyphicon-eye-open")
                            .attr("title", "Unhide this code")
                            .click(self.unhide_code_clicked.bind(obj))
                    ).append(
                        $("<i>").addClass("glyphicon glyphicon-eye-close")
                            .attr("title", "Hide this code")
                            .click(self.hide_code_clicked.bind(obj))
                    ).append(
                        // Labels button
                        $("<i>").addClass("glyphicon glyphicon-tags").attr("title", "Show labels")
                            .click(self.show_labels_clicked.bind(obj))
                    ).append(
                        // Create new child button
                        $("<i>").addClass("glyphicon glyphicon-asterisk").attr("title", "Create new child")
                            .click(self.create_child_clicked.bind(obj))
                    ).append(
                        // Move up button
                        $("<i>").addClass("glyphicon glyphicon-arrow-up").attr("title", "Move code up")
                            .click(self.move_code_up_clicked.bind(obj))
                    ).append(
                        // Move down button
                        $("<i>").addClass("glyphicon glyphicon-arrow-down").attr("title", "Move code down")
                            .click(self.move_code_down_clicked.bind(obj))
                    );

                // Hide (un)hide button
                $(".glyphicon-eye-" + (obj.is_hidden() ? 'close' : 'open'), opt_span).hide();

                return opt_span;
            };

            self._create_modal_window = function (id, title, body) {
                /*
                 * Create base modal window (hidden by default).
                 */
                var dialog = $(
                 '<div class="modal">' +
                  '<div class="modal-dialog">' +
                    '<div class="modal-content">' +
                      '<div class="modal-header">' +
                        '<button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>' +
                        '<h4 class="modal-title"></h4>' +
                      '</div>' +
                      '<div class="modal-body"></div>' +
                      '<div class="modal-footer">' +
                        '<button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>' +
                        '<button type="button" class="btn btn-primary">Save changes</button>' +
                      '</div>' +
                    '</div>' +
                  '</div>' +
                '</div>');

                $("#"+id).remove();

                dialog.attr("id", id);
                $(".modal-body", dialog).append(body || "Loading..");
                $("h4", dialog).append(title).addClass("noline");
                $("body").append(dialog);
                return dialog;
            };

            self._create_label_languages = function (dflt) {
                /*
                 * Generates a select element which contains all (preloaded)
                 * languages.
                 */
                var select = $("<select>").css("width", "100px");

                $.each(self.languages, function (i, lan) {
                    var option = $("<option>").attr("value", lan.id).append(
                        $(document.createTextNode(lan.label))
                    );

                    select.append(option);

                    if (lan.id == dflt) {
                        option.attr("selected", "selected");
                    }
                });

                if (dflt === undefined || dflt === null) {
                    $(":first-child", select).attr("selected", "selected");
                }

                return select;
            };

            self._create_label_table_row = function (label) {
                /*
                 * Create a row of a label table, based on given label-object.
                 */
                label = (label === undefined) ? {} : label;

                return $("<tr>").attr("label_id", label.id).append(
                        $("<td>").append(self._create_label_languages(label.language))
                    ).append(
                        $("<td>").append($("<input>").attr("value", label.label))
                    ).append($(
                        "<td>" +
                            "<div class='btn btn-mini btn-danger'>" +
                            "<i class='glyphicon glyphicon-trash'></i>" +
                            "</div>" +
                            "</td>"
                    ).click(function (event) {
                            // Delete row!
                            $(event.currentTarget).parent().remove()
                        }));
            };

            self._create_label_table = function (labels) {
                /*
                 * This function creates a table displayed (typically) in
                 * the manage label modal.
                 *
                 * @param labels: labels to render
                 * @return: table with columns "Language" and "Label"
                 */
                var table, tbody;

                // Base table
                table = $("<table>").append($("<thead>").append(
                            $("<th>Language</th>")
                        ).append(
                            $("<th>Label</th>")
                        ).append(
                            // Empty label for delete icon
                            $("<th>")
                        )).append(
                        (tbody = $("<tbody>"))
                    ).addClass("table table-bordered");

                // Add rows
                $.each(labels, function (i, label) {
                    tbody.append(self._create_label_table_row(label));
                });

                // Add row with 'add row' button
                tbody.append(
                    $("<tr>").append(
                        $("<td>").attr("colspan", 3).css("text-align", "center").append(
                            $("<button>").addClass("btn").append(
                                    $("<i>").addClass("glyphicon glyphicon-plus")
                                ).append(
                                    $(document.createTextNode(" Add label"))
                                ).click(
                                    self.add_label_row_clicked
                                )
                        )
                    )
                );

                return table;
            };

            self._unhide_code_and_children = function (code) {
                /*
                 * Unhide this code and all its children. Stops traversing the tree if
                 * it finds a code which is hidden.
                 */
                if (code.is_hidden()) return;

                $(code.dom_element).removeClass("hide");
                $.each(code.children, function (i, child) {
                    self._unhide_code_and_children(child);
                });

            };

            /* PUBLIC METHODS */
            self.render_tree = function (object) {
                /*
                 * This method renders a tree for the given object. It
                 * does not insert it into the DOM, but is does bind
                 * callbacks to option-icons.
                 *
                 * @param object: object ∊ self.objects | self.root
                 * @return: jQuery li element
                 */
                var code_el = $("<li>").addClass("code collapsable");
                var options_el = self._create_options_span(object).hide();

                if (object.children.length > 0) {
                    code_el.addClass("expanded");
                }

                if (object.is_hidden()) {
                    code_el.addClass("hide");
                }

                /*if (object.codebook_code == null){
                 code_el.addClass("inherited");
                 }*/

                // Add expanding icon to tree
                var action_icon = $("<img>");
                if (object.children.length > 0) {
                    action_icon.attr("src", self.COLLAPSE_ICON).click(
                        self.collapse_clicked.bind(object)
                    );
                } else {
                    action_icon.attr("src", self.NOACTION_ICON);
                }

                // Add action icon and label
                code_el.append(
                    $("<span>").addClass("parts")
                        .append(action_icon)
                        .append($("<span>").addClass("lbl").append(document.createTextNode(object.label)))
                        .append(options_el)
                        .mouseenter(self.options_mouse_enter)
                        .mouseleave(self.options_mouse_leave)
                );

                // Add children (if present) to tree
                var children_el = $("<ul>").addClass("children");

                $.each(object.children, function (i, child) {
                    children_el.append(self.render_tree(child));
                });

                code_el.append(children_el);

                // For quick access later on
                object.dom_element = code_el.get(0);
                object.dom_element.is_visible = true; // jQuery hidden lookup is *slow*
                object.dom_element.object = object;
                object.options_dom_element = options_el;

                return code_el;
            };

            self.update_label = function (code) {
                $("> .parts > .lbl", code.dom_element).html(code.label);
            };

            self.collapse = function (code, animation) {
                /* Collapse a code */
                code = $(code);

                if (!(code.get(0).is_visible) || (code.get(0).object.children.length == 0)) {
                    // Already collapsed | this node is an endpoint
                    return;
                }

                code.children("ul").hide(animation);

                code.children(".parts").children("img").off("click").click(
                    self.expand_clicked
                ).attr("src", self.EXPAND_ICON);

                code.get(0).is_visible = false;
            };

            self.expand = function (code, animation) {
                /* Expand a code */
                var code = $(code);

                if (code.get(0).is_visible || (code.get(0).object.children.length == 0)) {
                    return;
                }

                code.children("ul").show(animation);
                code.children(".parts").children("img").off("click").click(
                    self.collapse_clicked
                ).attr("src", self.COLLAPSE_ICON);

                code.get(0).is_visible = true;
            };

            self.highlight = function (node, regex) {
                /*
                 * Highlight given node with search parameters given. Returns
                 * true if regex was found, false if not.
                 */
                return (regex.exec(node.label) != null);
            };


            self.search = function (nodes, regex) {
                /* Search given nodes for `regex` and collapses / expands
                 * correct nodes.
                 *
                 * @param nodes: array of node-objects
                 * @param regex: query
                 *
                 */
                var matching_nodes = [];

                $.each(nodes, function (i, node) {
                    matching_nodes.push.apply(
                        matching_nodes, self._search(node, regex)
                    );
                });

                // Determine nodes which need to be expanded
                var to_be_expanded = [];
                $.each(matching_nodes, function (i, node) {
                    while ((node = node.parent) !== self.root) {
                        if (to_be_expanded.indexOf(node) == -1) {
                            to_be_expanded.push(node);
                        }
                    }
                });

                self._expand_items(to_be_expanded);

                return matching_nodes;
            };


            /* EVENTS */
            self.collapse_clicked = function (event) {
                /*
                 * Collapse icon clicked. Replace icon and collapse tree
                 */
                self.collapse($(event.currentTarget).parent().parent(), "fast");
            };

            self.expand_clicked = function (event) {
                /*
                 * Expand icon clicked. Replace icon and expand tree
                 */
                self.expand($(event.currentTarget).parent().parent(), "slow");
            };

            self.searchbox_keyup = function (event) {
                var reg = new RegExp(event.currentTarget.value, "i");
                self.search(self.objects, reg);
            };

            self.options_mouse_enter = function (event) {
                if (self.read_only) return;

                if (!self.moving) {
                    $(".options").hide();
                    $(".options", event.currentTarget).fadeIn("fast").css("display", "inline");
                }
            };

            self.options_mouse_leave = function (event) {
                if (self.read_only) return;
                $(".options", event.currentTarget).hide();
            };

            self.hide_code_clicked = function () {
                /* Hide code clicked. This function is bound to an object */

                // Set correct icon
                $(".glyphicon-eye-close", this.options_dom_element).hide();
                $(".glyphicon-eye-open", this.options_dom_element).show();

                $(this.dom_element).addClass("hide");
                $(".code", this.dom_element).addClass("hide");
                this.hidden = true;
                self.changesets.hides[this.code_id] = this;
            };


            self.unhide_code_clicked = function () {
                /* Unhide code clicked. This function is bound to an object */
                this.hidden = false;

                // Set correct icon
                $(".glyphicon-eye-open", this.options_dom_element).hide();
                $(".glyphicon-eye-close", this.options_dom_element).show();

                // If node is root after the loop, a parent has a hide=true property
                var code = this;
                while ((code = code.parent) !== self.root) {
                    if (code.is_hidden()) break;
                }

                if (code === self.root) {
                    self._unhide_code_and_children(this);
                }

                self.changesets.hides[this.code_id] = this;
            };

            self.show_labels_clicked = function () {
                // Create and acivate modal window
                var modal = self._create_modal_window("labels", "Labels of code " + this.code_id).modal();

                modal.on("hidden", function () {
                    $("#labels").remove()
                });

                $(".btn-primary", modal).click(self.save_label_changes_clicked.bind({
                    "new_code": false,
                    "code": this
                }));

                $.getJSON(api_url + 'label?format=json&paginate=false&code__id=' + this.code_id, self.labels_loaded.bind(this));
            };

            self.labels_loaded = function (labels) {
                /*
                 * show_labels_clicked calls the API to request labels for opened
                 * code. This function serves as a callback. It builds and inserts
                 * the editing interface.
                 */
                labels = labels.results;

                // Create table
                var table = self._create_label_table(labels);
                $("#labels .modal-body").contents().remove();
                $("#labels .modal-body").append(table);

                var current_label = this;

                // Because the codebookhierarchy does not return corresponding
                // languages with each label, we have to guess which language
                // the current label has.
                self.current_label_lang = null;
                $.each(labels, function (i, label) {
                    if (current_label.label == label.label) {
                        self.current_label_lang = label.language;
                    }
                });

                // if (self.current_label_lang === null):
                //
                // No label in db corresponds with label given by API. This means
                // that somebody changed the label within the timespan of this
                // codebookeditor instance or this is a newly created child.
            };

            self.add_label_row_clicked = function (event) {
                $(event.currentTarget).parent().parent().before(
                    self._create_label_table_row()
                );
            };

            self._get_label_data = function (rows) {
                /*
                 * Collect data from 'manage labels' table
                 */
                var labels = [];

                $.each(rows, function (i, row) {
                    var label = {};
                    var cells = $("td", row);

                    label.id = $(row).attr("label_id");
                    label.language = $(":selected", cells[0]).attr("value");
                    label.label = $("input", row).attr("value");

                    if (label.label === undefined) {
                        // Last row, probably
                        return;
                    }

                    labels.push(label);
                });

                return labels;
            };

            self._validate_label_data = function (labels) {
                /*
                 * Validate entered data before sending it to the server.
                 *
                 * @return: error message if errors or null if successful
                 */

                // Validate rowcount. Ugly alerts below, but should suffice for now..
                if (labels.length == 0) {
                    // No labels!
                    return ("You should at least enter one label!");
                }
                // Prevent empty labels
                for (var i = 0; i < labels.length; i++) {
                    if (labels[i].label.length == 0) {
                        return ("Row " + (i + 1).toString() + " contains an empty value.");
                    }
                }

                // A language can only occur once
                var seen = [];
                for (var i = 0; i < labels.length; i++) {
                    if (seen.indexOf(labels[i].language) == -1) {
                        seen.push(labels[i].language);
                        continue;
                    }

                    return ("A language can only occur once!");
                }

                return null;
            };

            self.save_label_changes_clicked = function () {
                /*
                 * Called if button "save labels" is clicked. Must be bound to an object
                 * containing at least the boolean property "new_code". Depending on this
                 * value, it futher contains either "code" or "parent".
                 */
                var labels = self._get_label_data($("#labels tbody tr"));
                var error = self._validate_label_data(labels);

                if (error !== null) {
                    alert(error);
                    return;
                }

                // Validation complete!
                $("#labels").modal("hide");

                // Create "saving labels" modal
                var loading_modal = self._create_modal_window("loading_modal");
                $(".modal-header", loading_modal).remove();
                $(".modal-footer", loading_modal).remove();
                $(".modal-body", loading_modal).html("Saving labels..");

                $(loading_modal).modal({
                    keyboard: false,
                    backdrop: "static"
                });

                var callback_data = { "labels": JSON.stringify(labels) };
                var callback_func = null;

                if (this.new_code == true) {
                    callback_data.parent = this.parent.code_id;
                    callback_data.ordernr = this.parent.children.length;
                    callback_func = self.new_code_created;
                } else {
                    callback_data.code = this.code.code_id;
                    callback_func = self.labels_updated;
                }

                // Send results to server
                $.post(
                    window.location.href + "save-labels/",
                    callback_data, callback_func.bind({
                        "labels": labels,
                        "code": this.code,
                        "parent": this.parent
                    }), "json"
                );
            };

            self.labels_updated = function () {
                /*
                 * Called when labels are saved to server.
                 */
                $("#loading_modal").modal("hide").remove();

                var _found = false;
                for (var i = 0; i < this.labels.length; i++) {
                    if (this.labels[i].language == self.current_label_lang) {
                        this.code.label = this.labels[i].label;
                        _found = true;
                        break;
                    }
                }

                // Previous language removed?
                if (!_found) {
                    this.code.label = this.labels[0].label;
                }

                // Reset value
                self.current_label_lang = null;
                self.update_label(this.code);
            };

            self.new_code_created = function (new_code) {
                /*
                 * Called when new code is created in tree.  This function
                 * creates its DOM element and updates references where
                 * needed
                 */
                $("#loading_modal").modal("hide").remove();

                // Init new code
                new_code.children = [];
                new_code.hidden = false;
                new_code.parent = this.parent;
                new_code.label = this.labels[0].label;
                new_code.ordernr = this.parent.children.length;
                self._set_is_hidden_functions(new_code);
                this.parent.children.push(new_code);
                self.objects.push(new_code);

                // Render new code
                $($(".children", this.parent.dom_element)[0]).append(self.render_tree(new_code));
                self._update_collapse_icons(new_code, this.parent);
            };

            self.move_code_clicked = function(){
                var code = $(this.dom_element);
                $(".options", self.root_el).hide();

                // Collapse code
                if (this.dom_element.is_visible){
                    self.collapse(this.dom_element, "fast");
                }

                $(this.dom_element).children("img").off("click");
                code.addClass("moving");

                // Add help
                code.append(
                        $(document.createTextNode(" "))
                    ).append(
                        $("<i>").addClass("glyphicon glyphicon-question-sign move-help").click(
                            self.move_help_clicked
                        )
                    );

                // Mark destinations as such
                $(".parts", self.root_el)
                        .addClass("moving_destination")
                        .click(self.move_destination_clicked.bind(this))
            };

            self.move_help_clicked = function(){
                var base = self._create_modal_window("move_help", "Move instructions");

                $(".btn-primary", base).remove();
                $("a.btn", base).html("OK");
                $(".modal-body", base).html(
                    "<p>To move a code, bla..</p>"
                );

                base.modal();
            };

            self._update_collapse_icons = function () {
                /*
                 * Updates collapse icons for all given codes.
                 *
                 * @for each arg: arg ∈ (self.objects ∪ {self.root})
                 */
                $.each(arguments, function (i, code) {
                    var img = $("img", $(code.dom_element).children(".parts"));

                    // Disable listeners
                    img.off("click");

                    // Check which icon needs to be displayed
                    if (code.children.length == 0) {
                        // No children, display NOACTION
                        img.attr("src", self.NOACTION_ICON);
                    } else {
                        // Children present
                        img.attr("src", self.COLLAPSE_ICON);
                        img.click(self.collapse_clicked.bind(code));
                    }

                });
            };

            self.move_destination_clicked = function (event) {
                /*
                 * A move destination was clicked. Update relevant codes.
                 */
                if (!self.moving) {
                    return (self.moving = true);
                }

                var new_parent_el = $(event.currentTarget.parentNode);
                var new_parent_obj = new_parent_el.get(0).object;
                var old_parent_obj = this.parent;

                if (new_parent_obj == this) {
                    // Self clicked, do nothing.
                    return (self.moving = false);
                }

                // Update state
                this.parent.children.remove(this);
                this.parent = new_parent_obj;
                this.parent.children.push(this);

                self._update_collapse_icons(old_parent_obj, new_parent_obj);

                // Update GUI
                $(".moving_destination").off("click").removeClass("moving_destination");
                $(".moving").removeClass("moving");
                $(".move-help", this.dom_element).remove();
                $(this.dom_element).prependTo($(".children", new_parent_el).get(0));
                self.expand(this.dom_element, "slow");

                self.changesets.moves[this.code_id] = this;
                self.moving = false;
            };

            self.create_child_clicked = function () {
                var modal = self._create_modal_window("labels", "Labels new code").modal("show");

                $(".btn-primary", modal).click(self.save_label_changes_clicked.bind({
                    new_code: true, parent: this
                }));

                // Create new labels table
                self.labels_loaded({results: [
                    {"language": 1, "label": "?"}
                ]});
            };

            self.move_code_up_clicked = function () {
                self.move_code(this, -1);
            };

            self.move_code_down_clicked = function () {
                self.move_code(this, 1);
            };

            self.move_code = function (code, change) {
                var codes = code.parent.children;
                var index = codes.indexOf(code);
                var swap_with, swap_with_ordernr;

                // TODO: gernalise for change other than abs(change) === 1
                if (change === 1) {
                    if (index === codes.length - 1) return;
                    swap_with = codes[index + change];
                } else if (change === -1) {
                    if (index === 0) return;
                    swap_with = codes[index + change];
                } else {
                    throw "move_code does not implemented changes of " + change + " yet.";
                }

                // Swap ordernrs
                swap_with_ordernr = swap_with.ordernr;
                swap_with.ordernr = code.ordernr;
                code.ordernr = swap_with_ordernr;

                // Swap in children list
                codes[index] = swap_with;
                codes[index + change] = code;

                // Swap DOM elements
                if (change < 0){
                    $(swap_with.dom_element).before($(code.dom_element));
                } else {
                    $(code.dom_element).before($(swap_with.dom_element));
                }

                // Add to changeset
                self.changesets.reorders[code.code_id] = code;
                self.changesets.reorders[swap_with.code_id] = swap_with;
            };

            self.btn_reorder_by_alpha_clicked = function () {
                self.reorder(function (a, b) {
                    if (a.label.toLowerCase() < b.label.toLowerCase()) return -1;
                    if (a.label.toLowerCase() > b.label.toLowerCase()) return 1;
                    return 0;
                });
            };

            self.btn_reorder_by_id_clicked = function () {
                self.reorder(function (a, b) {
                    return a.code_id - b.code_id;
                });
            };

            self.reorder_confirm = function (sort_func) {
                var dialog = self._create_modal_window(
                    "reordering-confirm", "Irreversible action",
                    $("<p>").append("Your changes need to be saved to allow reordering.")
                ).modal("show");

                $(".btn-primary", dialog).click(function () {
                    $(this).attr("disabled", "true");
                    $(".btn-default", dialog).attr("disabled", "true");
                    $(this).text("Reordering..");

                    self.reorder(sort_func, self.root);
                    dialog.modal("hide");

                    // Call btn_save_changes_clicked with callback function
                    // bound (which gets called after changes have been saved)
                    self.btn_save_changes_clicked.bind(function () {
                        location.reload();
                    })();
                });

            };

            /*
             * 
             */
            self.reorder = function (sort_func, node) {
                if (node === undefined) return self.reorder_confirm(sort_func);

                node.children.sort(sort_func);
                $.each(node.children, function (i, child) {
                    child.ordernr = i;
                    self.changesets.reorders[child.code_id] = child;
                    self.reorder(sort_func, child);
                });
            };

            self.btn_edit_name_clicked = function () {
                /*
                 * This opens a new window which enables the user to edit the name
                 * of this codebook.
                 */
                var wdw = self._create_modal_window("edit_name", "Edit name of this codebook", $(
                    "<input class='input' type='text'>"
                ).attr("value", self.codebook.name)).modal();

                $(".btn-primary", wdw).click(self.edit_name_save);
            };

            self.edit_name_save = function () {
                /*
                 * This function is fired when "save changes" is clicked on
                 * the modal created in self.btn_edit_name_clicked.
                 */
                var name = $(".modal-body input", $("#edit_name")).attr("value").trim();

                if (name.length <= 0) {
                    alert("Codebook names can't be empty");
                    return;
                }

                // Validation complete
                $("#edit_name").modal("hide").remove();

                // Create "saving name" modal
                var loading_modal = self._create_modal_window("loading_modal").modal({
                    keyboard: false,
                    backdrop: "static"
                });

                $(".modal-header", loading_modal).remove();
                $(".modal-footer", loading_modal).remove();
                $(".modal-body", loading_modal).html("Saving codebook name..");

                // Send name to server
                $.post(
                    window.location.href + "change-name/",
                    {"codebook_name": name}, (function () {
                        self.root.label = "Codebook: <i>" + self._escape(name) + "</i>";
                        self.update_label(self.root);
                        $("#loading_modal").modal("hide").remove();
                    }).bind(name)
                );
            };

            self.btn_edit_name.click(self.btn_edit_name_clicked);
            self.btn_reorder_by_alpha.click(self.btn_reorder_by_alpha_clicked);
            self.btn_reorder_by_id.click(self.btn_reorder_by_id_clicked);

            self.btn_save_changes_clicked = function () {
                var moves = [], hides = [], reorders = [];

                // Get all moves
                $.each(self.changesets.moves, function (id, code) {
                    moves.push({ new_parent: code.parent.code_id, code_id: code.code_id });
                });

                // Get hides
                $.each(self.changesets.hides, function (id, code) {
                    hides.push({ code_id: code.code_id, hide: code.hidden });
                });

                // Get reorders
                $.each(self.changesets.reorders, function (id, code) {
                    reorders.push({ code_id: code.code_id, ordernr: code.ordernr });
                });

                // Create "saving changesets" modal
                var loading_modal = self._create_modal_window("loading_modal").modal({
                    keyboard: false,
                    backdrop: "static"
                });

                $(".modal-header", loading_modal).remove();
                $(".modal-footer", loading_modal).remove();
                $(".modal-body", loading_modal).html("Saving changesets..");

                $.post(
                    window.location.pathname + 'save-changesets/', {
                        "moves": JSON.stringify(moves),
                        "hides": JSON.stringify(hides),
                        "reorders": JSON.stringify(reorders)
                    }, (function () {
                        $("#loading_modal").modal("hide").remove();
                        self.changesets.moves = {};
                        self.changesets.hides = {};
                        self.changesets.reorders = {};

                        if (typeof(this) === "function") this();
                    }).bind(this)
                );

            };

            self.btn_save_changes.click(self.btn_save_changes_clicked);

            /* Call init function after AJAX call */
            $.getJSON(api_url + 'codebookhierarchy?format=json&id=' + $(self.root_el).attr("name"), self._initialize);
            $.getJSON(api_url + 'language?format=json&order_by=id&paginate=false&page_size=100', self._initialize_languages);
        });
    };
})(jQuery);

