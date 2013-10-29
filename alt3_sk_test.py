import sys
import os
import math
import cPickle as pickle
import gc
import itertools
import copy
import collections
import argparse
import heapq
import math 

from pqdict import PQDict # see https://github.com/nvictus/priority-queue-dictionary
import pqdict
import utilities

import copy

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
    a future "cost" that is "higher" actually means a lower cost (-1 is lower than -2 for example)
    so I call it a "future Probability" in the code
    
--  Prune hypotheses that are outside of the beam of the
    top-scoring hypothesis (threshold pruning) (compare all states, regardless of Subproblem)
    
--  Recombine all remaining hypotheses (where possible)

--  Histogram pruning: If there are k hypotheses in stack m and
    k > l, where l is the histogram pruning limit, remove the k-l
    lowest scoring hypotheses

"""

beamThreshHold = 2.9

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
  

  
# holds all state (hypothesis) properties
# hold 4 state-specific properties as well as a Subproblem object with 3 
# more properties
class State(object):
  
  def __init__(self, subproblem=None, translationCurrentPhraseE=None, prob=sys.maxint*(-1), backpointer=None, recombPointers=[], futureProb=0):
    
    self.subproblem = subproblem # instance of class Subproblem, containing 3 properties
    
    self.translationCurrentPhraseE = translationCurrentPhraseE
    self.prob = prob #translation probability
    self.backpointer = backpointer # one backpointer to previous state
    self.recombPointers = recombPointers # "back"-pointers to recombined states, should be heap too, b/c n-best 
    
    # for pruning
    self.futureProb= futureProb
    self.totalProb = self.prob  + self.futureProb
    
    self.nrFWordsTranslated = self.subproblem.nrFWordsTranslated   # nr. of foreign words translated
  
  
  def addRecombPointers(self, heapPointers):
    if self.recombPointers == []:
      self.recombPointers = heapPointers
    else :
      self.recombPointers.extend(heapPointers)
      heapq.heapify(self.recombPointers)
      
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
     return "\n\t\tstateHeap: %.2f" % self.calcTotalProb()
  
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
  beamThreshold = 2.9
  histogramPruneLimit = 1
  
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
  
    
  def addState(self, subproblem, state):
    self.stackHeapDict.addState(subproblem, state)
    
  def postProcess(self, bestScore):
    
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
        
      #if state.totalProb < bestScore-Stack.beamThreshold : # probability is within beam
          
      # deep copy necessary (?) b/c we will remove stackHeapDict later
      lowerStates = copy.deepcopy(statesSameSubproblem.stateHeap)
      
      # recombination  
      state.addRecombPointers(lowerStates)
      
      # add state to final list
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
      
    
    
      

def test1():
  
  
  subprobl1 = Subproblem([1,2],1,'I am')
  s1 = State(subproblem=subprobl1, prob=-2,  futureProb=-2)
  s2 = State(subproblem=subprobl1, prob=-3, futureProb=-5)
  s3 = State(subproblem=subprobl1, prob=-7)
  
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
  
if __name__ == '__main__': #if this file is called by python
  
  test1()
