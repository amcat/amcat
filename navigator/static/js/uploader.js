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
        console.log(this);
        let destination = this.value;
        let row = $(this).closest('tr');
        let newPropertyFields =  row.find('.new-property-fields');
        if(destination !== "new_field"){
            newPropertyFields.hide();
            return;
        }
        newPropertyFields.show();
    }

    let destinations = $('select[name$=-destination]');
    destinations.change(onDestinationSelect);
    destinations.each((i, destination)=>{
        onDestinationSelect.call(destination);
    });
});
