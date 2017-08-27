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

define(["jquery", "jquery-ui"], function($){

    let Widget = (id) => $(`
<div id="${id}" class="panel panel-primary sort-select-container">
<div class="panel-body">
<div class="row">
<div class="col-md-6">
    <div class="panel panel-primary">
        <div class="panel-heading">
        Selected
        </div>
        <ul class="list-group select-target selected">
        </ul>
    </div>
</div>
<div class="col-md-6">
    <div class="panel panel-default">
        <div class="panel-heading">
        Not selected
        </div>
        <ul class="list-group select-target non-selected">
        </ul>
    </div>
</div>
</div>
<small> Drag and drop to reorder, add, and remove elements. </small>
<br><small>Doubleclick to quick add.</small>
</div>
</div>`);

    let Item = (value, label) => $(`
<li id="sort-select-item-${value}" class="list-group-item sort-select-item" draggable="true" data-value="${value}">
    <span class="glyphicon glyphicon-menu-hamburger drag-handle"></span>
    <span class="remove glyphicon glyphicon-remove pull-right" style="margin-left:-1em; /*firefox workaround*/"></span>
    <span class="sort-select-label">${label}</span>
</li>`);


    class SortSelect {
        constructor(target){
            this.id = this.getRandomId();
            this.target = target;
            this.container = $("<div>");
            target.after(this.container);
            this.container.click(e =>{
                e.stopPropagation();
            });
            $(document).click(e =>{
                this.hide();
            });
            this.button = $("<button>")
                .addClass("btn btn-default")
                .click(e =>{
                    e.preventDefault();
                    e.stopPropagation();
                    this.toggle();
                });
            target.after(this.button);
            target.hide();
            this.hide();
            this.parseChoices(target);
            this.value = new Set(this.initial);
            this.update();
        }

        toggle(){
            this.container.toggle();
            this.button.toggleClass("active");
        }

        show(){
            this.container.show();
            this.button.addClass("active");
        }

        hide(){
            this.container.hide();
            this.button.removeClass("active");
        }

        remove(value){
            this.value.delete(value);
            this.update();
        }

        add(value){
            this.value.add(value);
            this.update();
        }

        update(){
            let val = Array.from(this.value);
            let labels = Array.from(this.selected()).map(x => x[1]);
            this.target.val(val);
            let opts = this.target.find("option");
            opts.sort((a, b) => val.indexOf(a.value) - val.indexOf(b.value)).appendTo(this.target);
            this.render();
            this.button.text(labels.length === 0 ? "(none selected)" : labels);
        }

        renderChoice(choice){
            let item = Item(choice[0], choice[1]);
            item.find(".remove").click(e => this.remove(choice[0]));
            item.dblclick(e => this.add(choice[0    ]));
            return item;
        }

        render(){
            let selected = Array.from(this.selected());
            let nonSelected = Array.from(this.nonSelected());
            selected = selected.map(choice => this.renderChoice(choice));
            nonSelected = nonSelected.map(choice => this.renderChoice(choice));
            let widget = Widget(this.id);
            let selectList = widget.find(".selected");
            let nonSelectList = widget.find(".non-selected");
            selectList.html(selected);
            nonSelectList.html(nonSelected);
            selectList.find(".remove").show();
            nonSelectList.find(".remove").hide();
            this.container.html(widget);
            let lists = $.merge($.merge($(), selectList), nonSelectList);
            lists.sortable({ cancel: ".empty", connectWith: lists });
            $(lists).on("sortupdate", (e, ui) =>{
                let values = selectList.find('.sort-select-item').map((i, el) => $(el).attr('data-value'));
                this.value = new Set(values.get());
                this.update();
            });
        }

        * selected(){
            for(let item of this.value){
                let label = this.choices.get(item);
                yield [item, label];
            }
        }

        * nonSelected(){
            for(let choice of this.choices){
                let item = choice[0];
                let label = choice[1];
                if(!this.value.has(item)){
                    yield [item, label];
                }
            }
        }

        parseChoices(input){
            let opt = input.find("option");
            let choices = opt.toArray().map(el => [el.value, el.text]);
            this.choices = new Map();
            for(let choice of choices){
                let item = choice[0];
                let label = choice[1];
                this.choices.set(item, label);
            }
            this.initial = new Set(input.val());
        }

        getRandomId(){
            let randomBytes = Array.from(crypto.getRandomValues(new Uint8Array(8)));
            let randomStr = randomBytes.map(x => (x < 16 ? "0" : "") + x.toString(16)).join("");
            return "sortselect-" + randomStr;
        }

        static getInstance(target){
            const self = $(target);
            const data_key = "__sort_select.instance";
            let instance = self.data(data_key);
            if(instance === undefined){
                instance = new SortSelect(self);
                self.data(data_key, instance);
            }
            return instance;
        }
    }

    $.fn.sortSelect = function(){
        return $(this).map((i, el) => SortSelect.getInstance(el));
    };

});
