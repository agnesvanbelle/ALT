import sys
import os
import math
import cPickle as pickle
import gc
import itertools
import copy
from collections import defaultdict
import argparse
import heapq
import math
from operator import itemgetter
import copy

from pqdict import PQDict # see https://github.com/nvictus/priority-queue-dictionary
import pqdict
import utilities

import cache
from cache import Cache


# defines a sub-problem: holds the 3 properties according to which
# States can be recombined
class Subproblem(object):

  def __init__(self, translatedPositionsF=[], lastTranslatedPositionF=None, lastTwoWordsE=[]):

    self.translatedPositionsF = translatedPositionsF # coverage vector , foreign side
    self.lastTranslatedPositionF = lastTranslatedPositionF # last translated foreign word (or phrase?) position
    self.lastTwoWordsE = lastTwoWordsE # last 2-gram LM history = last two english words

    self.nrFWordsTranslated =  len(self.translatedPositionsF)


  def __str__(self):
     return "\n\tsubproblem: <%s,%s,%s>" % (self.translatedPositionsF, self.lastTranslatedPositionF, self.lastTwoWordsE)


  def __repr__(self):
    return self.__str__()


  def __eq__(self, other):
    if isinstance(other, Subproblem):
      return (self.translatedPositionsF == other.translatedPositionsF and
              self.lastTranslatedPositionF == other.lastTranslatedPositionF and
              self.lastTwoWordsE == other.lastTwoWordsE)

    return NotImplemented


  def __hash__(self):
    return hash((tuple(self.translatedPositionsF), self.lastTranslatedPositionF, tuple(self.lastTwoWordsE)),)


  def __ne__(self, other):
    result = self.__eq__(other)
    if result is NotImplemented:
      return result
    return not result



# holds all state (hypothesis) properties
# hold 4 state-specific properties as well as a Subproblem object with 3
# more properties
class State(object):

  def __init__(self, subproblem=None, translationCurrentPhraseE=None, prob=sys.maxint*(-1), backpointer=None, recombPointers=[], futureProb=0, fPhrase=""):

    self.subproblem = subproblem # instance of class Subproblem, containing 3 properties

    self.fPhrase = fPhrase
    self.translationCurrentPhraseE = translationCurrentPhraseE
    self.prob = prob #translation probability
    self.backpointer = backpointer # one backpointer to previous state
    self.recombPointers = recombPointers # "back"-pointers to recombined states

    # for pruning
    self.futureProb= futureProb
    self.totalProb = self.prob  + self.futureProb

    self.nrFWordsTranslated = self.subproblem.nrFWordsTranslated   # nr. of foreign words translated


  def addRecombPointers(self, listPointers):
    for pointer in listPointers :
      self.recombPointers.append((pointer, -(self.totalProb - pointer.totalProb)))


  # get the n best recombpointers, sorted, these are the recomb pointers
  # that have the smallest difference in probability with the current state
  def getNBestRecombPointers(self, n):
    return heapq.nsmallest(n, self.recombPointers, key=itemgetter(1))


  # get recomb pointers, sorted as to
  # having the smallest difference in probability with the current state
  def getRecombPointersSorted(self):
    return self.getNBestRecombPointers(len(self.recombPointers))


  # heapify by highest total prob
  def __lt__(self, other):
    return self.totalProb > other.totalProb


  def __str__(self):
     return "state: %.2f" % self.totalProb


  def __repr__(self):
    return self.__str__()



# container to hold States corresponding to a certain Subproblem
# used in a StackHeapDict,
# with Subproblem as the key, and this class as the value
class StatesSameSubproblem(object):

  def __init__(self, stateHeap=[] ):
    self.stateHeap = stateHeap
    heapq.heapify(self.stateHeap)


  # lowest cost of all the states it contains
  def calcTotalProb(self):
    return self.stateHeap[0].totalProb


  def __lt__(self, other):
    return self.calcTotalProb() > other.calcTotalProb()


  def __str__(self):
    return "\n\t\tstateHeap: %s (%.2f)" % (self.stateHeap, self.calcTotalProb())


  def __repr__(self):
    return self.__str__()


  # maintains heap invariant
  def addState(self, s):
    heapq.heappush(self.stateHeap, s)
    return self


