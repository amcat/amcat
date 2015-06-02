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


define(["jquery", "amcat/keyboardlistener"], function($, kl) {
    var DATA_ID = "__codebookKeyListener";

    function instantiate(jqObject, codebookEditor){
        var listener = new CodebookKeyListener(jqObject, codebookEditor);
        jqObject.data(DATA_ID, listener);
        return listener;
    }

    $.fn.codebookKeyListener = function(codebookEditor) {
        return this.map(function(idx, el){
            var obj = $(this);
            return obj.data(DATA_ID) || instantiate(obj, codebookEditor);
        });
    };


    /**
     *  The Codebook KeyboardListener
     *  @class
     *  @extends KeyboardListener
     */
    function CodebookKeyListener(jqObject, codebookEditor) {
        var self = this;
        kl.KeyboardListener.call(this, jqObject);
        this._codebookEditor = codebookEditor;
        this._navigationState = new NavigationState(codebookEditor.root);
        var bindings = this._getCodebookCommonBindings();
        bindings = bindings.concat(this._getCodebookDefaultBindings());
        this._renderCheatSheet();
        this.addBindings(bindings);
    }

    //Extend the KeyboardListener object
    CodebookKeyListener.prototype = Object.create(kl.KeyboardListener.prototype);
    CodebookKeyListener.prototype.constructor = CodebookKeyListener;

    /**
     * Bindings that stay the same in both modes.
     */
    CodebookKeyListener.prototype._getCodebookCommonBindings = function(){
        return this._commonBindings || (this._commonBindings = [
            new kl.Binding(new kl.KeyStroke(kl.Keys.s).ctrl(), this._onSave, "Save"),

            new kl.Binding(kl.Keys.up     , this._onUp       , "Navigate Up"),
            new kl.Binding(kl.Keys.down   , this._onDown     , "Navigate Down"),
            new kl.Binding(kl.Keys.right  , this._onExpand   , "Expand"),
            new kl.Binding(kl.Keys.left   , this._onCollapse , "Collapse"),
            new kl.Binding(kl.Keys.k      , this._onUp       , "Navigate Up"),
            new kl.Binding(kl.Keys.j      , this._onDown     , "Navigate Down"),
            new kl.Binding(kl.Keys.l      , this._onExpand   , "Expand"),
            new kl.Binding(kl.Keys.h      , this._onCollapse , "Collapse")
        ]);
    }

    /**
     * The default bindings for the codebook editor
     */
    CodebookKeyListener.prototype._getCodebookDefaultBindings = function() {
        return this._defaultBindings || (this._defaultBindings = [
            new kl.Binding(new kl.KeyStroke(kl.Keys.up  ).ctrl().shift(), this._onMoveCodeUp  , "Move code up"),
            new kl.Binding(new kl.KeyStroke(kl.Keys.down).ctrl().shift(), this._onMoveCodeDown, "Move code down"),     

            new kl.Binding(new kl.KeyStroke(kl.Keys.k).ctrl().shift(), this._onMoveCodeUp  , "Move code up"),
            new kl.Binding(new kl.KeyStroke(kl.Keys.j).ctrl().shift(), this._onMoveCodeDown, "Move code down"),    

            new kl.Binding(kl.Keys.insert , this._onInsert       , "New Item" ),
            new kl.Binding(kl.Keys.a      , this._onInsert       , "New Item" ),
            new kl.Binding(kl.Keys.enter  , this._onRename       , "Rename" ),
            new kl.Binding(kl.Keys.m      , this._onMoveCode     , "Move Code" ),
            new kl.Binding(kl.Keys.t      , this._onDisplayLabels, "Tags/Labels" )
        ]);
    };
     
    /**
     * The bindings for the code movement mode.
     */
    CodebookKeyListener.prototype._getCodebookMovingBindings = function() {
        return this._movingBindings || (this._movingBindings = [
            new kl.Binding(kl.Keys.enter  , this._onMoveCodeTo   , "Move Here" ),
            new kl.Binding(kl.Keys.m      , this._onMoveCodeTo   , "Move Here" ),
            new kl.Binding(kl.Keys.escape , this._onCancel       , "Cancel Current Action" )
        ]);
    };

    /**
     * Toggles between Moving bindings and default bindings depending on the 
     * state of the editor.
     */
    CodebookKeyListener.prototype.updateMovingBindings = function() {
        if (this._codebookEditor.moving) {
            this.addBindings(this._getCodebookMovingBindings());
            this.removeBindings(this._getCodebookDefaultBindings());
        } else {
            this.addBindings(this._getCodebookDefaultBindings());
            this.removeBindings(this._getCodebookMovingBindings());
        }
    };

    /**
     * Called from the editor when the browser focus has changed to another code.
     */
    CodebookKeyListener.prototype.focusChanged = function(self) {
        self._navigationState.active = this;
    }
    /**
     * Keydown handlers
     */
    CodebookKeyListener.prototype._onUp = function(e, self) {
        self._navigationState.toPreviousCode();
        self._scrollToActive();
    };

    CodebookKeyListener.prototype._onDown = function(e, self) {
        self._navigationState.toNextCode();
        self._scrollToActive();
    };

    CodebookKeyListener.prototype._onCollapse = function(e, self) {
        self._codebookEditor.collapse(self._navigationState.active.dom_element, "fast");
    };

    CodebookKeyListener.prototype._onExpand = function(e, self) {
        self._codebookEditor.expand(self._navigationState.active.dom_element, "fast");
    };

    CodebookKeyListener.prototype._onSave = function(e, self) {
        self._codebookEditor.btn_save_changes_clicked();
    };

    CodebookKeyListener.prototype._onInsert = function(e, self) {
        self._codebookEditor.create_child_clicked.call(self._navigationState.active);
        self._codebookEditor.expand(self._navigationState.active.dom_element, "fast");
    };

    CodebookKeyListener.prototype._onRename = function(e, self) {
        if (self._navigationState.active.read_only) {
            return;
        }
        var span = $("> .parts .lbl", self._navigationState.active.dom_element);
        var d = {
            code: self._navigationState.active,
            span: span,
            input: $("+ input", span)
        };
        self._codebookEditor.rename_clicked.call(d);
    };

    CodebookKeyListener.prototype._onMoveCodeUp = function(e, self) {
        self._codebookEditor.move_code(self._navigationState.active, -1);
        self._scrollToActive();

    };

    CodebookKeyListener.prototype._onMoveCodeDown = function(e, self) {
        self._codebookEditor.move_code(self._navigationState.active, 1);
        self._scrollToActive();
    };

    CodebookKeyListener.prototype._onMoveCodeTo = function(e, self) {
        self._codebookEditor.move_code_to(self._codebookEditor.movingCode, self._navigationState.active);
        self._scrollToActive();
    };

    CodebookKeyListener.prototype._onMoveCode= function(e, self) {
        self._codebookEditor.move_code_clicked.call(self._navigationState.active);
    };

    CodebookKeyListener.prototype._onCancel = function(e, self) {
        self._codebookEditor.cancel_move();
    };

    CodebookKeyListener.prototype._onDisplayLabels = function(e, self){
        self._codebookEditor.show_labels_clicked.call(self._navigationState.active);
    }

    /**
     * Scroll to the current active element
     */
    CodebookKeyListener.prototype._scrollToActive = function() {
        var clientRect = this._navigationState.active.dom_element.getBoundingClientRect();

        //scroll down if too high
        var bottom = window.innerHeight - (clientRect.top + 40);
        if (bottom < 0) {
            $(document.body).stop().animate({
                scrollTop: window.pageYOffset - 2 * bottom
            }, "fast");
            return;
        }

        // Scroll up if too low
        var top = clientRect.top - $('.navbar').height();
        if (top < 0) {
            $(document.body).stop().animate({
                scrollTop: window.pageYOffset + 2 * top
            }, "fast");
        }
    };

    /** 
     * Whether the event should not be triggered.
     * @override
     */
    CodebookKeyListener.prototype._shouldCancel = function(event){
        return event.target.tagName === "INPUT" || $(event.target).closest('.modal').length > 0;
    }
    /**
     * Called when bindings are added or removed
     * @override
     */
    CodebookKeyListener.prototype._onBindingsChanged = function(){
        this._cheatsheet.html($(this.getBindingsHelpTextHtml()).addClass('table'));
    }

    CodebookKeyListener.prototype._renderCheatSheet = function(){
        var button = $('<button>').addClass('btn btn-default pull-right')
            .append($("<span>").addClass("glyphicon glyphicon-info-sign"))
            .append(" Hotkeys");

        var wrapper = $('<div>').addClass('pull-right')
            .width(0) //width 0 so it doesn't interfere with the layout of the content
            .append(button)
            .append($('<div>').hide().addClass('pull-right').css('clear','right'))
            .insertAfter($('.btn-group',this._codebookEditor.root_el).first());

        button.click(function(){
            $('> div', wrapper).toggle("fast");
        });
        this._cheatsheet = $("> div", wrapper);
    }

    /**
     * The Navigation State, keeps track of the current node being navigated. 
     * @class
     * @param rootCode  The root code
     * @param [activeCode]  The initial active code, defaults to rootCode.
     */
    function NavigationState(rootCode, activeCode) {
        this.root = rootCode;
        this._active = activeCode || rootCode;
    }

    Object.defineProperty(NavigationState.prototype, "active", {
        get: function() {
            return this._active;
        },
        set: function(value) {
            this._active = value;
            var part = $('> .parts', this._active.dom_element)[0];
            if(part !== document.activeElement){
                $('> .parts', this._active.dom_element).focus();
            }
            
        },
        enumerable: true,
        configurable: true
    });

    /**
     * Move to the next visible code in the tree. The new active code is it's next visible sibling if it has one.
     * Otherwise, the tree is traversed upwards until an ancestor with a next visible sibling is reached.
     * This next sibling will be the new active ecode.
     */
    NavigationState.prototype.toNextCode = function() {
        var node = this.active;
        var lowestVisible = this.active;
        while (node !== this.root) {
            if (!node.dom_element.is_visible) {
                lowestVisible = node;
            }
            node = node.parent;
        }
        var visibleChildren = _filter_visible(lowestVisible.children);
        if (visibleChildren.length > 0) {
            this.active = visibleChildren[0];
            return;
        }
        var node = lowestVisible;
        while (node !== this.root) {
            if (node.parent) {
                var visibleSiblings = _filter_visible(node.parent.children);
                var nextIdx = visibleSiblings.indexOf(node) + 1;
                if (nextIdx < visibleSiblings.length) {
                    this.active = visibleSiblings[nextIdx];
                    return;
                }
            }
            node = node.parent;
        }
    };


    /**
     * Move to the previous code in the tree. The new active code is the last
     * visible successor of the previous sibling, or the nearest visible ancestor
     * of the current active code if it has no previous siblings.
     */
    NavigationState.prototype.toPreviousCode = function() {
        if (this.active !== this.root) {
            var visibleSiblings = _filter_visible(this.active.parent.children);
            var prevIdx = visibleSiblings.indexOf(this.active) - 1;
            if (prevIdx >= 0) {
                var node = visibleSiblings[prevIdx];
                var visibleChildren = _filter_visible(node.children);
                while (visibleChildren.length > 0) {
                    node = visibleChildren[visibleChildren.length - 1];
                    visibleChildren = _filter_visible(node.children);
                }
                this.active = node;
                return;
            }
            var node = this.active.parent;
            var lowestVisible = this.active.parent;
            while (node !== this.root) {
                if (!node.dom_element.is_visible) {
                    lowestVisible = node;
                }
                node = node.parent;
            }
            this.active = lowestVisible;
        }

    };


    function _filter_visible(array) {
        return array.filter(
            function(c) {
                return c.parent.dom_element.is_visible;
            });
    }
    return CodebookKeyListener;
});