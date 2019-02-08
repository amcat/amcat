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

define(["jquery"], ($) =>{
    "use strict";
    let exports = {};

    function getCell(table, i, j){
        let rows;
        if(table.find('tbody').length > 0){
            rows = table.find("tbody > tr");
        }
        else{
            rows = table.find("tr");
        }
        if(j >= rows) return $();
        let cols = $(rows[j]).find("td");
        if(i >= cols) return $();
        return $(cols[i]);
    }

    exports.expandTable = expandTable;
    function expandTable(form_table, N){
        let form_body = form_table.find('tbody');
        let rows = form_body.find(' > tr');
        if(N === undefined){
            N = rows.length + 1;
        }
        for(let n = rows.length; n < N; n++){
            let last = form_body.find(' > tr').last();
            let x = last.clone();
            x.html(x.html().replace(/form-\d+/g, "form-" + n));
            x.find("input").val("");
            last.after(x);
        }
        $('#id_form-TOTAL_FORMS').val(form_body.find(' > tr').length);
    }


    function insertIntoTable(data, form_table, target_input){
        let lines = data.split("\n").map(x => x.trim()).filter(x => x !== "");
        if(lines.length === 0 || lines.length === 1 && lines[0].split("\t").length <= 1){
            return false
        }
        let targetrow = $(target_input).closest("tr");
        let targetcol = $(target_input).closest("td");
        let currentRowIdx = targetrow.parent().children().index(targetrow);
        let startColIdx = targetrow.children().index(targetcol);
        expandTable(form_table, lines.length + currentRowIdx + 1);
        for(let line of lines){
            let colIdx = startColIdx;
            for(let cell of line.split("\t")){
                let c = getCell(form_table, colIdx, currentRowIdx);
                c.find("input").val(cell.trim());
                colIdx++;
            }
            currentRowIdx++;
        }
        return currentRowIdx;
    }

    exports.bindTablePasteEvent = bindTablePasteEvent;
    function bindTablePasteEvent(form_table){
        $(form_table)[0].addEventListener('paste', e =>{
            function dataCallback(data){
                let nInserted = insertIntoTable(data, form_table, e.target);
                $(form_table.find("tbody > tr").get(nInserted)).find('input').first().focus();
            }

            e.clipboardData.items[0].getAsString(dataCallback);

            // don't prevent default. If a table is pasted it will overwrite the pasted data, otherwise
            // it should behave like any other paste.
        });

    }

    return exports
});