# defines a stack dict using during decoding
# in class Stack
#
# basically, it's a heap-dict of type
# Subproblem --> StatesSameSubproblem
class StackHeapDict(pqdict.PQDict):

  def __init__(self, *args, **kwargs):
    super(StackHeapDict, self).__init__(*args, **kwargs)


  # maintains heap invariant
  # also b/c it calls StatesSameSubproblem.assState which does
  def addState(self, key, state):
    if key in self:
      self.updateitem(key, self[key].addState(state))
    else:
      sss  = StatesSameSubproblem([state])
      self.additem(key, sss)


  def __str__(self):
    s = ""
    s += "%d" % len(self)
    for key in self.keys():
      s += "\t%s --> %s\n" % (key, self[key])
    return "\n\t\tstackHeapDict:\n %s" % s

  def __repr__(self):
    return self.__str__()



class Stack(object):

  # static attributes
  beamThreshold = 0.1
  histogramPruneLimit = 100

  def __init__(self, nrFWordsTranslated=None, *args, **kwargs):

    self.nrFWordsTranslated = nrFWordsTranslated # not needed

    self.stackHeapDict = StackHeapDict(*args, **kwargs)
    self.finalStateList = None


  def __str__(self):
    if self.stackHeapDict != None:
      return self.stackHeapDict.__str__()
    else :
      return "finalStateList:\n\t%s" %self.finalStateList


  def __repr__(self):
    return self.__str__()


  def bestScore(self):
    if self.stackHeapDict != None and len(self.stackHeapDict) > 0:
      return self.stackHeapDict.peek()[1].calcTotalProb()
    elif self.finalStateList != None and len(self.finalStateList) > 0:
      return self.finalStateList[0].totalProb
    else:
      return sys.maxint*(-1)


  def addState(self, subproblem, state):
    self.stackHeapDict.addState(subproblem, state)


  def postProcess(self, bestScore=None):

    if bestScore == None:
      bestScore = self.bestScore()

    (finalStateList, finalStateDict) = self.thresholdPruneAndRecombine(bestScore)
    self.histogramPrune(finalStateList, finalStateDict)

    self.stackHeapDict = None


  # prune hypotheses outside of the beam of the highest-scoring one
  #
  # precondition: self.stackHeapDict is filled, and self.finalStateList is not yet
  # postcondition: self.finalStateList exists
  def thresholdPruneAndRecombine(self, bestScore):

    # dive into remaining subproblems (iterate over keys)
    # regular iteration, no prescribed order
    self.nrStatesTotal = 0
    finalStateList = []
    finalStateDict = {}

    #iterate from high to low scoring states
    while True and len(self.stackHeapDict) > 0:
      (subproblem, statesSameSubproblem) = self.stackHeapDict.popitem()

      # if the highest scoring state is lower than theshold
      if statesSameSubproblem.calcTotalProb < bestScore-Stack.beamThreshold:
        print "breaking"
        break

      print "Examining states of %s" % ((subproblem, statesSameSubproblem),)

      state = heapq.heappop(statesSameSubproblem.stateHeap) # return state with largest prob, remove from heap

      lowerStates = []
      while True and len(statesSameSubproblem.stateHeap) > 0:
        lowerState = heapq.heappop(statesSameSubproblem.stateHeap)

        # if outside of beam
        if lowerState.totalProb < bestScore-Stack.beamThreshold :
          print "breaking within subproblem"
          break
          
        lowerStates.append(lowerState)

      # recombination
      state.addRecombPointers(lowerStates)

      # add state to final list
      # this is the highest scoring one -- states will be added from high to low prob!
      finalStateList.append(state)
      finalStateDict[state] = ''

      # update total nr. of states in this stack
      self.nrStatesTotal += len(finalStateList)

    return (finalStateList, finalStateDict)


  # precondition: thresholdPruneAndRecombine has been run
  # postcondition: results in self.finalStateHeap
  def histogramPrune(self, finalStateList, finalStateDict):

    nrToRemain = min(self.nrStatesTotal, self.histogramPruneLimit)
    nrToRemove = max(0, self.nrStatesTotal - self.histogramPruneLimit)

    if nrToRemove > 0:
      if nrToRemove < nrToRemain:
        self.finalStateList = finalStateList[:-nrToRemove] # removes last k
      else :
        self.finalStateList = finalStateList[:nrToRemain] # remains first k
    else:
      self.finalStateList = finalStateList


