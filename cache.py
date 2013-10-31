from collections import defaultdict
import models_utils
from sets import Set
import os.path
import subprocess
import math
import operator

class Cache(object):

    def __init__(self, e_LMdir, f_LMdir, probs_file, fSen,  e_words_num=20910, f_words_num=34221, alpha=0.4, ngram_max_length = 3, topTrans = 20, delta = 0.0001):
        #here we  load only what is needed for translating  fSen
        self.f_LMmodel = defaultdict(float)
        self.e_LMmodel =  defaultdict(float)
        self.TMmodel = dict()
        self.LWmodel = defaultdict(float)
        self.topTrans = topTrans
        self.alpha = alpha
        self.ngram_max_length = ngram_max_length
        self.e_words_num = e_words_num
        self.f_words_num = f_words_num
        self.delta = delta

        self.loadmodels(probs_file, fSen, e_LMdir, f_LMdir)
        #print self.TMmodel
        #print self.LWmodel
        #print self.f_LMmodel

    def loadmodels(self,probs_file, fSen, e_LMdir, f_LMdir):
        #load foreign LM
        self.f_LMmodel = self.loadf_LM(f_LMdir, fSen)

        e_words_toconsider = Set()

        #get all possible ngrams of the foreign sentence
        ngrams = models_utils.getngrams(fSen, self.ngram_max_length)

        for ngram in ngrams:
            self.update_models_fPhrase(ngram, probs_file, e_words_toconsider)

        #load eLM for all possible translations starting with the first word
        self.e_LMmodel = self.loade_LM(e_LMdir, list(e_words_toconsider))

    def update_models_fPhrase(self,fPhrase, probs_file, e_words_toconsider):
        #print fPhrase
        if '<s>' in fPhrase or '</s>' in fPhrase:
            e_words_toconsider.add('<s>')
            e_words_toconsider.add('</s>')
            return
        command = 'grep ^\"' + fPhrase + ' |||\" ' + probs_file
        #print fPhrase, command
        try :
            result = subprocess.check_output(command, shell=True)
        except:
            #foreign phrase not in the phrase table
            return

        #print result
        if result == 1:
            return
        localTMmodel = dict()

        localLWmodel = defaultdict(float)

        trans_num = 0
        #for all possible translations of fPhrase
        for line in result.split('\n'):
            #only consider the top 'topTrans' phrases
            #if trans_num == self.topTrans:
            #    break
            #print len(result)
            split = line.split (' ||| ')
            #print split
            if len(split) == 1: #shell response
                continue

            ePhrase = split[1]

            ePhrase_split = ePhrase.split(' ')
            if len(ePhrase_split) > 3:
                continue
            e_first = ePhrase_split[0]

            e_words_toconsider.add(e_first)

            probs = split[2].split(' ')
            TMprob = float(probs[1])
            #print TMprob
            #print probs
            localTMmodel[ePhrase] = TMprob

            #add lexicalized weighting of this phrase pair in memory
            LWprob = float(probs[3])
            #print LWprob
            localLWmodel[(fPhrase, ePhrase)] = LWprob
            trans_num += 1

        #sort by value (prob) and add this phrase sub-table in memory
        sorted_TM = sorted(localTMmodel.iteritems(), key=operator.itemgetter(1), reverse = True)
        if len(sorted_TM) > self.topTrans:
            sorted_TM = sorted_TM[0:self.topTrans]
        top_translations = set()
        for (a,b) in sorted_TM:
            top_translations.add(a)
        #print sorted_TM, len(sorted_TM)
        self.TMmodel[fPhrase] = sorted_TM
       # print sorted_TM

        new_localLW = defaultdict(float)
        for (a,b) in localLWmodel:
            if b in top_translations:
               # print
                new_localLW[(a,b)] = localLWmodel[(a,b)]
        #print new_localLW
        #print

        self.LWmodel.update(new_localLW)
        #print self.LWmodel


    #words_list is all possible words that we might need the english LM prob for
    def loade_LM(self,eLMdir, words_list):
        #print
        #print words_list
        model = defaultdict(float)
        for word in words_list:
            model.update(self.loadLMfile(eLMdir, word))
        #print model
        return model

    def loadf_LM(self,fLMdir, fsen):
        model = defaultdict(float)
        toload = Set()
        for word in fsen.split(' '):
            toload.add(word)
        for word in toload:
            print word
            model.update(self.loadLMfile(fLMdir, word))
        #print model
        return model

    def loadLMfile(self,LMdir, word):
        model = defaultdict(float)

        #path = LMdir+'/'+str(models_utils.java_string_hashcode(word))+'.lm'
        word = word.replace('/', '\\')
        path = LMdir+'/\"'+word+'\".lm'

        #check if file exists
        if not os.path.exists(path):
            #print path, 'not exists'
            return model

        f_in = open(path)
        for line in f_in:
            split = line.split('\t')
            ngram = split[0]
            #if LMdir == '/Users/parismavromoustakos/Desktop/nikos/lm_nl/':
            #    print word, ngram
            prob = float(split[1].replace('\n',''))
            #add it to the model
            model[ngram] = prob
        f_in.close()
        return model

    #get stupid back off probability
    #model is the aggregated model loaded from the files. can be either e_LMmodel or f_LMmodel
    def stupidback_prob(self,ngram, model, total_words_num):
        print "ngram: %s" % ngram
        if ngram in model:
            print ngram , ' in vocabulary'
            return model[ngram]


        split = ngram.split(' ')
        back_ngram = ''
        #print split
        if len(split)==1:
            print '\t\t'+ngram + ' \tnot in vocabulary'
            return math.log(self.delta / (self.delta*total_words_num))

        if len(split)==2:
            back_ngram = split[1]
        elif len(split) == 3:
            back_ngram = split[1] + ' ' + split[2]

        return self.alpha * self.stupidback_prob(back_ngram, model, total_words_num)


    def TM(self, fPhrase):
        #empty list if phrase does not exist
        if fPhrase not in self.TMmodel:
            return []
        return self.TMmodel[fPhrase]


    def LM(self, sen, LMmodel, lang_words_num):
        return self.stupidback_prob(sen, LMmodel, lang_words_num)
        #print sen, '\n'
        #prob = 0
        #split = sen.split(' ')
        #print split

        #<s> first_word
        #print split[0]+ ' ' + split[1]
        #res = self.stupidback_prob(split[0]+ ' ' + split[1], LMmodel, lang_words_num)
        #print res
        #prob += res
        #print prob
        #<s> first_word second_word
        #for i in range(2, len(split)):
        #    res = self.stupidback_prob(split[i-2]+ ' ' + split[i-1] + ' ' +split[i], LMmodel, lang_words_num)
