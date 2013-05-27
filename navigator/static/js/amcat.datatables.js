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

/*
 * This module contains tools to build datatables with very simple function
 * calls. It can figure out most of the needed information by just an api-
 * url.
 */

amcat = (amcat === undefined) ? {} : amcat;
amcat.datatables = {};

_TARGET_ERR = "You can't use number to target columns in columndefs, as " +
                "create_rest_table creates the table for you. Please use " +
                "strings which refer to mData.";

_SORTCOL = "iSortCol_";
_SORTDIR = "sSortDir_";
_DPROP = "mData_";

// Default options passed to datatables.
_AMCAT_DEFAULT_OPTS = {
    "bScrollInfinite": true,
    "bScrollCollapse": true,
    "sScrollY": "300px",
    "fnRowCallback" : function(nRow){
        amcat.datatables.truncate_row(nRow);
    },
    "bDeferRender": true,
    "bFilter" : false,
    "iDisplayLength" : 100,
    "bProcessing" : true
};

$.fn.dataTableExt.sErrMode = 'throw';


/*
 * Create a rest table based on given url. You can still pass options to
 * datatables by providing opts as a second argument.
 *
 * @param cont: element in which to render the table
 * @param rest_url: page to fetch results from (ex: /api/article/)
 * @param clb: function which will be called when dataTable() has been
 *             called. The first (and only) argument of it will be the
 *             objects which is returned by dataTable().
 *
 * @param name: name which is unique for this table.
 * @param opts: datatables options.
 *
 * NOTE: aaSorting accepts (only) column-names now. For example:
 *
 *  "aaSorting" : [["name", "desc"], ["id", "asc"]]
 */
amcat.datatables.create_rest_table = function(cont, rest_url, optional_args){
    var state = $.extend({
        cont : $(cont).get(0),
        rest_url : rest_url,
        name : rest_url,
        datatables_options : {},

        // Metadata contains the json returned by the initial
        // OPTIONS call to rest_url.
        metadata : null,

        // Contains metadata of all sorts of types
        metadatas : {
            //  type : {} mapping for example:
            //
            //  article : {
            //     "fields" : ....
            //  }
        },

        // Store fetched objects here
        objects : {
            // type : [] mapping. For example:
            //
            // article : [{
            //   id : 123
            // }, ..]
        },

        // Contains jQuery table element
        table : null,

        // Contains fnServerData callbacks. It is an
        // sEcho : function mapping.
        callbacks :  {}
    }, optional_args);


    // Force user to use certain options as we need them for our
    // REST API.
    $.extend(state.datatables_options, {
        "sAjaxSource": rest_url,
        "sAjaxDataProp" : "results",
        "fnServerData" : amcat.datatables.fnServerData.bind(state),
        "bServerSide" : true,
        "bStateSave" : true
    });

    // Add our default options
    $.extend(state.datatables_options, _AMCAT_DEFAULT_OPTS, {
        "sWidth" : "100%"
    });

    console.log("Fetching OPTIONS for table: ", state.name);

    $.ajax({
        dataType : "json",
        type : "OPTIONS",
        url : rest_url,
        success : amcat.datatables.fetched_initial_success.bind(state),
        error : amcat.datatables.fetched_initial_error.bind(state)
    });
}

/*
 * This function truncates all cells in the given row.
 */
amcat.datatables.truncate_row = function(row, limit){
    var txt, limit = limit || 30;

    $.each($("td", row), function(i, cell){
        txt = $(cell).text();

        if (txt.length > 30){
            $(cell).attr("title", txt);
            $(cell).text(txt.substring(0,30)+"...");
        }
    });

    return row;
};

/* 
 * Python(ish) string fomratting. Examples:
 *
 *  >>> format('{0}', ['zzz'])
 *  "zzz"
 *  >>> format('{x}', {x: 1})
 *  "1"
 *
 */
amcat.datatables.format = (function(){
    var re = /\{([^}]+)\}/g;

    return function(str, args){
        return str.replace(re, function(_, match){
            return args[match];
        });
    };
})();

/*
 * Replace, in given results, all ids with labels.
 */
amcat.datatables.put_labels = function(state, objects, fieldname){
    var labels = state.objects[fieldname];

    // Replace default properties with label properties. Append _id to
    // still keep id values.
    for (var i in objects){
        if (objects[i][fieldname] === null){
            // Skip null fields (field with no label)
            continue;
        };

        objects[i][fieldname] = amcat.datatables.format(
            state.metadatas[fieldname].label,
            labels[objects[i][fieldname]]
        );
    }
}