class Decoder(object):

  # Limit decoding to using phrases not longer than 3 words (both sides)
  maxWords = 3

  wordPenalty = -1
  phrasePenalty = -1
  
  # hardcoded
  weightPerModel = {  'tm':1, # translation model
                      'lm':1, # language model
                      'lw':1, # lexical weights
                      
                              ## not really models more like features:
                      'dm':1, # distortion model/penalty
                      'pp':1, # phrase penalty
                      'wp':1, # word penalty
                      
                      'fp':1  # estimated future prob (future cost)
                    }


  def __init__(self, fSen, cache=None):

    self.fSen = "<s> " + fSen + " </s>"
    self.fList = self.fSen.split()
    self.nrFWords = len(self.fList)

    self.nrStacks = self.nrFWords # add <s> and </s>
    self.stackList = []
    for i in range(0, self.nrStacks):
      self.stackList.append(Stack(i))

    if cache == None:
      cache = Cache()
    self.cache = cache

    self.makeFutureCostModel()


  # lower = more unlikely
  # not penalty, but a score to add
  def calcDistortionPenalty(self, firstPosNow, lastPosPrevious):
    return (-1) * abs(firstPosNow -  lastPosPrevious - 1)


  def printFutureCostModel(self):
    for i in range(0, self.nrFWords):
      for j in range(i+1, min(i+self.maxWords, self.nrFWords)+1):
        print "%s --> %s " % ((i,j), self.futureCostTable[(i,j)])


  # please note last index is + 1, so:
  # if sentence has length 6
  # i.e. indices loop from 0, 1, .. 4, 5
  # then prob of
  #   first word = self.futureCostTable[(0,1)]
  #   last word = self.futureCostTable[(5,6)]
  #   2nd t/m 4th word = self.futureCostTable[(1,4)]
  def makeFutureCostModel(self) :
    # from (startpos, endpos) --> prob
    self.futureCostTable = defaultdict(lambda:(-10000))

    print "self.fSen: %s, self.nrFWords: %s" % (self.fSen, self.nrFWords)

    for llen in range(1, self.nrFWords+1):
      for i in range (0, self.nrFWords):
        j = min(i + llen, self.nrFWords)
        fPhrase = " ".join(self.fList[i:j])
        possibleTranslations = self.cache.TM(fPhrase)
        if len(possibleTranslations) > 0:
          bestTrans = possibleTranslations[0][0]
          bestTransTMProb = possibleTranslations[0][1]
          bestTransLMProb = self.cache.LMe(bestTrans)
          bestTransLWProb = self.cache.LW(fPhrase, bestTrans)

          self.futureCostTable[(i,j)] = bestTransTMProb + bestTransLMProb  + bestTransLWProb
        elif j == (i+1) : # 1 word
          fPhraseLMprob = self.cache.LMf(fPhrase)
          self.futureCostTable[(i,j)] = fPhraseLMprob -10

        # check for cheaper costs, DP way
        for k in range(i+1, j):
          combProb =  self.futureCostTable[(i,k)] + self.futureCostTable[(k, j)]
          if combProb > self.futureCostTable[(i,j)]:
            self.futureCostTable[(i,j)] = combProb


  def getFutureCost(self, covVector):

    maxSenIndex = self.nrFWords-1

    unCovered = list(set(range(0, maxSenIndex+1)) - set(covVector))
    unCovSpans = []

    unCovSpan = None
    for i in unCovered:
      if unCovSpan == None:
        unCovSpan = [i,i]
      elif unCovSpan[1] == i-1:
        unCovSpan[1] = i
      else:
        unCovSpans.append(unCovSpan)
        unCovSpan = [i,i]

    unCovSpans.append(unCovSpan)

    totalFutureCost = 0
    for span in unCovSpans:
      span = tuple(span)
      totalFutureCost += self.futureCostTable[span]

    return totalFutureCost


  def decodeFromStack(self,stackNr):
    stack = self.stackList[stackNr]
    stateList = stack.finalStateList
    nrFWordsTranslated = 0

    covVectorDict = defaultdict(list)

    for state in stateList:

      covVector = state.subproblem.translatedPositionsF

      for i in range(0, self.nrFWords):
        #print "i: %d" % i
        if i in covVector:
          continue
        for j in range(i+1, min(i+Decoder.maxWords+1, self.nrFWords+1)):
          #print "j: %d" % i
          if j-1 in covVector:
            break
          span = (i,j)
          fPhraseList = self.fList[i:j]
          fPhrase = " ".join(fPhraseList)

          #print "span: %s, fPhrase: %s" % ((i,j),fPhrase)
                                
          possibleTranslations = self.cache.TM(fPhrase)

          for trans in possibleTranslations:

            #print "trans of '%s': '%s'" % (fPhrase, trans[0])            
            #if fPhrase == 'argumenten .':
            #  print possibleTranslations
            #  sys.exit(0)
            
            enPhrase = trans[0]
            enList = enPhrase.split()
            ## calculate (and sum):
            # trans. prob, lex. weight, lm prob, distortion cost,  phrase penalty, word penalty
            ## and (add separately)
            # future cost est.

            transProb = trans[1]
            lexWeight = self.cache.LW(fPhrase, enPhrase)

            # sum lm prob's for all possible trigrams
            # (like if the enPhrase has length 3 there will be 3)
            lmProb  = 0
            #print state.subproblem.lastTwoWordsE
            lastTwoWordsE = copy.deepcopy(state.subproblem.lastTwoWordsE)   # at least has 1
            for newEnWord in enList:
             # print "newEnWord: %s" % newEnWord
              enSubList = lastTwoWordsE
              enSubList.append(newEnWord) # at least length 2
             # print "enSubList: %s" %enSubList
              enSubPhrase = " ".join(enSubList)
              lmProb += self.cache.LMe(enSubPhrase)
              lastTwoWordsE = enSubList[-2:]


            distPenalty = self.calcDistortionPenalty(i, state.subproblem.lastTranslatedPositionF)
            phrasePenalty = Decoder.phrasePenalty
            wordPenalty = Decoder.wordPenalty * (j-i)



            prob = sum([transProb, lexWeight, lmProb, distPenalty,phrasePenalty, wordPenalty])
            futureProb = self.getFutureCost(covVector)

            
            
            # the 1st subproblem property
            translatedPositionsF = sorted(covVector + range(i,j))
            # the 2nd subproblem property
            lastTwoWordsE = (state.subproblem.lastTwoWordsE + enList)[-2:]

            # if all states are covered (stackNrToAdd will be 7),
            # also calculate LM prob of last 2 and </s>            
            if (set(translatedPositionsF) == set(range(0,self.nrFWords))):
              #print "---> all covered"
              lastTwoWordsE.append('</s>')
              #lastTwoWordsE = lastTwoWordsE[-2:]
              enSubPhrase = " ".join(lastTwoWordsE[-2:])
              lmFinalProb = self.cache.LMe(enSubPhrase)
              prob += lmFinalProb
            
            
            (transProb, lmProb, lexWeight, distPenalty,phrasePenalty,wordPenalty,futureProb) = \
              self.reWeight(transProb, lmProb, lexWeight, distPenalty,phrasePenalty,wordPenalty,futureProb)
            
            print "(transProb, lmProb, lexWeight, distPenalty,phrasePenalty,wordPenalty,futureProb) : "
            print (transProb, lmProb, lexWeight, distPenalty,phrasePenalty,wordPenalty,futureProb) 
            
            
            stackNrToAdd = len(translatedPositionsF)-1
            bestScoreStackToAdd = self.stackList[stackNrToAdd].bestScore()
            
            if stackNrToAdd == self.nrStacks-1:
              (transProb, lmProb, lexWeight, distPenalty,phrasePenalty,wordPenalty,futureProb) = \
                (transProb, lmProb, lexWeight, distPenalty,phrasePenalty,wordPenalty-1,0)
              
            
            # only add it if it's within beam of *current* best score
            if (prob+futureProb) >= (bestScoreStackToAdd - Stack.beamThreshold) :

              # the 3rd subproblem property
              lastTranslatedPositionF = j-1 


              # define new state
              newSubproblem = Subproblem( translatedPositionsF, lastTranslatedPositionF, lastTwoWordsE)
              newState = State(subproblem=newSubproblem, translationCurrentPhraseE=enPhrase, prob=prob, backpointer=state,
                                  recombPointers=[], futureProb=futureProb, fPhrase=fPhrase)


              # add new state to correct stack
              self.stackList[stackNrToAdd].addState(newSubproblem, newState)
           


  def reWeight(self, tp, lm, lw, dm, pp, wp, fp ):
    weightPerModel = Decoder.weightPerModel
    
    if 'tp' in weightPerModel:
      tp = tp * weightPerModel['tp']
    if 'lm' in weightPerModel:
      lm = lm * weightPerModel['lm']
    if 'lw' in weightPerModel:
      lw = lw * weightPerModel['lw']
    
    if 'dm' in weightPerModel:
      dm = dm * weightPerModel['dm']
    if 'pp' in weightPerModel:
      pp = pp * weightPerModel['pp']
    if 'wp' in weightPerModel:
      wp = wp * weightPerModel['wp']
    
    if 'fp' in weightPerModel:
      fp = fp * weightPerModel['fp']
    
    return (tp, lm, lw, dm, pp, wp, fp)
                      
                      
  def decode(self):

    # stack 1 has translations of length 2, stack 2 has translations of length 3, etc.
    # this is because stack 0 has translation of length 1 (</s>)

    subProblemZero = Subproblem( translatedPositionsF=[0,self.nrFWords-1], lastTranslatedPositionF=0, lastTwoWordsE=['<s>'])
    stateZero = State(subproblem=subProblemZero, translationCurrentPhraseE='<s>', prob=0, backpointer=None,
                                  recombPointers=[], futureProb=0)


    self.stackList[0].addState(subProblemZero, stateZero)
    print "Postprocessing stack %d" % 0
    self.stackList[0].postProcess()
    print "Stack %d after postprocessing:" % 0
    print self.stackList[0]
    print "======= decoding from stack %d=============" % 0
    self.decodeFromStack(0)

    stackNr = 1
    while stackNr < self.nrStacks:

      print "=== new next stacks: === "
      for stackNrTemp in range(stackNr, min(stackNr+Decoder.maxWords, self.nrFWords)):
        print "Stack %d:" % (stackNrTemp)
        print self.stackList[stackNrTemp]


      print "Postprocessing stack %d" % stackNr
      self.stackList[stackNr].postProcess()

      print "Stack %d after postprocessing:" % stackNr
      print self.stackList[stackNr]

      print "======= decoding from stack %d=============" % stackNr
      self.decodeFromStack(stackNr)

      stackNr += 1

    print "end"
    print "nr stacks: %d" % self.nrStacks
    print "nrFWords: %d" % self.nrFWords
    print self.stackList[self.nrStacks-1]

 

    self.printViterbiSentence()
    

  def printViterbiSentence(self) :    
    
    endResultStack = self.nrStacks-1
    endState = None
    while True:  
      if len(self.stackList[endResultStack].finalStateList) > 0:
        endState = self.stackList[endResultStack].finalStateList[0]
        break
      endResultStack-= 1
    
    if endState == None:
      raise error('No stack has any translations!')
    
    notTranslatedPositions = []
    if endResultStack != self.nrStacks-1:
      notTranslatedPositions = list(set(range(0,self.nrFWords)) - set(endState.subproblem.translatedPositionsF) )
      
    print "notTranslatedPositions: %s" % notTranslatedPositions
    vList = []
    vList.append(endState)
    
    endStateOrig = endState
    
    while True:
      prevState = endState.backpointer
      if prevState == None:
        break
      vList.append(prevState)
      
      endState = prevState
      
    vList = list(reversed(vList))
    
    transList = []
    for i in range(1, len(vList)):
      translationState = vList[i]
      print "translation '%s' --> '%s'" % (translationState.fPhrase, translationState.translationCurrentPhraseE)
      print "translation cov. vector: %s" % translationState.subproblem.translatedPositionsF
      transList.append(translationState.translationCurrentPhraseE)
    
    if len(notTranslatedPositions) > 0:
      print "============"
      print "Failure to translate word(s): %s" % (list(self.fList[x] for x in notTranslatedPositions))
    print "============"
    print "Translation: %s" % " ".join(transList)
    print "Final prob.: %2.2f" % endStateOrig.totalProb
    print "============"
  
      
  