#            prob += res
#            print res, '\n'
#            print split[i-2]+ ' ' + split[i-1] + ' ' + split[i], prob

#        return prob

    def LMe(self, eSen):
        return self.LM(eSen, self.e_LMmodel, self.e_words_num)

    def LMf(self, fSen):
        return self.LM(fSen, self.f_LMmodel, self.f_words_num)

    def LW(self, fPhrase, ePhrase):
        return self.LWmodel[(fPhrase, ePhrase)]

"""
e_LMdir = '/home/10406921/en_lm/'
f_LMdir = '/home/10406921/nl_lm/'
probs_file = '/home/10363130/alt1/output_clean/final_file.txt'

fSen = 'duisternis mijn oude'
cache = Cache(e_LMdir, f_LMdir, probs_file, fSen)

#print cahe.
print "LMf: %s" % cache.LMf(fSen)

cache = Cache(e_LMdir, f_LMdir, probs_file, 'ik ben hier nu .')
print "TM: %s" % cache.TM('ik ben')
print "LW: %s" % cache.LW('ik ben', 'i am')

print "LMf(hier nu): %s" % cache.LMf('hier nu')
print "LMf(koe): %s" % cache.LMf('koe')

print "LMe(I am): %s" % cache.LMe('I am')
print "LMe(. </s>): %s" % cache.LMe('. </s>')
print "LMf(. </s>): %s" % cache.LMf('. </s>')
"""
