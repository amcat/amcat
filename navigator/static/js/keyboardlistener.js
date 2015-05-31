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

    //Constants
    var SHIFT = 1
    var CTRL = 2;
    var ALT = 4;

    var DATA_ID = "__keyboardListener"
    /*
     * A key map that is used to instantiate the Keys object
     */
    var KEYCODES = {
        backspace: [8, "Backspace"],
        tab: [9, "Tab"],
        enter: [13, "\u23CE"],
        shift: [16, "Shift"],
        ctrl: [17, "Ctrl"],
        alt: [18, "Alt"],
        pauseBreak: [19, "Pause"],
        capsLock: [20, "Caps Lock"],
        escape: [27, "Escape"],
        spacebar: [32, "Spacebar"],

        pageUp: [33, "Page Up"],
        pageDown: [34, "Page Down"],
        end: [35, "End"],
        home: [36, "Home"],

        left: [37, "\u2190"],
        up: [38, "\u2191"],
        right: [39, "\u2192"],
        down: [40, "\u2193"],

        insert: [45, "Insert"],
        delete: [46, "Delete"],

        0: [48, "0"],
        1: [49, "1"],
        2: [50, "2"],
        3: [51, "3"],
        4: [52, "4"],
        5: [53, "5"],
        6: [54, "6"],
        7: [55, "7"],
        8: [56, "8"],
        9: [57, "9"],

        a: [65, "A"],
        b: [66, "B"],
        c: [67, "C"],
        d: [68, "D"],
        e: [69, "E"],
        f: [70, "F"],
        g: [71, "G"],
        h: [72, "H"],
        i: [73, "I"],
        j: [74, "J"],
        k: [75, "K"],
        l: [76, "L"],
        m: [77, "M"],
        n: [78, "N"],
        o: [79, "O"],
        p: [80, "P"],
        q: [81, "Q"],
        r: [82, "R"],
        s: [83, "S"],
        t: [84, "T"],
        u: [85, "U"],
        v: [86, "V"],
        w: [87, "W"],
        x: [88, "X"],
        y: [89, "Y"],
        z: [90, "Z"],

        num0: [96, "Numpad 0"],
        num1: [97, "Numpad 1"],
        num2: [98, "Numpad 2"],
        num3: [99, "Numpad 3"],
        num4: [100, "Numpad 4"],
        num5: [101, "Numpad 5"],
        num6: [102, "Numpad 6"],
        num7: [103, "Numpad 7"],
        num8: [104, "Numpad 8"],
        num9: [105, "Numpad 9"],

        multiply: [106, "Numpad *"],
        add: [107, "Numpad +"],
        subtract: [109, "Numpad -"],
        decimalPoint: [110, "Numpad ."],
        divide: [111, "Numpad /"],

        f1: [112, "F1"],
        f2: [113, "F2"],
        f3: [114, "F3"],
        f4: [115, "F4"],
        f5: [116, "F5"],
        f6: [117, "F6"],
        f7: [118, "F7"],
        f8: [119, "F8"],
        f9: [120, "F9"],
        f10: [121, "F10"],
        f11: [122, "F11"],
        f12: [123, "F12"],

        numLock: [144, "Num Lock"],
        scrollLock: [145, "Scroll Lock"],

        semicolon: [186, ";"],
        equalSign: [187, "="],
        comma: [188, ","],
        dash: [189, "-"],
        period: [190, "."],
        forwardSlash: [191, "/"],
        graveAccent: [192, "`"],
        openingBracket: [219, "["],
        backslash: [220, "\\"],
        closingBracket: [221, "]"],
        singleQuote: [222, "'"]
    };

    function instantiate(jqObject, options)
    {
        var listener = new KeyboardListener(jqObject, options);
        jqObject.data(DATA_ID, listener);
        return listener;
    }

    /**
     * Instantiates and binds a KeyboardListener object to the jQuery object(s), or returns the existing keylistener.
     *
     * @param {Object} [options] A collection of options. Ignored if the listener is already instantiated.
     * @param {boolean} options.useKeyUp Whether to use keyup instead of keydown.
     *
     * @returns {KeyboardListener} The KeyboardListener object.
     */
    $.fn.keyboardListener = function(options) {
        return this.map(function(idx, el){
            var obj = $(this);
            return obj.data(DATA_ID) || instantiate(obj, options);
        });
    };


    /** 
     * A KeyboardListener object
     * @class
     *
     * @param {JQuery} jqObject the jQuery `this` element(s).
     * @param {Object} options A collection of options.
     * @param {boolean} options.useKeyUp Whether to use keyup instead of keydown.
     */
    function KeyboardListener(jqObject, options) {

        this._bindingDescriptionMap = [];
        this._binds = [];
        this._jqObject = jqObject;
        this._bindKeyEventHandler(options ? options.useKeyUp : false);

    }

    /**
     * Binds a key binding to the keydown event.
     *
     * @param {Binding} binding The binding.
     */
    KeyboardListener.prototype.addBinding = function(binding) {
        this._addBinding(binding);
        this._onBindingsChanged();
    };


    /**
     * Binds a list of bindings to the keydown event.
     *
     * @param {Binding[]} bindings The bindings.
     */
    KeyboardListener.prototype.addBindings = function(bindings) {
        var self = this;
        bindings.forEach(function(binding) {
            self._addBinding(binding);
        });
        this._onBindingsChanged();
    };

    /**
     * Removes a key binding from the keydown event.
     *
     * @param {Binding} binding The binding.
     */   
    KeyboardListener.prototype.removeBinding = function(binding) {
        this._removeBinding(binding);
        this._onBindingsChanged();        
    }

    /**
     * Removes a list of key bindings from the keydown event.
     *
     * @param {Binding[]} bindings The bindings.
     */   
    KeyboardListener.prototype.removeBindings = function(bindings) {
        var self = this;
        bindings.forEach(function(binding){
            self._removeBinding(binding);
        });
        this._onBindingsChanged();        
    }


    KeyboardListener.prototype.getBindingsHelpTextHtml = function()
    {
        var dl = $('<dl>');
        for (var description in this._bindingDescriptionMap) {
            var keystrokes = this._bindingDescriptionMap[description].map(function(binding) {
                return binding.key.toHtml();
            });
            var keyText = keystrokes.join(", ");
            if(keyText.length === 0)
            {
                continue;
            }
            var dt = $('<dt>').text(description);
            var dd = $('<dd>').html(keyText);
            dl.append(dt, dd);
        }
        return dl;
    }

    /**
     * Binds a key binding to the keydown event.
     *
     * @param {Binding} binding The binding.
     */
    KeyboardListener.prototype._addBinding = function(binding) {
        var self = this;

        this._bindfn(binding.key, binding);
        if (binding.description === undefined) {
            return;
        }
        if (this._bindingDescriptionMap[binding.description] === undefined) {
            this._bindingDescriptionMap[binding.description] = [];
        }
        this._bindingDescriptionMap[binding.description].push(binding);
    };

    /**
     * Removes a key binding from the keydown event.
     *
     * @param {Binding} binding The binding.
     */   
    KeyboardListener.prototype._removeBinding = function(binding) {
        this._unbindfn(binding.key, binding);
        if (binding.description === undefined) {
            return;
        }
        var desc = this._bindingDescriptionMap[binding.description];
        var idx;
        while (idx = desc.indexOf(binding) >= 0) {
            desc[idx] = desc.pop();
        }
    };

    /**
     * Binds a handler to a keystroke.
     *
     * @param {KeyStroke|Key|string|number} key The key to bind the handler to. It should be either
     *  the name of the key in `Keys` as a string, a `KeyStroke` containing the key and optional modifiers,
     *  a `Key` object from `Keys`, or the raw `keyCode` as a number.
     * @param {Binding} binding The handler binding. The binding.handler function is called with the
     *  calling `Element` as the `this` object, the jQuery `KeyboardEvent` parameter, 
     *  and the the listener object itself as the second parameter.
     */
    KeyboardListener.prototype._bindfn = function(key, binding) {
        var keyCode = this._getKeyCode(key);
        if (!keyCode) {
            throw new Error("Invalid key: " + key);
        }
        this._binds[keyCode] = this._binds[keyCode] || [];
        this._binds[keyCode].push(binding);
    };


    /**
     * Removes a binding from a keystroke. If the same function is bound multiple
     *  times to the same key, all of these instances are removed.
     *
     * @param {KeyStroke|Key|string|number} key The key to remove the binding from. It should be either
     *  the name of the key in `Keys` as a string, a `KeyStroke` containing the key and optional modifiers,
     *  a `Key` object from `Keys`, or the raw `keyCode` as a number.
     * @param {function} binding The binding to be removed.
     */
    KeyboardListener.prototype._unbindfn = function(key, binding) {
        var keyCode = this._getKeyCode(key);
        if (!keyCode) {
            throw new Error("Invalid key: " + key);
        }
        if (this._binds[keyCode]) {
            var idx;
            while ((idx = this._binds[keyCode].indexOf(binding)) >= 0) {
                this._binds[keyCode][idx] = null;
            }
        }
    };


    /*
     * Binds the internal handler function to the appropriate keyboard event.
     */
    KeyboardListener.prototype._bindKeyEventHandler = function(keyup) {
        var self = this;
        var handler = function(e) {
            if(e.target.tagName === "INPUT"){
                return;
            }
            var mod = 0;

            //metaKey is the apple command key
            mod += e.ctrlKey || e.metaKey ? CTRL : 0;
            mod += e.altKey ? ALT : 0;
            mod += e.shiftKey ? SHIFT : 0;
            var keyCode = e.keyCode + (mod << 8);
            if (self._binds[keyCode]) {
                self._binds[keyCode].forEach(function(binding) {
                    if(!binding || typeof(binding.handler) !== "function")
                    {
                        return;
                    }
                    binding.handler.call(this, e, self);
                    if(binding.preventDefault){
                        e.preventDefault();
                    }
                });
            }
        };
        if (keyup) {
            this._jqObject.keyup(handler);
        } else {
            this._jqObject.keydown(handler);
        }
    };


    /**
     * Gets the keycode belonging to the key.
     *
     * @param {KeyStroke|Key|string|number} key The key to bind the handler to. It should be either
     *  the name of the key in `Keys` as a string, a `KeyStroke` containing the key and optional modifiers,
     *  a `Key` object from `Keys`, or the raw `keyCode` as a number.
     * @returns {number} The keyCode belonging to `key` or `key` itself if it is a valid code.
     *  `undefined` if `key` is not valid.
     */
    KeyboardListener.prototype._getKeyCode = function(key) {
        if (typeof key === "string") {
            var key = Keys[key];
            return key ? key.keyCode : undefined;
        }
        if (typeof key === "number") {
            return key % 1 === 0 ? key : undefined;
        }
        if (key instanceof Key) {
            return key.keyCode;
        }
        if (key instanceof KeyStroke) {
            var modifier = 0;
            if (key.modifiers) {
                modifier += key.modifiers.shift ? SHIFT : 0;
                modifier += key.modifiers.ctrl ? CTRL : 0;
                modifier += key.modifiers.alt ? ALT : 0;
            }
            if (key.key instanceof KeyStroke) {
                return undefined;
            }
            return this._getKeyCode(key.key) + (modifier << 8);
        }
        return undefined;
    };

    /**
     *  Is called when one or multiple bindings have been added or removed.
     */
    KeyboardListener.prototype._onBindingsChanged = function() { };

    function Key(keyCode, keyName, keyText) {
        Object.defineProperty(this, "keyCode", {
            value: keyCode
        });
        Object.defineProperty(this, "keyName", {
            value: keyName
        });
        Object.defineProperty(this, "keyText", {
            value: keyText
        });
    }

    Key.prototype.toHtml = function() {
        return $('<kbd>').text(this.keyText)[0].outerHTML;
    };


    /**
     * Static readonly mapping from key names to Key objects.
     */
    var Keys = new(function() {
        for (var k in KEYCODES) {
            Object.defineProperty(this, k, {
                value: new Key(KEYCODES[k][0], k, KEYCODES[k][1])
            });
        }
    })();

    /** 
     * A KeyStroke object represents either a single key, or a combination of a key with modifiers (ctrl, alt, shift).
     * @class
     *
     * @param {Key|string} key The key to bind the handler to. It should be either
     *  the name of the key in `Keys` as a string or a `Key` object from `Keys`.
     * @param {Object} [modifiers] An object with 3 optional booleans `ctrl`, `alt`, or `shift`, representing
     *  their respective modifiers.
     */
    function KeyStroke(key, modifiers) {
        Object.defineProperty(this, "key", {
            value: key instanceof Key ? key : Keys[key]
        });
        Object.defineProperty(this, "modifiers", {
            value: modifiers || {}
        });
    }

    /**
     * Adds ctrl to the modifiers
     * @returns {KeyStroke} self
     */
    KeyStroke.prototype.ctrl = function() {
        this.modifiers.ctrl = true;
        return this;
    };


    /**
     * Adds shift to the modifiers
     * @returns {KeyStroke} self
     */
    KeyStroke.prototype.shift = function() {
        this.modifiers.shift = true;
        return this;
    };

    /**
     * Adds alt to the modifiers
     * @returns {KeyStroke} self
     */
    KeyStroke.prototype.alt = function() {
        this.modifiers.alt = true;
        return this;
    };

    /**
     * Converts KeyStroke to readable HTML, wrapped in a `<kbd>` tag, following bootstrap style advice.
     * @returns {string} the HTML
     */
    KeyStroke.prototype.toHtml = function() {
        var text = this.key.toHtml();
        if (this.modifiers.shift) {
            text = Keys.shift.toHtml() + " + " + text;
        }
        if (this.modifiers.ctrl) {
            text = Keys.ctrl.toHtml() + " + " + text;
        }
        if (this.modifiers.alt) {
            text = Keys.alt.toHtml() + " + " + text;
        }
        return $('<kbd>').html(text)[0].outerHTML;
    };

    /** 
     * A Binding object represents either a single key, or a combination of a key with modifiers (ctrl, alt, shift).
     * @class
     *
     * @param {KeyStroke|Key|string} key The key or keystroke to bind the handler to. It should be either
     *  the name of the key in `Keys` as a string or a `Key` object from `Keys`.
     * @param {function} handler The event handler. The handler is called with the calling element as the `this` object.
     *  ,and the jQuery `KeyboardEvent` parameter.
     * @param {string} [description] The readable description, used to display the binding help text. 
     * @param {boolean} [dontPreventDefault] If this is set to true, the preventDefault function
     *  won't be called.
     */
    function Binding(key, handler, description, dontPreventDefault) {
        this.key = key instanceof KeyStroke ? key : new KeyStroke(key);
        this.handler = handler;
        this.description = description;
        this.preventDefault = !dontPreventDefault;
    }

    return {
        Binding: Binding,
        Keys: Keys,
        KeyStroke: KeyStroke,
        KeyboardListener: KeyboardListener
    };
});