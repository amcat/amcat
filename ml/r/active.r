report <- function(testdata, canddata) {
  testdata <- prepare(testdata)
  report <- createReport()
  report.accuracy(testdata, report)
  report.confidence(testdata, canddata, report)
  report.confusion(testdata, report)
  report
}

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

startPlot <- function(report, filename, label) {
  f <- sprintf("%s/%s.png", report$plotdir, filename)
  png(file=f)
  addResult(report, sprintf("file://%s", f), label)
}

prepare <- function(dm) {
  dm[dm$actualpos==9999,"actualpos"] <- NA
  dm["correct"] <- dm[,"actual"]==dm[,"pred1"]
  dm["actual.2"] <- dm[,"actual"] %/% 100
  dm["pred1.2"] <- dm[,"pred1"] %/% 100
  dm["pred2.2"] <- dm[,"pred2"] %/% 100
  dm["correct.2"] <- dm[,"actual.2"]==dm[,"pred1.2"]
  dm
}

report.accuracy <- function(testresults, report) {
  report$Accuracy <-
    data.frame(Accuracy=c(mean(testresults[,"correct"]), mean(testresults[,"correct.2"])),
               row.names=c("4-digit", "2-digit"))
                                
  addResult(report, "Accuracy","Overall Accuracy")

  Acc.4 <- tapply(testresults$correct, testresults$actual.2, mean)
  Acc.2 <- tapply(testresults$correct.2, testresults$actual.2, mean)
  N <- tapply(testresults$correct, testresults$actual.2, length)
  relN <- round(N / sum(N), 2)
  Residual <- round(resid(lm(Acc.4 ~ N)),2)
  by.class <- data.frame(Acc.2, Acc.4, N, relN, Residual)
  report$Accuracy.byclass <- by.class[order(-N),]
  addResult(report, "Accuracy.byclass", "Accuracies by 2-digit class")
  
  report$Correlation.n.acc <-
    data.frame(Correlation=c(cor(by.class$N, by.class$Acc.4), cor(by.class$N, by.class$Acc.2)),
               row.names=c("4-digit", "2-digit"))
  addResult(report, "Correlation.n.acc", "Overall correlation between supertopic N and accuracy")

  startPlot(report, "acc", "Accuracy on 2 and 4 digits")
  barplot(t(as.matrix(by.class[,c(1,2)])), beside=T)
  dev.off()
  
  startPlot(report, "acc4", "Accuracy on 4 digits")
  barplot(by.class$Acc.4)
  dev.off()  
}

report.confusion <- function(testresults, report) {
  report$confusion.2 <- table(testresults$actual.2, testresults$pred1.2)
  addResult(report, "confusion.2", "Confusion matrix for 2 digit")
  
  report$doubt.2 <- table(testresults$pred1.2, testresults$pred2.2)
  addResult(report, "doubt.2", "'Doubt' matrix for 2 digit")
}

report.confidence <- function(testresults, candidateresults, report) {
  
  NBINS=10
  conf = 0:(NBINS-1)/NBINS
  acc <- function(c) {mean(testresults[testresults$conf1>c &
                                       testresults$conf1<=c+(1/NBINS),"correct"])}
  maxlen <- function(vec) {max(sapply(conf, function(c) {sum(vec>c&vec<=c+(1/NBINS))}))}

  counts <- function(vec) {sapply(conf, function(c) {sum(vec>c&vec<=c+(1/NBINS))})}
  
  
  report$conf <-
    data.frame(Accuracy=sapply(conf, acc),
               NTest=counts(testresults$conf1),
               NCand=counts(candidateresults$conf1),
               row.names=conf)
  addResult(report, "conf", "Accuracy and test/candidate N by confidence bin")
  
  startPlot(report, "conf_acc_ntest", "Accuracy and test N by confidence bin")
  hist(testresults$conf1, NBINS)
  lines(conf+(.5/NBINS), sapply(conf, acc) * maxlen(testresults$conf1))
  dev.off()

  
  startPlot(report, "conf_acc_ncand", "Accuracy and candidate N by confidence bin")
  hist(candidateresults$conf1, NBINS)
  lines(conf+(.5/NBINS), sapply(conf, acc) * maxlen(candidateresults$conf1))
  dev.off()
}

go2 <- function() {
  x <- read.table("/home/wva/tmp/test.txt", header=T)
  y <- read.table("/home/wva/tmp/cands.txt", header=T)
  print(sample(x,y, 10))
  sample(x,y, 10000)
  #sample(x,y, 10000)
                 
}

getunits <- function(data, threshold, name="units", n=-1) {
  confs <- data[data$conf1 <= threshold, "conf1"]
  result <- data[data$conf1 <= threshold, "unit"]
  if (n != -1) {result <- result[1:n]; confs <- confs[1:n]} # assume order
  print(sprintf("Selected %s %s with confidence of %s - %s",
                length(result), name, min(confs), max(confs)))
  result
}

sample <- function(testresults, candidateresults, n) {
  candidateresults <- candidateresults[order(candidateresults$conf1),]
  threshold <- candidateresults[n, "conf1"]
  print(sprintf("Threshold for n=%s is confidence <= %s", n, threshold))
  cands <- getunits(candidateresults, threshold, "candidates", n=n)
  test <- getunits(testresults, threshold, "test")
  list(threshold, cands, test)
}
  
go3 <- function() {
  x <- read.table("/home/wva/tmp/test.txt", header=T)
  x <- prepare(x)
  report <- createReport()
  report.confusion(x, report)
}
