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
 * Module to ease the pain of merging and calulating date ranges.
 */

define(["jquery", "moment"], function($, moment){
    var QueryDates = {};

    $.extend(QueryDates, {
        /**
         * @param ranges array of objects with `start` and `end` milliseconds,
         *        possibly null if not defined.
         * @returns {start_date: ms, end_date: ms} if we can merge (intersection
         *          of dates found), else null.
         */
        merge: function(ranges){
            var start = null, end = null;

            if (ranges.length === 0){
                return { start_date: null, end_date: null };
            }

            // Sort based on start dates. Handles 'null' as null is smaller
            // than a positive integer.
            ranges.sort(function(a, b){
                return (a.start_date < b.start_date) ? -1 : 1;
            });

            // Determine largest 'start_date' and smallest 'end_date'
            $.each(ranges, function(_, range){
                if (range.start_date > start) start = range.start_date;
                if (end === null) end = range.end_date;
                if (range.end_date !== null && range.end_date < end){
                    end = range.end_date;
                }
            });

            // If start ends up being bigger than we have found no intersection
            if (end !== null && start > end){
                return null;
            }

            return {
                start_date: start,
                end_date: end
            }
        },

        /**
         *
         * @param start_date date in milliseconds
         * @param interval one of `day`, `week`, `month`, `quarter` or `year`
         * @return object with properties `start_date` and `end_date`,
         *         both milliseconds.
         */
        get_range: function(start_date, interval){
            var start, end;

            start = moment(start_date);
            end = start.clone().add(1, interval + "s");

            return {
                start_date: start.unix() * 1000,
                end_date: end.unix() * 1000
            }
        },

        /**
         * Get range of dates for current articlesets from form.
         *
         * @param form_element DOM element of selection form
         */
        get_default_range: function(form_element){
            var range = $("#dates", form_element).find(".input-daterange");

            return {
                start_date: moment(range.data("min")).unix() * 1000,
                end_date: moment(range.data("max")).add(1, "days").unix() * 1000
            }
        },

        /**
         * Get currently selected range in form
         * @param form object containing values of form
         * @return object with properties `start_date` and `end_date`,
         *         both milliseconds.
         */
        get_range_from_form: function(form){
            function d(date){ return moment(date, "DD-MM-YYYY").unix() * 1000; }

            if (form.datetype === "on"){
                return QueryDates.get_range(d(form.on_date), "day");
            }

            if (form.datetype === "after"){
                return {
                    start_date: d(form.start_date),
                    end_date: null
                }
            }

            if (form.datetype === "before"){
                return {
                    start_date: null,
                    end_date: d(form.end_date)
                }
            }

            if (form.datetype === "between"){
                return {
                    start_date: d(form.start_date),
                    end_date: moment(d(form.end_date))
                }
            }

            return QueryDates.get_default_range($("form"));
        }
    });

    return QueryDates;
});



