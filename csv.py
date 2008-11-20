import toolkit

class CSVFile(object):

    def __init__(this, file_or_string, sep='\t', strip=True):
        this.strip = strip
        if toolkit.isString(file_or_string):
            this.file = iter(open(file_or_string))
        else:
            this.file = iter(file_or_string)
        
        this.sep = sep
        
        this.columns = this.file.next().strip().split(this.sep)
        this.coldict = {}
        for i, col in enumerate(this.columns):
            this.coldict[col] = i

    def __iter__(this):
        return this

    def next(this):
        txt = this.file.next()
        if this.strip: txt = txt.strip()
        elif txt[-1] == '\n': txt = txt[:-1]
        row = txt.split(this.sep)
        return Row(row, this)

class Row(dict):
    def __init__(this, data, csvfile):
        this.data = data
        this.csvfile = csvfile

    def get(this,col):
        if toolkit.isString(col):
            col = this.csvfile.coldict[col]
        try:
            return this.data[col]
        except:
            print this.data
            print col
            raise

    def __getattr__(this, col):
        return this.get(col)
    
    def __getitem__(this, col):
        return this.get(col)

    def asDict(this):
        ret = {}
        for key, index in this.csvfile.coldict.items():
            ret[key] = this.data[index]
        return ret

    def __iter__(this):
        return this.csvfile.columns.__iter__()
    def items(this):
        return zip(this.csvfile.columns, this.data)

if __name__ == '__main__':
    import sys
    f = CSVFile(sys.stdin)
    print f.columns
    print f.coldict
    for row in f:
        print row[3]
        print row['kop']
        print row.kop
        print row.asDict()
        print row.items()
        for key in row:
            print key, row[key]
        break

