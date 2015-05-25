"use strict";
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
define(["amcat/jshashset", "amcat/jshashtable"], function(){
    var AGGR_HASH_FUCNTIONS = {
        "equals": function (a, b) {
            return (a.id === undefined) ? (a === b) : (a.id === b.id && a.label === b.label);
        },
        "hashCode": function (aggr) {
            return (aggr.id === undefined) ? aggr.toString() : (aggr.id + "_" + aggr.label);
        }
    };

    /**
     * Provides convience functions for aggregation-data returned by server
     * @param data returned by server (json)
     */
    var _Aggregation = function(data){
        //////////////////////
        // PUBLIC FUNCTIONS //
        //////////////////////
        this.transpose = function(){
            var aggr_dict = new Hashtable(AGGR_HASH_FUCNTIONS);

            var temp_column;
            this.aggr.each(function(row, row_data){
                row_data.each(function(column, article_count){
                    temp_column = aggr_dict.get(column);

                    if (temp_column === null){
                        aggr_dict.put(column, [[row, article_count]]);
                    } else {
                        temp_column.push([row, article_count]);
                    }
                });
            });

            var aggr_list = [];
            aggr_dict.each(function(k, v){ aggr_list.push([k, v]); });
            return _Aggregation.bind({})(aggr_list);
        };

        //////////////////////////////////////
        // PRIVATE INITIALISATION FUNCTIONS //
        //////////////////////////////////////
        this._getHashMap = function(){
            var aggr_dict = new Hashtable(AGGR_HASH_FUCNTIONS);

            $.map(data, (function(x_values){
                aggr_dict.put(x_values[0], new Hashtable(AGGR_HASH_FUCNTIONS));

                $.map(x_values[1], function(y_values){
                    aggr_dict.get(x_values[0]).put(y_values[0], y_values[1]);
                });
            }).bind(this));

            return aggr_dict;
        };

        this._getColumns = function(aggr){
            var columns = new HashSet(AGGR_HASH_FUCNTIONS);

            $.each(aggr.values(), function(_, y_values) {
                $.each(y_values.keys(), function(_, x_key) {
                    columns.add(x_key);
                });
            });

            return columns.values();
        };

        this._getColumnIndices = function(columns){
            var indices = new Hashtable(AGGR_HASH_FUCNTIONS);
            $.each(columns, indices.put);
            return indices;
        };

        ///////////////////////
        // PUBLIC PROPERTIES //
        ///////////////////////
        this.aggr = this._getHashMap();
        this.rows = this.aggr.keys();
        this.columns = this._getColumns(this.aggr);
        this.columnIndices = this._getColumnIndices(this.columns);

        ///////////////////////////////////////////
        // PUBLIC FUNCTIONS MAPPING TO HASHTABLE //
        ///////////////////////////////////////////
        this.get = this.aggr.get;
        this.size = this.aggr.size;


        return this;
    };

    return function(data){
        return _Aggregation.bind({})(data);
    }
});

