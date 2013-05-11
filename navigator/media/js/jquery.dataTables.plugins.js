
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
}

jQuery.fn.dataTableExt.oApi.fnSetRowlink = function(oSettings, sRowlink){
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
                  console.log(format('Redirecting to: {0}', [url]))

                  window.location = url;
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