/*
 * Handles new incoming labels. It stores them in the state, and calls
 * the correct functions to update the existing data.
 */
amcat.datatables.load_labels_success = function(labels, textStatus, jqXHR){
    var label_objects = this.this.objects[this.fieldname];
    var objects = this.args[0].results;

    // Put all fetched objects in cache
    for (var i in labels.results){
        label_objects[labels.results[i].id] = labels.results[i];
    }

    if (amcat.datatables.fetch_needed_labels.bind(this.this)(this, true)){
        return;
    }

    // All labels loaded, render content.
    amcat.datatables.table_objects_received.apply(this.this, this.args);
};

/*
 * Return a boolean indicating if all needed metadatas
 * are present.
 */
amcat.datatables.metadatas_loaded = function(state){
    for (var fieldname in state.metadata.models){
        if (state.metadatas[fieldname] === undefined){
            return false;
        }
    }
    
    return true;
}

/*
 * Callback function for whenever an additional metadata call
 * succeeded. This function is bound to an object depicting call
 * state of table_objects_received().
 */
amcat.datatables.load_metadata_success = function(metadata, textStatus, jqXHR){
    this.this.metadatas[this.fieldname] = metadata;
    this.this.objects[this.fieldname] = [];

    if (!amcat.datatables.metadatas_loaded(this.this)){
        return;
    }

    amcat.datatables.table_objects_received.apply(this.this, this.args);
};

/*
 * Load all datatables necessary for rendering labels.
 */
amcat.datatables.load_metadatas = function(callback){
    var ctx;

    for (var fieldname in this.metadata.models){
        ctx = $.extend({}, callback, {
            fieldname : fieldname
        });

        $.ajax({
            dataType : "json",
            type : "OPTIONS",
            url : this.metadata.models[fieldname],
            success : amcat.datatables.load_metadata_success.bind(ctx),
            error : amcat.datatables.fetched_initial_error.bind(ctx)
        });
    }
};

/*
 * Returns an array containing all ids of the needed objects, which are in
 * turn needed to generate labels.
 *
 * @return: array with (or without!) labelobject ids.
 */ 
amcat.datatables.get_load_labels = function(fieldname, objects, label_objects){
    var res = [], lbl_obj_id;

    for (var i in objects){
        // Add fieldname_id property
        if(objects[i][fieldname + "_id"] === undefined){
            objects[i][fieldname + "_id"] = objects[i][fieldname]; 
        }

        lbl_obj_id = objects[i][fieldname + "_id"];
        if (label_objects[lbl_obj_id] === undefined){
            if (lbl_obj_id !== null && res.indexOf(lbl_obj_id) === -1){
                res.push(lbl_obj_id);
            }
        }
    }

    return res;
};

/*
 * Fetch labels if necessary. Returns true if loading labels was needed, false
 * if is was not.
 *
 * @param dummy: if true, AJAX calls will not be made (default: false)
 */
amcat.datatables.fetch_needed_labels = function(callback, dummy){
    var fetching = false;

    var needed_labels, ctx, url;
    for (var fieldname in this.metadata.models){
        needed_labels = amcat.datatables.get_load_labels(
            fieldname, callback.args[0].results,
            this.objects[fieldname]
        );

        if (needed_labels.length > 0){
            fetching = true;

            // We found missing labels. Check if this is a dummy call, and
            // if it is, return true.
            if (!!dummy) break;

            // Add fieldname to callback object
            ctx = $.extend({}, callback, {
                fieldname : fieldname
            });

            // Determine url by adding the correct filtering paramters
            url = this.metadata.models[fieldname];
            url += "?id=" + needed_labels.join("&id=");
            url += "&page_size=" + needed_labels.length;

            $.ajax({
                dataType : "json",
                type : "GET",
                url : url,
                success : amcat.datatables.load_labels_success.bind(ctx),
                error : amcat.datatables.fetched_initial_error.bind(ctx)
            });
        }
    };

    return fetching;
};

/*
 * Handles new objects which are received. It tries to determine if all
 * labels are already available. If they are, it calls the correct funtions
 * to update the data to include labels. If not, it tries to fetch them.
 */
