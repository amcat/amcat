

file = open("sentiment-adj.txt")

while 1:
    line = file.readline()
    words = line.split("/")
    print words
    if not line:
        break
