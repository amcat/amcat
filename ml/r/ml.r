library(plyr)
library(reshape)

DEFAULT.IMAGES = "/home/amcat/www/plain/test"

nfromtest <- function() {
  testdata = read.table("/tmp/table.txt")
  nfoldreport(testdata, dowrite=F)
}

percentages <- function(v) {v / sum(v)}

predictreport <- function(predicted, testdata=NULL, dowrite=T, imagesdir=DEFAULT.IMAGES) {
  if (dowrite) {
    write.table(predicted, "/tmp/predicted.txt")
    if (!is.null(testdata)) {write.table(testdata, "/tmp/testdata.txt")}
  }
  predicted <- prepare(predicted)
  if (!is.null(testdata)) testdata <- prepare(testdata, omit.missing.actual=T)
  list(
       "By confidence bin" =
         conftable(predicted, "confbin", testdata=testdata, includeconf=F),
       "By predicted category" =
         conftable(predicted, "pred0cat", testdata=testdata)
       )
}

confbins <- function(conf) {
  ((conf-0.00000001) %/% .05) * .05
}

testreport <- function(testdata, dowrite=T, imagesdir=DEFAULT.IMAGES) {
  d <- prepare(testdata, omit.missing.actual=T)
  if (dowrite) {write.table(testdata, "/tmp/table.txt")}

  d$een = 1
  overall <- acctable(d, "een")
  bycat <- acctable(d, "actualcat", order=T)
  conf <- acctable(d, "confbin")

  accplot = startPlot("acc", imagesdir)  
  prop = conf$n / sum(conf$n)
  max = max(c(prop, conf$acc, conf$report, conf$top5))
  max = ((max %/% 0.1) * 0.1) + 0.1
  x = barplot(prop, ylim=c(0,max), main="N and Accuracy by confidence", ylab="% of cases / Accuracy (%)", xlab="Confidence")
  lines(x, conf$acc)
  lines(x, conf$top5, col="red")
  lines(x, conf$report, col="blue")
  dev.off()
  
  d$confusion = sprintf("%s-%s", d$actual, d$pred0)
  t = table(d$confusion[!d$correct])
  t = t[order(-t)[1:min(10, length(t))]]
  confusion = data.frame( n=t)

  list(
       "Overall accuracy" = overall,
       "N and Accuracy by category" = bycat,
       "N and Accuracy by confidence bin" = conf,
       "Accuracy on 2 and 4 digits" = accplot,
       "Top-10 confused categories" = confusion
       )
}

startPlot <- function(filename, imagesdir=DEFAULT.IMAGES) {
  f <- sprintf("%s/%s.png", imagesdir, filename)
  url <- sprintf("file://%s", f)
  png(file=f)
  url
}

unfactor <- function(x) {as.integer(levels(x)[as.numeric(x)])}

prepare <- function(data, omit.missing.actual=F) {
  if (!is.numeric(data$actual)) {data$actual <- unfactor(data$actual)}
  if (!is.numeric(data$pred0)) {data$pred0 <- unfactor(data$pred0)}

  if (omit.missing.actual) {
    data <- data[!is.na(data$actual),]
  }
  data$correct <- data$actual == data$pred0
  data$top5 <- !is.na(data$actualpos) & (data$actualpos < 5)
  data$confbin <- confbins(data$conf0)

  data$actualcat <- data$actual %/% 100
  data$pred0cat <- data$pred0 %/% 100
  data$catcorrect <- data$actualcat == data$pred0cat  
  data
}


acctable <- function(data, split, order=F) {
  split = data[,split]
  result = data.frame(
    n = tapply(split, split, length),
    perc = percentages(tapply(split, split, length)),
    acc = tapply(data$correct, split, mean),              
    report = tapply(data$catcorrect, split, mean),
    top5 = tapply(data$top5, split, mean))
  if (order) result = result[order(-result$acc),]
  result
}

conftable <- function(data, split, testdata=NULL, includeconf=T) {
  dsplit = data[,split]
  result <- data.frame(
    n = tapply(dsplit, dsplit, length),
    perc = percentages(tapply(dsplit, dsplit, length))
  )
  if (includeconf) {
    result$conf = tapply(data$conf0, dsplit, mean)
  }

  if (!is.null(testdata)) {
    acc = acctable(testdata, split)
    names(acc) = paste("est.", names(acc))
    result = cbind(result, acc)
  }

  result
}


sample <- function(results, n=10) {
  indices = order(results$conf0)
  indices[1:min(length(results),n)]
  results[indices,"unit"]
}