amcat.datatables.table_objects_received = function(data, textStatus, jqXHR){
    var callback = {
        "args" : arguments,
        "this" : this,
    }

    // Convert to datatables requirements
    data.iDisplayStart = (data.page - 1) * data.per_page;
    data.iDisplayLength = data.per_page;
    data.iTotalDisplayRecords = data.total;
    data.iTotalRecords = data.total;

    // Store received data in callbacks to make sure it is accessible for
    // label functions
    this.callbacks[data.echo].objects = data.results;

    // Find out wether we need to fetch any metadatas
    if(!amcat.datatables.metadatas_loaded(this)){
        // If load_metadatas is finished, it should call this function
        // again with the same arguments / this-value as it is now.
        return amcat.datatables.load_metadatas.bind(this)(callback);
    };

    // Find out whether we need to fetch any labels.
    if (amcat.datatables.fetch_needed_labels.bind(this)(callback)){
        return;
    } else {
        // Render labels from cache
        for (var fieldname in this.metadata.models){
            amcat.datatables.put_labels(this, data.results, fieldname);
        }
    }

    this.callbacks[data.echo].fnCallback(data);
};

/*
 * This function takes an array of objects and iterates over all
 * these objects. It stops when it finds:
 *
 *  obj[sprop] == svalue
 *
 * and returns:
 *
 *  obj[rprop]
 */
amcat.datatables._search_oa_props = function(arr, svalue, sprop, rprop){
    // Revert to default values if necessary.
    sprop = sprop || "name";
    rprop = rprop || "value";

    for (var i in arr){
        if (arr[i][sprop] == svalue){
            return arr[i][rprop];
        }
    }

    return undefined;
};

/*
 * Based on given aoData, build a http query string which queries
 * the server and used correct ordering.
 */
amcat.datatables.get_order_by_query = function(aoData){
    var i = -1, col, dir, prop, res = [];

    while(++i !== -1){
        col = amcat.datatables._search_oa_props(aoData, _SORTCOL + i);
        dir = amcat.datatables._search_oa_props(aoData, _SORTDIR + i);
        prop = amcat.datatables._search_oa_props(aoData, _DPROP + col);

        if (dir === undefined | prop === undefined | col === undefined){
            break;
        }

        res.push(((dir == "desc") ? "-" : "") + prop);
    }

    return "order_by=" + res.join("&order_by=");
};

/*
 * This function overrides the default datatables function for retrieving
 * data. It translates requested paramaters to suitable ones for our REST
 * API. Furthermore, it selects amcat.datatables.table_objects_received as
 * callback function.
 */
amcat.datatables.fnServerData = function(sSource, aoData, fnCallback){
    var offset = amcat.datatables._search_oa_props(aoData, "iDisplayStart");
    var page_size = amcat.datatables._search_oa_props(aoData, "iDisplayLength");
    var search = amcat.datatables._search_oa_props(aoData, "sSearch");
    var echo = amcat.datatables._search_oa_props(aoData, "sEcho");

    var page = (offset / page_size) + 1;

    sSource += ((sSource.indexOf("?") !== -1) ? "&" : "?");
    sSource += "page=" + page + "&page_size=" + page_size;
    sSource += "&datatables_options=" + encodeURIComponent(JSON.stringify({
        sSearch : search,
        sEcho : echo
    }));

    // Add ordering
    sSource += "&" + amcat.datatables.get_order_by_query(aoData);

    this.callbacks[echo] = {};
    this.callbacks[echo].fnCallback= fnCallback;
    this.callbacks[echo].aoData = aoData;

    $.ajax({
        dataType : "json",
        type : "GET",
        url : sSource,
        success : amcat.datatables.table_objects_received.bind(this),
        error : amcat.datatables.fetched_initial_error.bind(this)
    });
};

/*
 * Build aoColumnDefs out of metadata. Refer to the datatables
 * documentation for more information. This currently renders the
 * properties aTargets, mData.
 */
amcat.datatables.gen_aoColumnDefs = function(metadata){
    var res = [], i = 0;

    for (var fieldname in metadata.fields){
        res.push({
            aTargets : [fieldname],
            mData : fieldname
            // TODO: Add sType
        });
        
        i++;
    }

    return res;
}

