from collections import defaultdict
import models_utils 
from sets import Set
import os.path
import subprocess

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
        
        self.loadmodels(probs_file, fSen, e_LMdir, f_LMdir) 

        
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
        print fPhrase
        if '<s>' in fPhrase or '</s>' in fPhrase:
            e_words_toconsider.add('<s>')
            e_words_toconsider.add('</s>')
            return   
        command = 'grep ^\"' + fPhrase + ' |||\" ' + probs_file
        print fPhrase, command
        result = subprocess.check_output(command, shell=True)

        print result
        if result == 1:
            return
        localTMmodel = dict()

        localLWmodel = defaultdict(float)
        
        trans_num = 0
        #for all possible translations of fPhrase
        for line in result.split('\n'):
            #only consider the top 'topTrans' phrases
            if trans_num == self.topTrans:
                break
            split = line.split (' ||| ')
            if len(split) == 0: #shell response
                break
            ePhrase = split[1]
            e_first = ePhrase.split(' ')[0]
            e_words_toconsider.add(e_first)
            
            probs = split[2].split(' ')
            TMprob = probs[0]
            
            localTMmodel[ePhrase] = TMprob
            
            #add lexicalized weighting of this phrase pair in memory
            LWprob = probs[2]           
            localLWmodel[(fPhrase, ePhrase)] = LWprob
            trans_num += 1


        #sort by value (prob) and add this phrase sub-table in memory
        sorted_TM = sorted(x.iteritems(), key=operator.itemgetter(1), reverse = True)
        self.TMmodel[fPhrase] = sorted_TM
            
        self.LWmodel.update(localLWmodel)    
    

    
    #words_list is all possible words that we might need the english LM prob for    
    def loade_LM(self,eLMdir, words_list):
        print words_list
        model = defaultdict(float)
        for word in words_list:
            model.update(self.loadLMfile(eLMdir, word))
        print model
        return model

    def loadf_LM(self,fLMdir, fsen):
        model = defaultdict(float)
        toload = Set()
        for word in fsen.split(' '):
            toload.add(word)
        for word in toload:
            model.update(self.loadLMfile(fLMdir, word))
        return model
            
    def loadLMfile(self,LMdir, word):
        model = defaultdict(float)
        path = LMdir+'/'+str(models_utils.java_string_hashcode(word))+'.lm'
        
        #check if file exists
        if not os.path.exists(path):
            return model
        
        f_in = open(path)
        for line in f_in:
            split = line.split('\t')
            ngram = split[0]
            prob = float(split[1].replace('\n',''))
            #add it to the model
            model[ngram] = prob
        f_in.close()
        return model

    #get stupid back off probability
    #model is the aggregated model loaded from the files. can be either e_LMmodel or f_LMmodel
    def stupidback_prob(ngram, model, total_words_num):
        if ngram in model:
            return model[ngram]
        elif len(ngram.split(' ')) == 1:  #not in vocabulary
            return delta / delta*total_words_num
            
        split = ngram.split(' ')
        back_ngram = ''
        if len(split)==2:
            back_ngram = ngram[1]
        elif len(split) == 3:
            back_ngram = ngram[1] + ' ' + ngram[2]
        
        return alpha * stupidback_prob(back_ngram, model)


    def TM(self, fPhrase):
        #empty list if phrase does not exist
        if fPhrase not in self.TMmodel:
            return []
        return self.TMmodel[fPhrase]   
        
  #      return [("to go", 0.32), ("avoiding to", 0.1), ("miss", 0.4)]

    def LM(self, sen, LMmodel, lang_words_num):
        prob = 0
        split = sen.split(' ')
        
        #<s> first_word
        prob += stupidback_prob(split[0]+ ' ' + split[1], LMmodel, lang_words_num)
        
        #<s> first_word second_word
        for i in range(2, len(split)):
            prob += stupidback_prob(split[i-2]+ ' ' + split[i-1] + ' ' +split[i], LMmodel, lang_words_num)
        return prob

    def LMe(self, eSen):
        return LM(self, eSen, e_LMmodel, e_words_num)

    def LMf(self, fSen):
        return LM(self, fSen, f_LMmodel, f_words_num)

    def LW(self, fPhrase, ePhrase):

        return LWmodel[(fPhrase, ePhrase)]  
      
      
e_LMdir = '/Users/parismavromoustakos/Desktop/nikos/lm_en/en.lm'
f_LMdir = '/Users/parismavromoustakos/Desktop/nikos/lm_nl/nl.lm'
probs_file = '/Users/parismavromoustakos/Desktop/nikos/final_file.txt'
fSen = 'hello duisternis mijn oude vriend'
cache = Cache(e_LMdir, f_LMdir, probs_file, fSen) 

#cache.LMf()
