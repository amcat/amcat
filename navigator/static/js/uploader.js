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

    const url_plugin_by_name = (project, plugin_name) => `/api/v4/projects/${project}/upload_plugins/?name=${plugin_name}`;
    const url_plugin = (project, plugin_id) => `/api/v4/projects/${project}/upload_plugins/${plugin_id}/`;

    const FIELD_NEW = "new_field";
    const FIELD_IGNORE = "-";
    const table = $("#table-fieldmap");
    const rows = table.find('.field-row');


    class PresetLoader {
        constructor(){
            this.rowmap = {};
            rows.each((i, el) =>{
                this.rowmap[$(el).data('fieldname')] = $(el);
            });
            this.suggested = this.getPresetFromTable();
            $("#preset-load-suggested").click(() => this.applySuggested());
            $("#preset-load-clear").click(() => this.clear());
            $("#preset-save").click(() => this.savePreset());
            this.loadPluginData();
        }

        applyPreset(preset){
            let fields = preset.fields;
            for(let key in fields){
                let fieldSettings = this.fieldNameToSettings(fields[key]);
                let row = $(this.rowmap[key]);
                if(row.length > 0){
                    for(let field_key in fieldSettings){
                        row.find(`[name$=-${field_key}]`).val(fieldSettings[field_key]).trigger("change");
                    }
                }
            }
        }

        applySuggested(){
            this.applyPreset(this.suggested);
        }

        clear(){
            let clear_fields = {};
            for(let key in this.suggested.fields){
                clear_fields[key] = FIELD_IGNORE;
            }
            this.applyPreset({ "name": null, "fields": clear_fields });
        }

        removePreset(preset){
            this.plugin.presets = $.extend({}, this.plugin.presets);
            delete this.plugin.presets[preset.name];
            this.savePluginData();
        }

        savePreset(){
            let preset = this.getPresetFromTable();
            let nameField = $("#preset-save-name");
            preset.name = nameField.val();
            if(preset.name.length == 0){
                nameField.css("border-color", "tomato");
                return;
            }
            this.plugin.presets = $.extend({}, this.plugin.presets);
            this.plugin.presets[preset.name] = preset;
            this.savePluginData();
        }

        savePluginData(){
            $.ajax({
                "url": url_plugin(window.project, this.plugin.id),
                "method": "PUT",
                "contentType": "application/json",
                "data": JSON.stringify(this.plugin),
                "dataType": "json",
                "headers": { "X-CSRFToken": csrf_middleware_token }
            }).done((data) =>{
                $("#input-group-save-collapse").removeClass("in");
                this.onLoadPluginData(data);
            });
        }

        loadPluginData(){
            $.getJSON(url_plugin_by_name(window.project, window.upload_plugin))
                .done((data) =>{
                    this.onLoadPluginData(data.results[0]);
                });
        }

        onLoadPluginData(data){
            this.plugin = data;
            $("#presets-divider").nextAll().remove();
            for(let preset in this.plugin.presets){
                this.addDropdownButton(this.plugin.presets[preset]);
            }
        }

        addDropdownButton(preset){
            let li = $("<li>");
            let button = $('<a href="#">')
                .append($("<span>").text(preset.name + " "))
                .appendTo(li)
                .addClass("preset-button");
            let removeButton =
                $('<span class="glyphicon glyphicon-remove pull-right">')
                    .appendTo(button);
            removeButton.hover(
                () =>{
                    return removeButton.addClass("text-danger");
                },
                () =>{
                    return removeButton.removeClass("text-danger");
                })
                .css("margin-left", "-3em");
            button.click(() =>{
                this.applyPreset(preset);
            });
            removeButton.click(e =>{
                this.removePreset(preset);
                e.stopPropagation();
            });
            $("#presets-divider").after(li);
        }


        getPresetFromTable(name){
            let fields = {};
            rows.each((i, el) =>{
                let row = $(el);
                let key = row.data('fieldname');
                if(key === undefined){
                    return;
                }
                let fieldSettings = {};
                for(let preset_key of ["destination", "new_name", "type"]){
                    fieldSettings[preset_key] = row.find(`[name$=-${preset_key}]`).val();
                }
                fields[key] = this.fieldSettingsToName(fieldSettings);
            });
            return { "name": name, "fields": fields };
        }

        fieldNameToSettings(fieldName){
            let dest_options = $("select[name$=-destination]").first().find("option");
            let dests = new Set(dest_options.toArray().map(x => x.value));
            if(dests.has(fieldName)){
                return { "destination": fieldName, "new_name": "", "type": "default" };
            }
            let uscore = fieldName.lastIndexOf("_");
            let name = fieldName.slice(0, uscore);
            let type = fieldName.slice(uscore + 1);
            return { "destination": FIELD_NEW, "new_name": name, "type": type };
        }

        fieldSettingsToName(fieldSettings){
            let value = null;
            if(fieldSettings.destination === FIELD_NEW){
                value = `${fieldSettings.new_name}_${fieldSettings.type}`;
            }
            else{
                value = fieldSettings.destination;
            }
            return value;
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

    function expand(){
        let literal = $(this);
        let row = literal.closest("tr");
        let id = +literal.attr("name").match(/form-(\d+)-label/)[1];
        let old_prefix = "form-" + id;
        let new_prefix = "form-" + (id + 1);
        let new_row = row.clone();
        new_row.html(new_row.html().replace(new RegExp(old_prefix, 'g'), new_prefix));
        row.after(new_row);
        new_row.find("input[name$=-label][type=text]").one("change", expand);

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

    let presetLoader = new PresetLoader();
});
