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


/**/
define([], function() {
    /*
     * Given model data ( [{ id : 5, prop1 : "asd", .. }] ), create a mapping with
     * the prop as key, and the object as value.
     */
    function map_ids(model_data, prop) {
        prop = (prop === undefined) ? "id" : prop;
        const result = {};
        for(let obj of model_data){
            result[obj[prop]] = obj;
        }
        return result;
    }

    function resolve_id(obj, target_models, prop) {
        var val = obj[prop];
        obj[prop] = (val === null) ? null : target_models[val];
    }

    /*
     * Some model objects contain foreign keys which are represented by
     * and id. This function resolves those ids to real objects.
     *
     * @param models: model objects which contain a foreign key
     * @param target_models: model objects which are targeted by the FK
     * @param prop: foreign key property
     */
    function resolve_ids(models, target_models, prop) {
        for(let obj of Object.values(models)){
            resolve_id(obj, target_models, prop);
        }
    }


    return {map_ids, resolve_id, resolve_ids};
});