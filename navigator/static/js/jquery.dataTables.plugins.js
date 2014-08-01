
/*
 * When listening to an onclick event, it is impossible to know whether
 * ctrl is pressed. This sets a global variable, which listens for ctrl
 * keypress events.
 */
var control = false;
$(document).keydown(function(e) {
  if (e.ctrlKey) control = true;
}).keyup(function(e){
    if (!shift) control = false;
});

var shift = false;
$(document).keydown(function(e) {
  if (e.shiftKey) shift = true;
}).keyup(function(){
    shift = false;
});


jQuery.fn.dataTableExt.oApi.fnSetFilteringDelay = function ( oSettings, iDelay ) {
    /*
     * Inputs:      object:oSettings - dataTables settings object - automatically given
     *              integer:iDelay - delay in milliseconds
     * Usage:       $('#example').dataTable().fnSetFilteringDelay(250);
     * Author:      Zygimantas Berziunas (www.zygimantas.com) and Allan Jardine
     * License:     GPL v2 or BSD 3 point style
     * Contact:     zygimantas.berziunas /AT\ hotmail.com
     */
    var
        _that = this,
        iDelay = (typeof iDelay == 'undefined') ? 250 : iDelay;
    
    this.each( function ( i ) {
        $.fn.dataTableExt.iApiIndex = i;
        var
            $this = this, 
            oTimerId = null, 
            sPreviousSearch = null,
            anControl = $( 'input', _that.fnSettings().aanFeatures.f );
        
            anControl.unbind( 'keyup' ).bind( 'keyup', function() {
            var $$this = $this;

            if (sPreviousSearch === null || sPreviousSearch != anControl.val()) {
                window.clearTimeout(oTimerId);
                sPreviousSearch = anControl.val();  
                oTimerId = window.setTimeout(function() {
                    $.fn.dataTableExt.iApiIndex = i;
                    _that.fnFilter( anControl.val() );
                }, iDelay);
            }
        });
        
        return this;
    } );
    return this;
};

jQuery.fn.dataTableExt.oApi.fnRowCheckbox = function(oSettings){
    oSettings.aoDrawCallback.push({
        "fn": function () {
            $('tbody > tr', oSettings.aanFeatures.t).each(function(i, row){
                // Add handler for clicking on checkbox
                $(row.firstChild).prepend(
                    $("<input type=checkbox class=row-checkbox>").click(function(event){
                        event.ctrlKey = true;
                        event.stopPropagation();
                        $(row).toggleClass("active");
                        _set_action_buttons($(oSettings.aanFeatures.t));
                    })
                ).click(function(event){
                    event.preventDefault();
                    event.stopPropagation();
                    $("input", event.currentTarget).click();
                });
            });
        }
    });
};

jQuery.fn.dataTableExt.oApi.fnTableActions = function(oSettings, actions){
    actions = actions.detach().show().addClass("DTTT");
    $(".actions", oSettings.nTableWrapper).append(actions);

    oSettings.aoDrawCallback.push({
        fn: function(){ $(".btn", actions).addClass("disabled"); }
    });

    // Logic for enabling / disabling buttons is managed in
    // AMCAT_DEFAULT_OPTS in amcat.datatables.js.
};

jQuery.fn.dataTableExt.oApi.fnSetRowlink = function(oSettings, sRowlink, sOpenIn){
    /*
     * Input:       string:sRowlink. URL to link to when a row is clicked,
     *              formatted like:
     *                > '/api/{column_name}/'
     *                > '/api/{id}'
     *
     * Usage:       $('#example').dataTable().fnSetRowlink('$sRowlink')
     * License:     GPL v2 or BSD 3 point style
     * Contact:     martijn.bastiaan /AT\ gmail.com
     */
    var self = this;
    var re, format;

    sOpenIn = (sOpenIn === undefined) ? "same" : sOpenIn;

    if (!sRowlink){
        throw "Error: sRowlink cannot be empty when calling fnSetRowlink()!"
    }

    re = /\{([^}]+)\}/g;
    format = function(s, args) {
      /* Python(ish) string formatting:
      * >>> format('{0}', ['zzz'])
      * "zzz"
      * >>> format('{x}', {x: 1})
      * "1"
      */
      return s.replace(re, function(_, match){ return args[match]; });
    }

    oSettings.aoDrawCallback.push({
       "fn"  : function(){
           $('tbody > tr', oSettings.aanFeatures.t).unbind('click').click(function(event){
              var cols={}, data, name, url;

              if (control||shift) return;

              data = self.fnGetData(event.currentTarget);
              if (typeof(data) != "object"){
                // mDatas not used
                for (var i=0; i < oSettings.aoColumns.length; i++){
                    name = oSettings.aoColumns[i].sName;
                    if (!name){ throw "Error: column `sName` should be set!" }
                    cols[name] = data[i];
                }
              } else {
                cols = data;
              }

              if(typeof sRowlink == 'function'){
                sRowlink($(event.currentTarget), cols);
              } else {
                  /* Find url and redirect! */
                  url = format(sRowlink, cols);

                  if (sOpenIn === "same"){
                      console.log(format('Redirecting to: {0}', [url]))
                      window.location = url;
                  } else if (sOpenIn === "new"){
                      window.open(url, '_blank');
                  }
              }
           })
           .css("cursor", "pointer");
       },
       "sName" : "fnSetRowlink"
    });

    return this;
}

/* Search highlighting */
jQuery.fn.dataTableExt.oApi.fnSearchHighlighting = function(oSettings) {
  // Initialize regex cache
  oSettings.oPreviousSearch.oSearchCaches = {};
  oSettings.fnRowCallback = function( nRow, aData, iDisplayIndex, iDisplayIndexFull) {
    // Initialize search string array
    var searchStrings = [];
    var oApi = this.oApi;
    var cache = oSettings.oPreviousSearch.oSearchCaches;

    // Global search string
    // If there is a global search string, add it to the search string array
    if (oSettings.oPreviousSearch.sSearch) {
      searchStrings.push(oSettings.oPreviousSearch.sSearch);
    }

    // Individual column search option object
    // If there are individual column search strings, add them to the search string array
    if ((oSettings.aoPreSearchCols) && (oSettings.aoPreSearchCols.length > 0)) {
      for (i in oSettings.aoPreSearchCols) {
        if (oSettings.aoPreSearchCols[i].sSearch) {
        searchStrings.push(oSettings.aoPreSearchCols[i].sSearch);
        }
      }
    }

    // Create the regex built from one or more search string and cache as necessary
    if (searchStrings.length > 0) {
      var sSregex = searchStrings.join("|");
      if (!cache[sSregex]) {
        // This regex will avoid in HTML matches
        console.log(sSregex);
        cache[sSregex] = new RegExp("("+sSregex+")(?!([^<]+)?>)", 'i');
      }
      var regex = cache[sSregex];
    }
    
    // Loop through the rows/fields for matches
    var data, j;
    $('td', nRow).each( function(i) {
      // Take into account that ColVis may be in use
      j = oApi._fnVisibleToColumnIndex( oSettings,i);
      data = aData[j];
      
      if (data == undefined){
        // Using DataProps
        data = aData[oSettings.aoColumns[j].mData];
      }

      // Only try to highlight if the cell is not empty or null
      if (data) {
        // If there is a search string try to match
        if ((typeof sSregex !== 'undefined') && (sSregex)) {
            this.innerHTML = data.toString().replace( regex, function(matched) {
            return "<span class='filterMatches'>"+matched+"</span>";
          });
        }
        // Otherwise reset to a clean string
        else {
          this.innerHTML = data;
        }
      }
    });
    return nRow;
  };
  return this;
}
