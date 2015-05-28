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

define(["jquery"], function($) {

    /**
     * Binds a KeyListener object to the jQuery object(s)
     *
     * @param {Object} [options] A collection of options.
     * @param {boolean} options.useKeyUp Whether to use keyup instead of keydown.
     * @param {Object.<string, function>} options.bindings
     *  A dictionary of bindings with the key as string as a key, and the handler as value.
     * @returns {KeyListener} The KeyListener object.
     */
    $.fn.keyListener = function(options) {
        var keyListener = new KeyListener(this);
        return keyListener;
    };

    var KeyListener = (function() {


        /*
         * @param {JQuery} jqObject the jQuery `this` element(s).
         * @param {Object} options A collection of options.
         * @param {Object.<string, function>} options.bindings
         *  A dictionary of bindings with the key as string as a key, and the handler as value.
         */
        var KeyListener = function(jqObject, options) {
            this._binds = [];
            this._jqObject = jqObject;
            this._bindKeyEventHandler(options ? options.keyup : false);
            if (options && options.bindings) {

                for (k in options) {
                    bind(k, options[k]);
                }

            }
        }


        /**
         * Binds a handler to a keystroke.
         *
         * @param {Key|string|number} key The key to bind the handler to. It should be either
         *  the name of the key in `$.keyListener.Keys` as a string, a Key object from `$.keyListener.Keys`,
         *  or the raw `keyCode` as a number.
         * @param {function} handler The handler function. The function is called with the
         *  calling `Element` as the `this` object, and the jQuery `KeyboardEvent` parameter.
         */
        KeyListener.prototype.bind = function(key, handler) {
            var keyCode = this._getKeyCode(key);
            if (!keyCode) {
                throw new Error("Invalid key: " + key);
            }
            this._binds[keyCode] = this._binds[keyCode] || [];
            this._binds[keyCode].push(handler);
        }


        /**
         * Removes a binding of a handler to a keystroke. If the same function is bound multiple
         *  times to the same key, all of these instances are removed.
         *
         * @param {Key|string|number} key The key to bind the handler to. It should be either
         *  the name of the key in `$.keyListener.Keys` as a string, a `Key` object from `$.keyListener.Keys`,
         *  or the raw `keyCode` as a number.
         * @param {function} handler The handler function to be removed.
         */
        KeyListener.prototype.unbind = function(key, handler) {
            var keyCode = this._getKeyCode(key);
            if (!keyCode) {
                throw new Error("Invalid key: " + key);
            }
            if (this._binds[keyCode]) {
                var idx;
                while ((idx = this._binds[keyCode].indexOf(handler)) >= 0) {
                    delete this._binds[keyCode][idx];
                }
            }
        }


        /**
         * Removes all bindings to a given key. If no key is given, all bindings are removed from all keys.
         *
         * @param {Key|string|number} [key] The key to bind the handler to. It should be either
         *  the name of the key in $.keyListener.Keys as a string, a Key object from $.keyListener.Keys,
         *  or the raw keyCode as a number.
         */
        KeyListener.prototype.unbindAll = function(key) {
            if (key === undefined) {
                this._binds = [];
                return;
            }
            var keyCode = this._getKeyCode(key);
            if (!keyCode) {
                throw new Error("Invalid key: " + key);
            }
            this._binds[keyCode] = [];
        }


        /*
         * Binds the internal handler function to the appropriate keyboard event.
         */
        KeyListener.prototype._bindKeyEventHandler = function(keyup) {
            var self = this;
            var handler = function() {
                if (self._binds[event.keyCode]) {
                    self._binds[event.keyCode].forEach(function(fn) {
                        fn.call(this, event);
                    });
                }
            };
            if (keyup) {
                this._jqObject.keyup(handler);
            } else {
                this._jqObject.keydown(handler);
            }
        }


        /*
         * Gets the keycode belonging to the key.
         *
         * @param {Key|string|number} [key] The key to bind the handler to. It should be either
         *  the name of the key in $.keyListener.Keys as a string, a Key object from $.keyListener.Keys,
         *  or the raw keyCode as a number.
         * @returns {number} The keyCode belonging to `key` or `key` itself if it is a valid code.
         *  `undefined` if `key` is not valid.
         */
        KeyListener.prototype._getKeyCode = function(key) {
            if (typeof key === "string") {
                var key = $.keyListener.Keys[key];
                return key ? key.keyCode : undefined;
            }
            if (typeof key === "number") {
                return key % 1 === 0 ? key : undefined;
            }
            if (key instanceof Key) {
                return key.keyCode;
            }
            return undefined;
        }


        return KeyListener;
    })();


    /*
     */
    var Key = function(keyCode, keyName) {
        Object.defineProperty(this, "keyCode", {
            value: keyCode
        });
        Object.defineProperty(this, "keyName", {
            value: keyName
        });
    };


    (function() {

        var _map = {
            Backspace: 8,
            Tab: 9,
            Enter: 13,
            Shift: 16,
            Ctrl: 17,
            Alt: 18,
            PauseBreak: 19,
            CapsLock: 20,
            Escape: 27,

            PageUp: 33,
            PageDown: 34,
            End: 35,
            Home: 36,

            Left: 37,
            Up: 38,
            Right: 39,
            Down: 40,

            Insert: 45,
            Delete: 46,

            Key0: 48,
            Key1: 49,
            Key2: 50,
            Key3: 51,
            Key4: 52,
            Key5: 53,
            Key6: 54,
            Key7: 55,
            Key8: 56,
            Key9: 57,

            A: 65,
            B: 66,
            C: 67,
            D: 68,
            E: 69,
            F: 70,
            G: 71,
            H: 72,
            I: 73,
            J: 74,
            K: 75,
            L: 76,
            M: 77,
            N: 78,
            O: 79,
            P: 80,
            Q: 81,
            R: 82,
            S: 83,
            T: 84,
            U: 85,
            V: 86,
            W: 87,
            X: 88,
            Y: 89,
            Z: 90,

            Num0: 96,
            Num1: 97,
            Num2: 98,
            Num3: 99,
            Num4: 100,
            Num5: 101,
            Num6: 102,
            Num7: 103,
            Num8: 104,
            Num9: 105,

            Multiply: 106,
            Add: 107,
            Subtract: 109,
            DecimalPoint: 110,
            Divide: 111,

            F1: 112,
            F2: 113,
            F3: 114,
            F4: 115,
            F5: 116,
            F6: 117,
            F7: 118,
            F8: 119,
            F9: 120,
            F10: 121,
            F11: 122,
            F12: 123,

            NumLock: 144,
            ScrollLock: 145,

            Semicolon: 186,
            EqualSign: 187,
            Comma: 188,
            Dash: 189,
            Period: 190,
            ForwardSlash: 191,
            GraveAccent: 192,
            OpeningBracket: 219,
            Backslash: 220,
            ClosingBracket: 221,
            SingleQuote: 222
        };
        $.keyListener = $.keyListener || {};
        /**
         * A mapping from key to keyCodes.
         */
        $.keyListener.Keys = new(function() {
            for (var k in _map) {
                Object.defineProperty(this, k, {
                    value: new Key(_map[k], k)
                });
            }
        })();
    })();
});