def test2(e_LMdir, f_LMdir, probs_file, fSen):

  cache = Cache(e_LMdir, f_LMdir, probs_file, fSen)
  dc  = Decoder(fSen, cache)

  dc.printFutureCostModel()

  dc.decode()


def test1():


  subprobl1 = Subproblem([1,2],1,'I am')
  s1 = State(subproblem=subprobl1, prob=-2,  futureProb=-2)
  subprobl1b = Subproblem([1,2],1,'I am')
  s2 = State(subproblem=subprobl1b, prob=-3, futureProb=-5)
  s3 = State(subproblem=subprobl1b, prob=-7)

  subprobl1States = StatesSameSubproblem([s1,s2,s3])



  subprobl2 = Subproblem([3,4,5],4,'am playing')
  s4 = State(subproblem=subprobl2, prob=-8)
  s5 = State(subproblem=subprobl2, prob=-1)


  subprobl2States = StatesSameSubproblem([s1,s2]  )

  #print subprobl1States.stateHeap
  #print subprobl1States
  #print subprobl2States.stateHeap
  #print subprobl2States



  stack = Stack()

  stack.addState(s1.subproblem, s1)
  stack.addState(s2.subproblem, s2)
  stack.addState(s3.subproblem, s3)

  print stack
  print len(stack.stackHeapDict.keys())

  stack.addState(s5.subproblem, s5)
  stack.addState(s4.subproblem, s4)

  print stack

  print len(stack.stackHeapDict)

  (finalStateList, finalStateDict) = stack.thresholdPruneAndRecombine(-1)

  print finalStateList

  stack.histogramPrune(finalStateList, finalStateDict)

  print stack.finalStateList



