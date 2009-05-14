def nicepass(alpha=6,numeric=2):
    """
    returns a human-readble password (say rol86din instead of 
    a difficult to remember K8Yn9muL ) 
    """
    import string
    import random
    vowels = "aoeui"
    consonants = list(set(string.lowercase) - set(vowels))
    digits = string.digits
    
    ####utility functions
    def a_part(slen):
        ret = ''
        for i in range(slen):			
            if i % 2 == 0:
                ret += random.choice(consonants)
            else:
                ret += random.choice(vowels)
        return ret
    
    def n_part(slen):
        ret = ''
        for i in range(slen):
            ret += random.choice(digits)
        return ret
        
    #### 	
    fpl = alpha / 2		
    if alpha % 2 :
        fpl = int(alpha/2) + 1 					
    lpl = alpha - fpl	
    
    start = a_part(fpl)
    mid = n_part(numeric)
    end = a_part(lpl)
    
    return "".join((start, mid, end))

if __name__ == "__main__":
    print nicepass(6, 2)
