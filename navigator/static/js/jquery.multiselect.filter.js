/*
 * jQuery MultiSelect UI Widget Filtering Plugin 1.2
 * Copyright (c) 2011 Eric Hynds
 *
 * http://www.erichynds.com/jquery/jquery-ui-multiselect-widget/
 *
 * Depends:
 *   - jQuery UI MultiSelect widget
 *
 * Dual licensed under the MIT and GPL licenses:
 *   http://www.opensource.org/licenses/mit-license.php
 *   http://www.gnu.org/licenses/gpl.html
 *
 
 Slightly modified for AmCAT.
 Changes:
 * 'clear' button added
 * 'ok' button added for multiple select

 *    diff -r 357f018c2d3a navigator/static/js/jquery.multiselect.filter.js                                                                                                                      [2/136]
 *   --- a/navigator/static/js/jquery.multiselect.filter.js  Mon Aug 19 10:38:39 2013 +0200
 *   +++ b/navigator/static/js/jquery.multiselect.filter.js  Mon Aug 19 10:50:14 2013 +0200
 *   @@ -146,7 +146,7 @@
 *    
 *                                   this._trigger( "filter", e, $.map(cache, function(v,i){
 *                                           if( v.search(regex) !== -1 ){
 *   -                                               rows.eq(i).show();
 *   +                                               rows.eq(i+1).show();
 *                                                   return inputs.get(i);
 *                                           }
 *
 *    
 *
*/
(function($){
	var rEscape = /[\-\[\]{}()*+?.,\\^$|#\s]/g;
	
	$.widget("ech.multiselectfilter", {
		
		options: {
			label: "Filter:",
			width: null, /* override default width set in css file (px). null will inherit */
			placeholder: "Enter keywords"
		},
		
		_create: function(){
			var self = this,
				opts = this.options,
				instance = (this.instance = $(this.element).data("multiselect")),
				
				// store header; add filter class so the close/check all/uncheck all links can be positioned correctly
				header = (this.header = instance.menu.find(".ui-multiselect-header").addClass("ui-multiselect-hasfilter")),
				
				// wrapper elem
				wrapper = (this.wrapper = $('<div class="ui-multiselect-filter">'+(opts.label.length ? opts.label : '')+'<input placeholder="'+opts.placeholder+'" type="search"' + (/\d/.test(opts.width) ? 'style="width:'+opts.width+'px"' : '') + ' /> <span class="ui-multiselect-filter-clear">Clear</span></div>').prependTo( this.header ));

			// reference to the actual inputs
			this.inputs = instance.menu.find('input[type="checkbox"], input[type="radio"]');
			
            $('<div class="ui-multiselect-filter-msg"></div>').insertAfter(this.header);
            
			// build the input box
			this.input = wrapper
			.find("input")
			.bind({
				keydown: function( e ){
					// prevent the enter key from submitting the form / closing the widget
					if( e.which === 13 ){
						e.preventDefault();
					}
				},
				keyup: $.proxy(self._handler, self),
				click: $.proxy(self._handler, self)
			});
            
            // ADDED FOR AmCAT
            this.clearButton = wrapper.find('.ui-multiselect-filter-clear')
                                    //.button({icons:{primary:'ui-icon-circle-close'}, text:false})
                                    .css('cursor', 'pointer')
                                    .bind('click', function(){
                                        $(this).prev().val('');
                                        $('.ui-multiselect-filter-msg').empty();
                                        self.rows.show();
                                    });
            // ADDED FOR AmCAT
            if(this.instance.options.multiple === true){
                var footer = (this.footer = $('<div />'))
                    .addClass('ui-widget-header ui-corner-all ui-multiselect-header ui-helper-clearfix')
                    .css('margin-top','3px')
                    .html(
                        $('<button>OK</button>')
                        .button()
                        .click(function(){
                            console.log('close');
                            instance.close();
                            return false;
                        })
                    )
                    .appendTo( instance.menu );
			}
            
			// cache input values for searching
			this.updateCache();
			
			// rewrite internal _toggleChecked fn so that when checkAll/uncheckAll is fired,
			// only the currently filtered elements are checked
			instance._toggleChecked = function(flag, group){
				var $inputs = (group && group.length) ?
						group :
						this.labels.find('input'),
					
					_self = this,

					// do not include hidden elems if the menu isn't open.
					selector = self.instance._isOpen ?
						":disabled, :hidden" :
						":disabled";

				$inputs = $inputs.not( selector ).each(this._toggleCheckbox('checked', flag));
				
				// update text
				this.update();
				
				// figure out which option tags need to be selected
				var values = $inputs.map(function(){
					return this.value;
				}).get();
				
				// select option tags
				this.element
					.find('option')
					.filter(function(){
						if( !this.disabled && $.inArray(this.value, values) > -1 ){
							_self._toggleCheckbox('selected', flag).call( this );
						}
					});
			};
			
			// rebuild cache when multiselect is updated
			$(document).bind("multiselectrefresh", function(){
				self.updateCache();
				self._handler();
			});
		},
		
		// thx for the logic here ben alman
		_handler: function( e ){
			var term = $.trim( this.input[0].value.toLowerCase() ),
			
				// speed up lookups
				rows = this.rows, inputs = this.inputs, cache = this.cache;
			
			if( !term ){
				rows.show();
			} else {
				rows.hide();
				
				var regex = new RegExp(term.replace(rEscape, "\\$&"), 'gi');
				
				this._trigger( "filter", e, $.map(cache, function(v,i){
					if( v.search(regex) !== -1 ){
					        // if first row is 'None' dummy, skip it
					        rownr = (rows[0].innerText.indexOf("----") == 0)?i+1:i;
					        rows.eq(rownr).show();
						return inputs.get(i);
					}
					
					return null;
				}));
			}

			// show/hide optgroups
			this.instance.menu.find(".ui-multiselect-optgroup-label").each(function(){
				var $this = $(this);
				$this[ $this.nextUntil('.ui-multiselect-optgroup-label').filter(':visible').length ? 'show' : 'hide' ]();
			});
		},
		
		updateCache: function(){
			// each list item
			this.rows = this.instance.menu.find(".ui-multiselect-checkboxes li:not(.ui-multiselect-optgroup-label)");
			
			// cache
			this.cache = this.element.children().map(function(){
				var self = $(this);
				
				// account for optgroups
				if( this.tagName.toLowerCase() === "optgroup" ){
					self = self.children();
				}
				
				// see _create() in jquery.multiselect.js
				if( !self.val().length ){
					return null;
				}
				
				return self.map(function(){
					return this.innerHTML.toLowerCase();
				}).get();
			}).get();
		},
		
		widget: function(){
			return this.wrapper;
		},
		
		destroy: function(){
			$.Widget.prototype.destroy.call( this );
			this.input.val('').trigger("keyup");
			this.wrapper.remove();
		}
	});
})(jQuery);