# python2.7 alt3_sk_test.py -eLM '../ass3/en_lm/' -fLM '../ass3/nl_lm/' -pF '../ass3/final_file.txt' -fSen 'wij zijn blij .'

# example:
#
#  python2.7 alt3_sk_test.py -eLM '../ass3/en_lm/' -fLM '../ass3/nl_lm/' -pF '../ass3/final_file.txt' -fSen 'de vergaderingen waren moeizaam . '
#
# or
#
#  python2.7 alt3_sk_test.py -eLM '/home/10406921/en_lm' -fLM '/home/10406921/nl_lm' -pF '/home/10363130/alt1/output_clean/final_file.txt' -fSen  'de vergaderingen waren moeizaam .'

if __name__ == '__main__': #if this file is called by python

  parser = argparse.ArgumentParser(description = "decoder")
  parser.add_argument('-eLM', '--englishLM', help='English LM dir', required=True)
  parser.add_argument('-fLM', '--foreignLM', help='Foreign LM dir', required=True)
  parser.add_argument('-pF', '--phraseProbsFile', help='output file from ALT assignment 1', required=True)
  parser.add_argument('-fSen', '--foreignSentence', help='foreign sentence to decode', required=True)

  args = parser.parse_args()
  e_LMdir = args.englishLM
  f_LMdir = args.foreignLM
  probs_file = args.phraseProbsFile
  fSen = args.foreignSentence

  test2(e_LMdir, f_LMdir, probs_file, fSen)
