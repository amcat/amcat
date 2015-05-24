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

/**
 * This module should include all functionality for making API calls.
 */
define(["query/utils/poll", "query/utils/format"], function(poll){
    return function(project, sets){
        var base_url = "/api/v4/query";

        return {
            get_api_url: function(action){
                var query_api_url = "{base_url}/{action}?format=json&project={project}&sets={sets}";

                return query_api_url.format({
                    action: action,
                    base_url: base_url,
                    project: project,
                    sets: sets
                });
            }
        }
    };
});