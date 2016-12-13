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

    function onDestinationSelect(){
        let destination = this.value;
        let row = $(this).closest("tr");
        let newPropertyFields =  row.find(".new-property-fields");
        if(destination !== "new_field"){
            newPropertyFields.hide();
            return;
        }
        newPropertyFields.show();
    }

    function expand(){
        let literal=$(this);
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
    destinations.each((i, destination)=>{
        onDestinationSelect.call(destination);
    });

    let last_literal = $("input[name$=-label][type=text]").last();
    last_literal.one("change", expand);

});
