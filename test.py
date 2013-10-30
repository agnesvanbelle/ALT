from collections import defaultdict
import math

def ngrams(input, n):
	input = input.split(' ')
	output = []
	for i in range(len(input)-n+1):
		output.append(input[i:i+n])
	return output

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

def getLMprob(ngram, counts, vocab_size, delta):
    split = ngram.split(' ')
    
    
    if len(split) == 1:
        a = counts[split[0]]
        b = float(len(counts))
        #return counts[split[0]]  / float(len(counts))
    if len(split) == 2:
        a = counts[split[0]+' '+split[1]]
        b = float(marg(split[0], counts))
        #return counts[split[0]+' '+split[1]] / float(marg(split[0], counts))
    if len(split) == 3:
        a = counts[split[0]+' '+split[1]+' '+split[2]]
        b = float(marg(split[0]+' '+split[1], counts))
        #return counts[split[0]+' '+split[1]+' '+split[2]] / float(marg(split[0]+' '+split[1], counts))
    
    return (a + delta) / float(b + vocab_size*delta) 

def buildLM (path, outputpath,delta=0.0001):

    print 'Building Language model...'
    f_in  = open(path)
    f_out = open(outputpath, 'w')
    counts = defaultdict(lambda:0)
    vocabulary =set()
    for line in f_in:
        
        ngrams = getngrams(line.strip(), 3)
        for ngram in ngrams:
            #print ngram
            counts[ngram] += 1
            vocabulary.add(ngram.split(' ')[0])
    f_in.close()
    model = defaultdict(lambda:0)
    
    i = 0
    for ngram in counts:
        i += 1
        model[ngram] = getLMprob(ngram, counts, len(vocabulary), delta)
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
    print 'Vocabulary size: ', len(vocabulary)

#path = '/home/cmonz1/alt2013/dutch-english/clean/clean.en'
path = '/Users/parismavromoustakos/Desktop/nikos/clean.en'
outputpath = '../en.lm'
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

        ngram = line.split('\t')[0]
        start = ngram.split(' ')[0]#line[0:line.index(' ')]

        if start != s :
            if (s == ''):
                s = start
                #print s
                buf+=line
                continue
            #f_out = open(outputdir+'/'+str(java_string_hashcode(start))+'.lm', "w")
            if '/' in s:
                s = s.replace('/', '\\')
            f_out = open(outputdir+'/\"'+s+'\".lm', "w")
            f_out.write(buf[:-1]) #remove last '\n'
            f_out.close()

            buf = line
            s = start
        else:
            buf += line
        #
        #s = start
        #buf += line
    f_in.close()


lmpath = '/Users/parismavromoustakos/Desktop/nikos/en.lm'
#lmpath = '/Users/parismavromoustakos/Desktop/nikos/nl.lm'

outputdir = '/Users/parismavromoustakos/Desktop/nikos/lm_en'
#outputdir = '/Users/parismavromoustakos/Desktop/nikos/lm_nl'

splitLM(lmpath)
