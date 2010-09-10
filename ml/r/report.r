createReport <- function() {
  env <- new.env()
  env$reportvars = character(0)
  env$reportlabels = character(0)
  env
}

addResult <- function(report, varname, label) {
  i <- length(report$reportvars) + 1
  report$reportvars[i] <- varname
  report$reportlabels[i] <- label
  report$plotdir <- "/home/amcat/www/plain/test"
}






