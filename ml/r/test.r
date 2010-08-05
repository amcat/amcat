source("/home/wva/libpy/ml/r/ml.r")


test <- function() {
  testdata = read.table("/home/wva/table.txt")
  #predictreport(testdata, testdata, imagesdir="/tmp")
  testreport(testdata, imagesdir="/tmp")
}

test()

