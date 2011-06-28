import subprocess, StringIO
import toolkit

#echo "he pays attention to his mother" | java -jar /home/amcat/resources/jars/BerkeleyParser.jar -gr /home/amcat/resources/jars/eng_sm6.gr | java -cp /home/amcat/resources/jars/stanford-parser-2010-07-06.jar edu.stanford.nlp.trees.EnglishGrammaticalStructure -treeFile -

PARSE = "/usr/bin/java -jar /home/amcat/resources/jars/BerkeleyParser.jar -gr /home/amcat/resources/jars/eng_sm6.gr"
TREE = "java -cp /home/amcat/resources/jars/stanford-parser-2010-07-06.jar edu.stanford.nlp.trees.EnglishGrammaticalStructure -treeFile -"

def parse(sentence):
    print toolkit.execute("%s | %s" % (PARSE, TREE), sentence)[0]
    
    


if __name__ == '__main__':
    parse("this is a test\nand this is another one")
    
