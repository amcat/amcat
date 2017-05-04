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

define(["jquery", "bootstrap-multiselect"], function($){
    "use strict";

    const url_plugin_by_name =
        (project, plugin_name) => `/api/v4/projects/${project}/upload_plugins/?name=${plugin_name}`;
    const url_plugin = (project, plugin_id) => `/api/v4/projects/${project}/upload_plugins/${plugin_id}/`;

    const FIELD_NEW = "new_field";
    const FIELD_IGNORE = "-";
    const DEFAULT_TYPE = "default";

    const table = $("#table-fieldmap");
    const presetSaveButton = $("#preset-save");
    const presetSaveNameField = $("#preset-save-name");
    const presetLoadSuggestedButton = $("#preset-load-suggested");
    const presetLoadClearButton = $("#preset-load-clear");



    class Field {

        constructor(destination, new_name, type){
            this.destination = destination;
            this.new_name = new_name;
            this.type = type;
        }

        toString(){
            let value = null;
            if(this.destination !== FIELD_NEW){
                value = this.destination;
            }
            else if(this.type === DEFAULT_TYPE){
                value = `${this.new_name}`;
            }
            else{
                value = `${this.new_name}_${this.type}`;
            }
            return value;
        }

        static fromString(fieldString){
            let dest_options = $("select[name$=-destination]").first().find("option");
            let dests = new Set(dest_options.toArray().map(x => x.value));
            if(dests.has(fieldString)){
                return new Field(fieldString, "", DEFAULT_TYPE);
            }
            let uscore = fieldString.lastIndexOf("_");
            let name;
            let type;
            if(uscore < 0){
                name = fieldString;
                type = DEFAULT_TYPE;
            }
            else{
                type = fieldString.slice(uscore + 1);
                name = fieldString.slice(0, uscore);
            }
            return new Field(FIELD_NEW, name, type);
        }

    }



    class Preset {
        constructor(name, fields, literals){
            if(typeof(name) === "string") {
                this.name = name;
                this.fields = fields;
                this.literals = literals;
            }
            else if(typeof(name) === "object"){
                $.extend(this, name);
            }
        }
    }

    class PresetManager {
        constructor(){
            this.rowmap = {};
            table.find('.field-row').each((i, el) =>{
                this.rowmap[$(el).data('fieldname')] = $(el);
            });
            this.suggested = this.getPresetFromTable();
            presetLoadSuggestedButton.click(() => this.applySuggested());
            presetLoadClearButton.click(() => this.clear());
            presetSaveButton.click(() => this.savePreset());
            this.loadPluginData();
        }

        /**
         * Applies the preset, and sets the input values in the field table by field name.
         *
         * @param preset {object} An object containing at least a property 'fields', which is an object with field names
         *                          as keys, and destination names as values. If the destination name is any available
         *                          value in the destination dropdown, then this value is used. Otherwise, the new_field
         *                          destination will be used, and the destination will be parsed as "{name}_{type}".
         */
        applyPreset(preset){
            let fields = preset.fields;
            this._applyFields(fields);

            let literals = preset.literals;
            this._applyLiterals(literals);
        }


        /**
         * Applies the suggested preset, which is equal to the initial values of the table.
         */
        applySuggested(){
            this.applyPreset(this.suggested);
        }

        /**
         * Clears the whole table, setting all destinations to "(don't use)".
         */
        clear(){
            let clear_fields = {};
            for(let key in this.suggested.fields){
                clear_fields[key] = FIELD_IGNORE;
            }
            this.applyPreset({ "fields": clear_fields });
        }

        /**
         * Remove the preset from the presets object and update the data on the server.
         * @param preset A preset object with at least a 'name' attribute.
         */
        removePreset(preset){
            this.plugin.presets = $.extend({}, this.plugin.presets);
            delete this.plugin.presets[preset.name];
            this.savePluginData();
        }

        /**
         * Add the current preset to the presets object and update the data on the server.
         */
        savePreset(){
            let preset = this.getPresetFromTable();
            preset.name = presetSaveNameField.val();
            if(preset.name.length == 0){
                presetSaveNameField.css("border-color", "tomato");
                return;
            }
            presetSaveNameField.css("border-color", "");
            this.plugin.presets = $.extend({}, this.plugin.presets);
            this.plugin.presets[preset.name] = preset;
            this.savePluginData();
        }

        /**
         * Save the plugin data on the server.
         * Sends a put request containing the current data.
         */
        savePluginData(){
            presetSaveButton.attr("disabled", "disabled");
            $.ajax({
                "url": url_plugin(window.project, this.plugin.id),
                "method": "PUT",
                "contentType": "application/json",
                "data": JSON.stringify(this.plugin),
                "dataType": "json",
                "headers": { "X-CSRFToken": csrf_middleware_token }
            }).done((data) =>{
                let collapseGroup = $("#input-group-save-collapse");
                if(collapseGroup.hasClass("in")){
                    collapseGroup.collapse("hide");
                    presetSaveButton.removeClass("btn-primary").addClass("btn-success");
                    setTimeout(() => presetSaveButton.removeClass("btn-success").addClass("btn-primary"), 350);
                }
                this.onLoadPluginData(data);
            }).fail(()=>{
                presetSaveButton.removeClass("btn-primary").addClass("btn-warning");
                this.loadPluginData();
            });
        }

        /**
         * Load the plugin data on the server.
         */
        loadPluginData(){
            $.getJSON(url_plugin_by_name(window.project, window.upload_plugin))
                .done((data) =>{
                    this.onLoadPluginData(data.results[0]);
                });
        }

        /**
         * Called after loadPluginData succeeds.
         */
        onLoadPluginData(data){
            this.plugin = data;
            $("#presets-divider").nextAll().remove();
            for(let preset in this.plugin.presets){
                this.addDropdownButton(new Preset(this.plugin.presets[preset]));
            }
            presetSaveButton.removeAttr("disabled");
        }


        addDropdownButton(preset){
            let presetName = $('<span>').text(preset.name + " ");
            let removeButton = $('<span class="glyphicon glyphicon-remove pull-right">')
                .css("margin-left", "-3em");
            let button = $(`<a href="#" class="preset-button">`)
                .append([presetName, removeButton]);
            let li = $("<li>").append(button);

            removeButton.hover(
                () =>{
                    removeButton.addClass("text-danger");
                },
                () =>{
                    removeButton.removeClass("text-danger");
                });
            button.click(() =>{
                this.applyPreset(preset);
            });
            removeButton.click(e =>{
                this.removePreset(preset);
                e.stopPropagation();
                e.preventDefault();
            });
            $("#presets-divider").after(li);
        }


        getPresetFromTable(name){
            let fields = {};
            let literals = {};
            table.find('.field-row').each((i, el) =>{
                let fieldmap = fields;
                let row = $(el);
                let key;
                let isLiteral = row.data("literal") !== undefined;
                if(isLiteral){
                    fieldmap = literals;
                    key = row.find("[name$=-label]").val();
                }
                else{
                    key = row.data('fieldname');
                }
                if(key.length === 0){
                    return;
                }
                let field = new Field();
                for(let preset_key of ["destination", "new_name", "type"]){
                    field[preset_key] = row.find(`[name$=-${preset_key}]`).val();
                }
                fieldmap[key] = field.toString();
            });
            return new Preset({ "name": name, "fields": fields, "literals": literals });
        }

        _applyFields(fields){
            $('[name$=-destination]').val(FIELD_IGNORE);
            for(let key in fields){
                let fieldSettings = Field.fromString(fields[key]);
                let row = $(this.rowmap[key]);
                if(row.length > 0){
                    for(let field_key in fieldSettings){
                        row.find(`[name$=-${field_key}]`).val(fieldSettings[field_key]).trigger("change");
                    }
                }
            }
        }

        _applyLiterals(literals){
            let firstLiteral = $('[data-literal]').first();
            firstLiteral.nextAll("[data-literal]").remove();
            firstLiteral.find("[name$=-label]").val("");
            firstLiteral.find("[name$=-destination]").val(FIELD_IGNORE).trigger("change");
            for(let key in literals){
                let last = $("[data-literal] [name$=-label]").last();
                last.val(key);
                expand();
                let fieldSettings = Field.fromString(literals[key]);
                let row = last.closest('.field-row');
                for(let field_key in fieldSettings){
                    row.find(`[name$=-${field_key}]`).val(fieldSettings[field_key]).trigger("change");
                }
            }
        }
    }

    function onDestinationSelect(){
        let destination = this.value;
        let row = $(this).closest("tr");
        let newPropertyFields = row.find(".new-property-fields");
        if(destination !== FIELD_NEW){
            newPropertyFields.hide();
            return;
        }
        newPropertyFields.show();
    }

    /**
     * Expand the table by 1 row. Duplicates the last row, and increments the TOTAL_FORMS of the formset
     * management form by 1.
     */
    function expand(){
        let literal = $("[data-literal] [name$=-label]").last();
        let row = literal.closest("tr");
        let id = +literal.attr("name").match(/form-(\d+)-label/)[1];
        let old_prefix = "form-" + id;
        let new_prefix = "form-" + (id + 1);
        let new_row = row.clone();
        new_row.html(new_row.html().replace(new RegExp(old_prefix, 'g'), new_prefix));
        row.after(new_row);
        new_row.find("input[name$=-label][type=text]").one("change", expand);
        new_row.find("select[name$=-destination]").change(onDestinationSelect);
        let total_field = $('input[name=form-TOTAL_FORMS]');
        total_field.val(+total_field.val() + 1)
    }


    let destinations = $("select[name$=-destination]");
    destinations.change(onDestinationSelect);
    destinations.each((i, destination) =>{
        onDestinationSelect.call(destination);
    });

    let last_literal = $("input[name$=-label][type=text]").last();
    last_literal.one("change", expand);

    let presetLoader = new PresetManager();
});
