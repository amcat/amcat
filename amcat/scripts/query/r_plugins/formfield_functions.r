local({r <- getOption("repos")
       r["CRAN"] <- "http://cran.r-project.org" 
       options(repos=r)
})

djangoFieldList <- function(fieldtype, ...){
  list(type=fieldtype, arguments=list(...))
}

#' Create a json string for django form fields
#'
#' Create the form fields to be used for R plugins in AmCAT.
#'
#' @param ... the field objects, created using the functions: BooleanField, IntegerField, etc. Note that the field objects have to be named!
#'
#' @return a json string
#' @export 
#'
#' @examples
#' djangoFormFields(field1=BooleanField(initial=F, required=F),
#'                  field2=IntegerField(initial=10, required=T))
djangoFormFields <- function(...){
  rjson::toJSON(list(...))
}

#' Create a Django Form Field
#'
#' Use to create field objects for R plugins in AmCAT. See djangoFormFields().
#' 
#' @export
BooleanField <- function(...) djangoFieldList('BooleanField', ...)

#' Create a Django Form Field
#'
#' Use to create field objects for R plugins in AmCAT. See djangoFormFields().
#'
#' @export
CharField <- function(...) djangoFieldList('CharField', ...)

#' Create a Django Form Field
#'
#' Use to create field objects for R plugins in AmCAT. See djangoFormFields().
#'
#' @export
IntegerField <- function(...) djangoFieldList('IntegerField', ...)

#' Create a Django Form Field
#'
#' Use to create field objects for R plugins in AmCAT. See djangoFormFields().
#'
#' @export
DecimalField <- function(...) djangoFieldList('DecimalField', ...)

#' Create a Django Form Field
#'
#' Use to create field objects for R plugins in AmCAT. See djangoFormFields().
#'
#' @param choices the options, should be a character vector or list(c(label, value), ...)
#' @export
ChoiceField <- function(choices, ...) {
  if (is.character(choices))  choices = lapply(choices, function(x) c(x,x))
  djangoFieldList('ChoiceField', choices=choices, ...)
}


connect = function(api_host, api_token, ...) {
  library(amcatr)
  amcat.connect(host=api_host, token = api_token)
}

get_text = function(api_host, api_token, project, articlesets, query=NULL, filters=NULL, ...) {
  conn = connect(api_host, api_token)

  # Convert filters from [{"key": key, "value": value}, ...] into {key: value, ...}
  if (is.null(filters)) {
    filters2 = NULL
  } else {
  print(paste("!!!", filters))
    filters2 = list()
    for (filter in filters) {
       filters2[[filter$field]] = filter$value
    }
  }

  args = list(conn=conn, project=project)
  if (is.null(query) || query == "") {
    func = amcat.articles 
    args$articleset = articlesets
    args$columns = c("title", "text")
    if (!is.null(filters2)) {
      args$filters = rjson::toJSON(filters2)
    }
  } else {
    func = amcat.hits
    args$sets = articlesets
    args$col= c("title", "text")
    args$queries = query
    args = c(args, filters2)
  }
  result = do.call(func, args)
  print(paste0("get_text(query=", query, ", filters=", rjson::toJSON(filters2), "): ", nrow(result), " results"))
  result
}
