from collections import defaultdict
import math

def ngrams(input, n):
	input = input.split(' ')
	output = []
	for i in range(len(input)-n+1):
		output.append(input[i:i+n])
	return output

#return the list of possible ngrams of a phrase
def getngrams(input, n):
    input = '<s> ' + input.replace('\n','') + ' </s>'
    #print input
    l = []
    for i in range(1, n+1):
        l = l + [' '.join(x) for x in ngrams(input, i)]
    return l


def marg(history_ngram, counts):
    #c =0
    #for x in counts:
    #    if x == history_ngram:
    #        c += counts[x]
    #return c
    return counts[history_ngram]

def getLMprob(ngram, counts):
    split = ngram.split(' ')
    if len(split) == 1:
        return counts[split[0]] / float(len(counts))
    if len(split) == 2:
        return counts[split[0]+' '+split[1]] / float(marg(split[0], counts))
    if len(split) == 3:
        return counts[split[0]+' '+split[1]+' '+split[2]] / float(marg(split[0]+' '+split[1], counts))
        #p(c|ab) = p(abc) / p(ab)

def buildLM (path, outputpath):

    print 'Building Language model...'
    f_in  = open(path)
    f_out = open(outputpath, 'w')
    counts = defaultdict(lambda:0)
    for line in f_in:
        
        ngrams = getngrams(line.strip(), 3)
        for ngram in ngrams:
            #print ngram
            counts[ngram] += 1
    f_in.close()
    model = defaultdict(lambda:0)
    
    i = 0
    for ngram in counts:
        i += 1
        model[ngram] = getLMprob(ngram, counts)
        if i % 10000 == 0:
            print 'calculated LM for ' + str(i) + ' out of '+str(len(counts))+ ' ngrams'
    delim = ''    
        
    for key in sorted(model.iterkeys()):
    #for key in model.iterkeys():
        #print key, math.log(model[key])
        f_out.write(delim+key + "\t" + str(math.log(model[key])))
        delim = '\n'
#        print "%s: %s" % (key, model[key])
    f_in.close()
    f_out.close()
    print 'Done.'

#path = '/home/cmonz1/alt2013/dutch-english/clean/clean.en'
#path = '/Users/parismavromoustakos/Desktop/nikos/ALT/clean.en'
#outputpath = 'ALT/lm.en'
#path = '/home/cmonz1/alt2013/dutch-english/clean/clean.nl'
#outputpath = '/home/10406921/lm/clean.en.lm'
#buildLM(path, outputpath)

def java_string_hashcode(s):
    h = 0
    for c in s:
        h = (31 * h + ord(c)) & 0xFFFFFFFF
    return ((h + 0x80000000) & 0xFFFFFFFF) - 0x80000000


def splitLM(lmpath):
    f_in = open(lmpath)
    s = ''
    buf = ''
    for line in f_in:
        #print line
        ngram = line.split('\t')[0]
        start = ngram.split(' ')[0]#line[0:line.index(' ')]
        if start != s :
            if (s != ''):
                f_out = open(outputdir+'/'+str(java_string_hashcode(start))+'.lm', "w")
                f_out.write(buf[:-1]) #remove last '\n'
                f_out.close()
                buf = ''
            s = start
        buf += line
    f_in.close()


#lmpath = '/Users/parismavromoustakos/Desktop/nikos/lm_en/en.lm'
lmpath = '/Users/parismavromoustakos/Desktop/nikos/lm_nl/nl.lm'

#outputdir = '/Users/parismavromoustakos/Desktop/nikos/lm_en'
outputdir = '/Users/parismavromoustakos/Desktop/nikos/lm_nl'

#splitLM(lmpath)
