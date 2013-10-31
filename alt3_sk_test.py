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

"""
- All hypotheses (states) that are comparable for pruning
  are in the same stack
- All hypotheses that can be recombined are in the same
  stack

- Before expanding the hypotheses in stack m:
--  All hypotheses (s) in stack m are sorted according to
    current cost(s)+future cost(s)
    NOTE: this is simply translation probability + future cost
    since a future "cost" is also in terms of log probs,
    a future "cost" that is "higher" actually means a lower cost (-1 is lower cost than -2 for example)
    so I call it a "future Probability" in the code

--  Prune hypotheses that are outside of the beam of the
    top-scoring hypothesis (threshold pruning) (compare all states, regardless of Subproblem)

--  Recombine all remaining hypotheses (where possible)

--  Histogram pruning: If there are k hypotheses in stack m and
    k > l, where l is the histogram pruning limit, remove the k-l
    lowest scoring hypotheses

"""


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
      #print "checking equality"
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

  def __init__(self, subproblem=None, translationCurrentPhraseE=None, prob=sys.maxint*(-1), backpointer=None, recombPointers=[], futureProb=0):

    self.subproblem = subproblem # instance of class Subproblem, containing 3 properties

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

  """
  # for threshold pruning : comparable definition
  def __eq__(self, other):
    if isinstance(other, State):
      return self.nrFWordsTranslated == other.nrFWordsTranslated

    return NotImplemented

  # for threshold pruning : comparable definition
  def __ne__(self, other):
    result = self.__eq__(other)
    if result is NotImplemented:
      return result
    return not result
  """

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
    #print self.keys()
    #print "key: %s" % key
    if key in self:
      #print "key in self"
      self.updateitem(key, self[key].addState(state))
    else:
      #print "key not in self"
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
  beamThreshold = 0.5
  histogramPruneLimit = 50

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
        #lowerState = copy.deepcopy(lowerState) # necessary? we remove stackHeapDict but popped it

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
    """
    if nrToRemove > 0:
      print "editing stack with histogram pruning"
      # complexity of heapq.nlargest is n*log(k), of nsmallest I assume similar
      if self.nrStatesTotal*math.log(nrToRemove)*nrToRemove < self.nrStatesTotal*math.log(nrToRemain):
        print "removing"
        # remove smallest
        toRemoveList = heapq.nlargest(nrToRemove, finalStateList)
        for state in toRemoveList:
          finalStateDict.pop(state, None)
        self.finalStateHeap = finalStateDict.keys()

      else: # remain largest
        print "keeping"
        self.finalStateList = heapq.nsmallest(nrToRemain, finalStateList)

      del finalStateDict

    else:
      self.finalStateList = finalStateList
    """

class OldCache(object):

  transDict =  {"ik":[("I", -0.2)],
                #"<s> ik":[("<s> I", -0.9)],
                "ben":[("am", -0.1),("are",-0.8)],
                "ik ben": [("I am", -0.9), ("I exist", -0.1)],
                "ben":[("am", -0.8)],
                "nu":[("now", -1)],
                "al":[("yet", -1)],
                "nu al":[("already",-1.5)],
                "hier": [("here", -0.6)],
                "hier .": [("here .",-0.1)],
                "." :[ (".",-1)]
                #". </s>" :[ (". </s>",-1)]
                }

  def TM(self, fPhrase):
    if fPhrase in  Cache.transDict:
      return Cache.transDict[fPhrase]
    else:
      return []

  def LMe(self, eSen):
    return -1

  def LMf(self, fSen):
    return -2

  def LW(self, fPhrase, ePhrase):
    return -3

