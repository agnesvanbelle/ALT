from collections import defaultdict
import models_utils
from sets import Set
import os.path
import subprocess

class Cache(object):
    
    def __init__(self, e_LMdir, f_LMdir, probs_file, fSen, alpha=0.4, ngram_max_length = 3):
        #here we  load only what is needed for translating  fSen
        self.f_LMmodel = defaultdict(float) 
        self.e_LMmodel =  defaultdict(float)       
        self.TMmodel = dict()
        self.LWmodel = defualtdict(float)
        
        loadmodels(probs_file, fSen, e_LMdir) 

        self.alpha = alpha
        self.ngram_max_length = n_gram_max_length
        
    def loadmodels(probs_file, fSen, e_LMdir, f_LMdir):
        #load foreign LM
        self.f_LMmodel = loadf_LM(f_LMdir, fsen)
        
        e_words_toconsider = Set()
        
        ngrams = models_utils.get_ngrams(self.ngram_max_length)
        for ngram in ngrams:
            update_models_fPhrase(ngram, probs_file, e_words_toconsider, TMconsidered)
 
        #load eLM for all possible translations starting with the first word
        self.e_LMmodel = loade_LM(e_LMdir, list(e_words_toconsider))
        
    def update_models_fPhrase(fPhrase, probs_file, e_words_toconsider):      
        command = 'grep ^\"' + fPhrase + ' |||\"' + probs_file
        result = subprocess.call(command, shell=True)
        
        localTMmodel = dict()

        localLWmodel = defaultdict(float)
        
        #for all possible translations of fPhrase
        for line in result.split('\n'):
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


        #sort by value (prob) and add this phrase sub-table in memory
        sorted_TM = sorted(x.iteritems(), key=operator.itemgetter(1), reverse = True)
        self.TMmodel[fPhrase] = sorted_TM
            
        self.LWmodel.update(localLWmodel)    
    

    
    #words_list is all possible words that we might need the english LM prob for    
    def loade_LM(eLMdir, words_list):
        model = defaultdict(float)
        for word in words_list:
            model.update(loadLMfile(eLMdir, word))
        return model

    def loadf_LM(fLMdir, fsen):
        model = defaultdict(float)
        toload = Set()
        for word in fsen.split(' ')
            toload.add(word)
        for word in toLoad:
            model.update(loadLMfile(fLMdir, word))
        return model
            
    def loadLMfile(LMdir, word):
        model = defaultdict(float)
        path = LMdir+'/'+models_utils.java_string_hashcode(word)+'.lm'
        
        #check if file exists
        if not os.path.exists(path):
            return model
        
        f_in = open(path)
        for line in f_in:
            split = line.split('\t')
            ngram = split[0]
            prob = float(split[1].replace('\n','')
            #add it to the model
            model[ngram] = prob
        f_in.close()
        return model

    def TM(self, fPhrase):
        #empty list if phrase does not exist
        if fPhrase not in self.TMmodel:
            return []
        return self.TMmodel[fPhrase]   
        
  #      return [("to go", 0.32), ("avoiding to", 0.1), ("miss", 0.4)]

    def LMe(self, eSen):
        #if 
        return 0.1

    def LMf(self, fSen):
        return 0.1

    def LW(self, fPhrase, ePhrase):
        return 0.1


    
    #get stupid back off probability
    #model is the aggregated model loaded from the files. can be either e_LMmodel or f_LMmodel
    def stupidback_prob(ngram, model):
        if ngram in model:
            return model[ngram]
        split = ngram.split(' ')
        back_ngram = ''
        if len(split)==2:
            back_ngram = ngram[0]
        else if len(split) == 3:
            back_ngram = ngram[0] + ' ' + ngram[1]
        
        return alpha * stupidback_prob(back_ngram, model)
        
    