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

from pqdict import PQDict # see https://github.com/nvictus/priority-queue-dictionary
import pqdict
import utilities
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
    self.recombPointers = recombPointers # "back"-pointers to recombined states
    
    # for pruning
    self.futureProb= futureProb
    self.totalProb = self.prob  + self.futureProb
    
    self.nrFWordsTranslated = self.subproblem.nrFWordsTranslated   # nr. of foreign words translated
  
    
  # heapify by highest total prob 
  def __lt__(self, other):
    return self.totalProb > other.totalProb
  
  def __str__(self):
     return "state: %.2f" % self.totalProb
  
  def __repr__(self):
    return self.__str__()
    
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
    
    
  
# defines a stack
#
# basically, it's a heap-dict of type
# Subproblem --> StatesSameSubproblem
class StackHeapDict(pqdict.PQDict):
  
  # static attributes
  beamThreshold = 2.9
  histogramPruneLimit = 5
  
  def __init__(self, nrFWordsTranslated=None, *args, **kwargs):
    super(StackHeapDict, self).__init__(*args, **kwargs)
  
    # a stack is defined by the nr. of foreign words translated
    if nrFWordsTranslated == None:    
      if len(self) > 0:
        self.nrFWordsTranslated = self.peek()[0].nrFWordsTranslated

        
  # maintains heap invariant
  # also b/c it calls StatesSameSubproblem.assState which does
  def addState(self, key, state):
    self.updateitem(key, self[key].addState(state))


  # TODO
  def thresholdPrune(self, bestState):
    pass
  
  
  def recombine(self):    
    pass
    
      
  def histogramPrune(self):
    pass
    
  
  
def test1():
  
  
  subprobl1 = Subproblem([1,2],1,'I am')
  s1 = State(subproblem=subprobl1, prob=-2,  futureProb=-2)
  s2 = State(subproblem=subprobl1, prob=-3, futureProb=-5)
  s3 = State(subproblem=subprobl1, prob=-7)
  
  subprobl1States = StatesSameSubproblem([s1,s2,s3])
  
  
  
  subprobl2 = Subproblem([3,4,5],4,'am playing')
  s1 = State(subproblem=subprobl2, prob=-8)
  s2 = State(subproblem=subprobl2, prob=-1)
  
  
  subprobl2States = StatesSameSubproblem([s1,s2]  )
  
  print subprobl1States.stateHeap
  print subprobl1States
  print subprobl2States.stateHeap
  print subprobl2States

  
  
  
  pq = StackHeapDict()
  pq[subprobl1] = subprobl1States
  pq[subprobl2] = subprobl2States

  print pq
  
  # idea is that we can easily add states to the right subproblem-heap
  # by using subproblem-based dictionary keys

  #pq.updateitem(subprobl1, pq[subprobl1].addState(State(-0.5)))
  pq.addState(subprobl1, State(subproblem=subprobl1, prob=-0.5, futureProb=-0.01))
  
  print pq
  
  # returns true b/c same nr. of translated foreign words
  print subprobl1States.stateHeap[0] == subprobl1States.stateHeap[1]
  
  # returns false b/c different nr. of translated foreign words
  print subprobl1States.stateHeap[0] == subprobl2States.stateHeap[0]
  
  
if __name__ == '__main__': #if this file is called by python
  
  test1()