class Decoder(object):

  # Limit decoding to using phrases not longer than 3 words (both sides)
  maxWords = 3

  wordPenalty = -1
  phrasePenalty = -1

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
        #print "fPhrase: %s, range:%s" % (fPhrase, (i,j))
        possibleTranslations = self.cache.TM(fPhrase)
        if len(possibleTranslations) > 0:
          # TODO: check if sorting on prob. needed for TM
          #possibleTranslations = sorted(possibleTranslations, key=itemgetter(1), reverse=True)
          bestTrans = possibleTranslations[0][0]
          bestTransTMProb = possibleTranslations[0][1]
          bestTransLMProb = self.cache.LMe(bestTrans)
          # lexical weights?
          bestTransLWProb = self.cache.LW(fPhrase, bestTrans)

          self.futureCostTable[(i,j)] = bestTransTMProb + bestTransLMProb  + bestTransLWProb
        elif j == (i+1) : # 1 word
          #print "i+1==j"
          fPhraseLMprob = self.cache.LMf(fPhrase)
          self.futureCostTable[(i,j)] = fPhraseLMprob -10

        # check for cheaper costs, DP way
        for k in range(i+1, j):
          #print "checking recomb for %s and %s" % ((i,k),(k,j))
          combProb =  self.futureCostTable[(i,k)] + self.futureCostTable[(k, j)]
          #print "combProb: %2.2f" % combProb
          if combProb > self.futureCostTable[(i,j)]:
            #print "found cheaper cost"
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


          print "span: %s, fPhrase: %s" % ((i,j),fPhrase)
          """
          if fPhrase == "</s>" and stackNr == self.nrStacks-1:
            print "fPhrase is </s>"
            possibleTranslations = [('</s>',0)]

          else:
        """
          possibleTranslations = self.cache.TM(fPhrase)

          for trans in possibleTranslations:

            print "trans of '%s': '%s'" % (fPhrase, trans[0])

            enPhrase = trans[0]
            enList = enPhrase.split()
            ## calculate (and sum):
            # trans. prob
            # lex. weight
            # lm prob
            # distortion cost
            # phrase penalty
            # word penalty
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

            lastTwoWordsE = (state.subproblem.lastTwoWordsE + enList)[-2:]

            # if all states are covered (stackNrToAdd will be 7),
            # also calculate LM prob of last 2 and </s>
            if (set(translatedPositionsF) == set(range(0,self.nrFWords))):
              print "---> all covered"
              lastTwoWordsE.append('</s>')
              #lastTwoWordsE = lastTwoWordsE[-2:]
              enSubPhrase = " ".join(lastTwoWordsE[-2:])
              lmFinalProb = self.cache.LMe(enSubPhrase)
              prob += lmFinalProb

            stackNrToAdd = len(translatedPositionsF)-1
            bestScoreStackToAdd = self.stackList[stackNrToAdd].bestScore()

            # only add it if it's within beam of *current* best score
            if (prob+futureProb) >= (bestScoreStackToAdd - Stack.beamThreshold) :

              lastTranslatedPositionF = j-1 #?


              # define new state
              newSubproblem = Subproblem( translatedPositionsF, lastTranslatedPositionF, lastTwoWordsE)
              newState = State(subproblem=newSubproblem, translationCurrentPhraseE=enPhrase, prob=prob, backpointer=state,
                                  recombPointers=[], futureProb=futureProb)


              # add new state to correct stack
              self.stackList[stackNrToAdd].addState(newSubproblem, newState)
            else:
              print "was below beam threshold"



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

    # TODO: if not find full coverage, replace misisng indices
    # with foreign words (don't edit prob)

    endState = self.stackList[self.nrStacks-1].finalStateList[0]

    print "endState prob: %s" % endState
    print "endState lmH: %s" % endState.subproblem.lastTwoWordsE
    print "endState translationCurrentPhraseE: %s" % endState.translationCurrentPhraseE
    print "endState translatedPositionsF: %s" % endState.subproblem.translatedPositionsF
    while True:
      prevState = endState.backpointer
      if prevState == None:
        break
      print "prevState prob: %s" % prevState
      print "prevState lmH: %s" % prevState.subproblem.lastTwoWordsE
      print "prevState translationCurrentPhraseE: %s" % prevState.translationCurrentPhraseE
      print "prevState translatedPositionsF: %s" % prevState.subproblem.translatedPositionsF
      endState = prevState


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

# e_LMdir, f_LMdir, probs_file, fSen)


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
