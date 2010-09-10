source("/home/wva/libpy/ml/r/ml.r")


test <- function() {
  predicted = read.table("/tmp/predicted.txt")
  testdata = read.table("/tmp/testdata.txt")
  predictreport(predicted, testdata, imagesdir="/tmp", dowrite=F)
  #testreport(testdata, imagesdir="/tmp", dowrite=F)
}

test()

