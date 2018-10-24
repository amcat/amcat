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

get_text = function(api_host, api_token, project, articlesets, query=NULL, ...) {
  conn = connect(api_host, api_token)
  if (is.null(query) || query == "") {
    amcat.articles(conn, project=project, articleset=articlesets, columns = c("title", "text"))
  } else {
    amcat.hits(conn, queries=query, project=project, sets = articlesets, col=c("title" ,"text"))
  }
}
