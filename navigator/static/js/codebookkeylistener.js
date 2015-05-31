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



    $.fn.codebookKeyListener = function(codebookEditor) {
        var keyListener = this.data("_codebookKeyListener") || 
            new CodebookKeyListener(this, codebookEditor);
        this.data("_codebookKeyListener", keyListener);
        return keyListener;
    };

    function CodebookKeyListener(jqObject, codebookEditor) {

        kl.KeyboardListener.call(this, jqObject);

        this._codebookEditor = codebookEditor;
        this._navigationState = new NavigationState(codebookEditor.root);
        var bindings = this._getCodebookBindings();
        this.addBindings(bindings);
    }

    //Extend the KeyboardListener object
    CodebookKeyListener.prototype = Object.create(kl.KeyboardListener.prototype);
    CodebookKeyListener.prototype.constructor = CodebookKeyListener;

    CodebookKeyListener.prototype._getCodebookBindings = function() {
        return [
            new kl.Binding(new kl.KeyStroke(kl.Keys.s).ctrl(), this._onSave, "Save"),

            new kl.Binding(new kl.KeyStroke(kl.Keys.up  ).ctrl().shift(), this._onMoveUp  , "Move code up"),
            new kl.Binding(new kl.KeyStroke(kl.Keys.down).ctrl().shift(), this._onMoveDown, "Move code down"),     

            new kl.Binding(new kl.KeyStroke(kl.Keys.k).ctrl().shift(), this._onMoveUp  , "Move code up"),
            new kl.Binding(new kl.KeyStroke(kl.Keys.j).ctrl().shift(), this._onMoveDown, "Move code down"),    


            new kl.Binding(kl.Keys.up     , this._onUp       , "Navigate Up"),
            new kl.Binding(kl.Keys.down   , this._onDown     , "Navigate Down"),
            new kl.Binding(kl.Keys.tab    , this._onDown     , "Navigate Down"),
            new kl.Binding(kl.Keys.right  , this._onExpand   , "Expand"),
            new kl.Binding(kl.Keys.left   , this._onCollapse , "Collapse"),
            new kl.Binding(kl.Keys.k      , this._onUp       , "Navigate Up"),
            new kl.Binding(kl.Keys.j      , this._onDown     , "Navigate Down"),
            new kl.Binding(kl.Keys.l      , this._onExpand   , "Expand"),
            new kl.Binding(kl.Keys.h      , this._onCollapse , "Collapse"),
            new kl.Binding(kl.Keys.insert , this._onInsert   , "New Item" ),
            new kl.Binding(kl.Keys.enter  , this._onRename   , "Rename" ),
            new kl.Binding(kl.Keys.enter  , this._onMoveTo   , "Move Here" ),
            new kl.Binding(kl.Keys.m      , this._onMove     , "Move Code/Move Here" ),
            new kl.Binding(kl.Keys.delete , this._onDelete   , "Delete" )
        ];
    };


    /**
     * Keydown handlers
     */
    CodebookKeyListener.prototype._onUp = function(e, self) {
        self._navigationState.toPreviousCode();
        var clientRect = self._navigationState.active.dom_element.getBoundingClientRect();
        var top = clientRect.top - $('.navbar').height();
        if (top < 0) {
            $(document.body).stop().animate({
                scrollTop: window.pageYOffset + 2 * top
            }, "fast");
        }
    };

    CodebookKeyListener.prototype._onDown = function(e, self) {
        self._navigationState.toNextCode();
        var clientRect = self._navigationState.active.dom_element.getBoundingClientRect();
        var bottom = window.innerHeight - (clientRect.top + 40);
        if (bottom < 0) {
            $(document.body).stop().animate({
                scrollTop: window.pageYOffset - 2 * bottom
            }, "fast");
            
        }
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

    CodebookKeyListener.prototype._onDelete = function(e, self) {
        //Not implemented
        //TODO: Implement delete method in the codebook editor, 
        //      call from here
    };

    CodebookKeyListener.prototype._onMoveUp = function(e, self) {
        self._codebookEditor.move_code(self._navigationState.active, -1);
    };

    CodebookKeyListener.prototype._onMoveDown = function(e, self){
        self._codebookEditor.move_code(self._navigationState.active, 1);
    };

    CodebookKeyListener.prototype._onMoveTo = function(e, self){
        if(self._codebookEditor.moving)
        {
            self._codebookEditor.move_code_to(self._codebookEditor.movingCode, self._navigationState.active);
        }
    };

    CodebookKeyListener.prototype._onMove = function(e, self){
        if(!self._codebookEditor.moving)
        {
            self._codebookEditor.move_code_clicked.call(self._navigationState.active);
        }
        else
        {
            self._codebookEditor.move_code_to(self._codebookEditor.movingCode, self._navigationState.active);
        }
    };

    function NavigationState(rootCode) {
        this.root = rootCode;
        this._active = rootCode;
    }

    Object.defineProperty(NavigationState.prototype, "active", {
        get: function() {
            return this._active;
        },
        set: function(value) {
            //TODO: add an 'active' class
            $(this._active.dom_element).children(".parts").css("background-color", "");
            this._active = value;
            $(this._active.dom_element).children(".parts").css("background-color", "silver");
        },
        enumerable: true,
        configurable: true
    });

    NavigationState.prototype.toNextCode = function() {
        var visibleChildren = _filter_visible(this.active.children);
        if (visibleChildren.length > 0) {
            this.active = visibleChildren[0];
            return;
        }
        var node = this.active;
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
            this.active = this.active.parent;
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