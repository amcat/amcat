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

$(function(){
    var self = this;

    self.input_changed = function(event){
        var file = event.target.files[0];
        var reader = new FileReader();
        
        if(file.name.match(/.csv$/)){
            reader.onload = self.csv_onload;
        } else {
            reader.onload = self.raw_onload;
        }

        reader.readAsText(file);
    }

    self.csv_onload = function(file){
        var result = "";
        $.each($.csv.toArrays(file.target.result), function(i, row){
            console.log(row);
            result += row[0];
            result += "\n";
        });
        $("#id_query").text(result);
    }

    self.raw_onload = function(file){
        $("#id_query").text(file.target.result);
    }


    $("#upload-query").change(self.input_changed);
});