/*
 * Columns can either be defined in aoColumns or in
 * aoColumnDefs. Both need their own parsing. This function
 * parses them both according to
 *
 *  > http://datatables.net/usage/columns
 *
 * And returns an array of columndefs.
 */
amcat.datatables.get_columns = function(opts){
    var coldefs = {}, i = 0;

    // Process aoColumnDefs
    $.each(opts.aoColumnDefs, function(i, coldef){
        $.each(coldef.aTargets, function(i, target){
            if (typeof target == "number") throw _TARGET_ERR;

            coldefs[target] = coldefs[target] || {};
            $.extend(true, coldefs[target], coldef);
        });
    });

    // Reset aTargets
    $.each(coldefs, function(i, coldef){
        coldef.aTargets = [coldef.mData];
    });

    // Process aoColumns
    if (opts.aoColumns !== undefined){
        $.each(opts.aoColumns, function(colnr, coldef){
            if(coldef.mData === undefined || coldef.mData === null){
                throw _TARGET_ERR;
            }

            $.extend(true, coldefs[coldef.mData], coldef);
        });
    };

    // Convert to list
    var res = [], coldef = null;
    if (opts.aoColumns !== undefined){
        // Keep order of aoColumns (and ignore superfluous coldefs defined
        // in aoColumnDefs.
        for (var i in opts.aoColumns){
            coldef = coldefs[opts.aoColumns[i].mData];

            if (coldef === null || coldef === undefined){
                coldef = opts.aoColumns[i];
                coldef.aTargets = [coldef.mData];
            }

            res.push(coldef);
        }
    } else {
        // No aoColumns defined. Display columns in (semi)random fashion.
        for (var target in coldefs){
            res.push(coldefs[target]);
            delete coldefs[target].aTargets;
        }
    }

    return res;
}

/*
 * Create table header element (tr).
 */
amcat.datatables.create_table_header = function(opts){
    var tr = $("<tr>");

    $.each(opts.aoColumns, function(colnr, coldef){
        tr.append(
            $("<th>").text(coldef.mData)
        );
    });

    return tr;
};

/*
 * Create table element which can be used to initialize datatables.
 */
amcat.datatables.create_table_element = function(opts){
    return (
        $("<table>").attr("width", opts.sWidth)
        .addClass("display datatable").append(
            $("<thead>").append(
                amcat.datatables.create_table_header(opts)
            )
        ).append(
            $("<tbody>")
        )
    )
};

/*
 * This function is executed when the initial call to the api succeeds.
 */
amcat.datatables.fetched_initial_success = function(data, textStatus, jqXHR){
    this.metadata = data;

    // Do we need to manually calculate aoColumnDefs?
    if (this.datatables_options.aoColumnDefs === undefined){
        this.datatables_options.aoColumnDefs = [];
    }

    this.datatables_options.aoColumnDefs = amcat.datatables.gen_aoColumnDefs(data)
                                                .concat(this.datatables_options.aoColumnDefs);

    // Merge aoColumnDefs / aoColumns
    this.datatables_options.aoColumns = amcat.datatables.get_columns(this.datatables_options);
    delete this.datatables_options.aoColumnDefs;

    // Create table element and add it to the DOM
    var tbl = amcat.datatables.create_table_element(this.datatables_options);
    $(this.cont).append(tbl);
    this.table = $(this.cont.children[this.cont.children.length - 1]);
    this.table.attr("id", this.name);

    // Find out which columns to sort based on given aaSorting
    $.each(this.datatables_options.aaSorting, (function(i, order){
        $.each(this.datatables_options.aoColumns, function(columnr, column){
            // Replace human-readable name with columnr
            if(order[0] === column.mData){ order[0] = columnr; }
        });
    }).bind(this));

    // Call datatables
    console.log("Calling dataTable with options: ", this.datatables_options);
    tbl = this.table.dataTable(this.datatables_options);

    // Call callback funtion with our datatables object as its
    // argument.
    if (this.setup_callback !== undefined && this.setup_callback !== null){
        this.setup_callback(tbl);
    }
}

/*
 * This function is executed when the initial call to the api fails: it
 * notifies the user.
 *
 * TODO: Try again a few times before giving up.
 */
amcat.datatables.fetched_initial_error = function(jqXHR, textStatus, errorThrown){
    console.log(
        "Could not load table: " + this['name'] + 
        ". You can find debugging information in the console."
    );

    console.log([jqXHR, textStatus, errorThrown]);
}

