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
 * Determines whether at least one item in `list` is true, which is
 * determined by `f`.
 *
 * @param f: function which takes one argument and returns a boolean
 * @param list: array / object to be iterated over
 */
function any(list, f){
    for (var i=0; i < list.length; i++){
        if (f(list[i])) return true;
    }
    return false;
}

/*
 * Returns true if all items in `list` are true when applied to `f`.
 *
 * @param f: function which takes one argument and returns a boolean
 * @param list: array / object to be iterated over
 */
function all(list, f){
    for (var i=0; i < list.length; i++){
        if (!f(list[i])) return false;
    }
    return true;
}

/*
 * Returns a list constructed from members of a list (the second argument)
 * fulfilling a condition given by the first argument.
 */
function filter(f, list){
    var _list = [];
    $.each(list, function(i, item){
        if (f(item)) _list.push(item);
    });
    return _list;
}

/*
 * Returns a list constructed by appling a function (the first argument) to
 * all items in a list passed as the second argument
 */
function map(f, list){
    _list = [];

    $.each(list, function(i, item){
        _list.push(f(item));
    });

    return _list;
}
