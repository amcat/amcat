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
 * This module should include all functionality for making API calls. It is more
 * or less the equivalent of amcatclient.py in javascript. Examples:
 *
 * <script>
 *     require("api", function(Api){
 *         var api = Api({
 *             username: "amcat",
 *             password: "amcat",
 *             authSuccess: function(){
 *                 alert("horaay!");
 *             }
 *        });
 *
 *        // Assuming authSuccess was executed
 *        api.search({
 *            project: 1,
 *            articlesets: [1, 2, 3],
 *            columns: ["text", "headline"],
 *            minimal: true,
 *            success: function(data){
 *                alert(data);
 *            }
 *        });
 *     });
 * </script>
 */
define(["jquery", "query/utils/poll", "query/utils/format"], function($, poll){
    var nop = function(){};

    return function(options){
        // Extend options with default options
        options = $.extend({
            host: "https://amcat.nl",
            api: "{host}/api/v4/{component}",
            username: null,
            password: null,
            token: null,
            csrf: null,

            // Request pages of N items
            pageSize: 200,

            // Throw an error if we exceed N pages (prevent accidental DOS-attack)
            maxPages: 10,

            // Call success callback after each page is fetched. If true, authSuccess
            // may take another argument 'lastPage', which indicates whether the last
            // page was reached.
            streamPages: false,

            authSuccess: nop,
            authError: nop,
            urls: {
                get_token: 'get_token',
                search: 'search'
            }
        }, options);

        var token = options.token;
        var host = options.host;

        function assert_token(){
            if (token === null){
                throw "No token stored. You need to authenticate first!";
            }
        }

        // Exposed user API
        var api = {
            /**
             * Get full url for a specific API resource
             * @param component: one of options.urls's attributes
             * @returns: url (string)
             */
            get_url: function(component){
                return options.api.format({host: options.host, component: component});
            },

            /**
             *
             * @param action
             * @returns: url (string)
             */
            get_action_url: function(action){

            },

            /**
             * Tries to authenticate with given username and password. If it succeeds,
             * the token is stored and options.authSuccess is called, if it fails
             * authError is called.
             */
            get_token: function(){
                var url = api.get_url(options.urls.get_token);

                $.ajax({
                    type: "POST",
                    url: url,
                    data: {
                        username: options.username,
                        password: options.password
                    },
                    headers: {
                        "X-CSRFTOKEN": options.csrf
                    },
                    success: function(data){
                        // I haz token!
                        token = data.token;
                        options.authSuccess();
                    },
                    error: options.authError
                });

                // (Hopefully) remove sensitive data from memory
                delete options.username;
                delete options.password;

                return api;
            },

            /**
             * Try to authenticate using given username/password/token. Throws if no
             * valid values are given.
             */
            authenticate: function(){
                // If token is set, we assume it is correct
                if (token !== null){
                    options.authSuccess();
                    return api;
                }

                // Ensure username / password is given
                if (options.username === null || options.password === null){
                    throw "No token, and no username/password pair supplied."
                }

                return api.get_token();
            }
        };

        return api.authenticate();
    }
});