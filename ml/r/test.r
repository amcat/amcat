library(Hmisc)
library(reshape)
source("/home/wva/libpy/ml/r/ml.r")

testdata = read.table("/tmp/table.txt")
testdata$pred0cat <- testdata$pred0 %/% 100
testdata$confbin <- confbins(testdata$conf0)
testdata$correct <- testdata$actual == testdata$pred0

mean(testdata$correct)

testdata$n = 1

cast(testdata, confbin ~ pred0cat, mean, value="correct")

with(testdata, lm(correct ~ conf0))

head(testdata)

head(testdata[,-grep("pred[1-9]", names(testdata) )])

head(testdata[,-c("pred1")])

head(testdata) 

melt(testdata, id=c("unit", "context", "actual", "actualpos", "pred0","pred0cat"))

cast(testdata[,c("confbin","pred0cat", "unit")], pred0cat ~confbin, value="unit")

f <- function(x) {list(avg=mean(x), n=length(x))}

d <- with(testdata, summarize(cbind(conf0), llist(confbin, pred0cat), FUN=length))

reshape(d, timevar="pred0cat", idvar="confbin", direction="wide", v.names="x")

cast(d, . ~ .)

cast(d, conf ~ cat, sum)

summary(testdata)

head(testdata)

t <- testdata[,c("confbin","pred0cat", "unit")]
head(t)

cast(testdata[,c("confbin","pred0cat", "unit")], confbin ~ pred0cat, f, value="unit")
cast(testdata[,c("confbin","pred0cat", "unit")], pred0cat ~confbin , f, value="unit")

cast(testdata[,c("confbin","pred0cat", "unit")], pred0cat ~confbin, value="unit")
?subset

testdata$confbin

x <- c("a","b")

