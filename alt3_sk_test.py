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
    
  def __str__(self):
     return "\n\tsubproblem: <%s,%s,%s>" % (self.translatedPositionsF, self.lastTranslatedPositionF, self.lastTwoWordsE)
  
  def __repr__(self):
    return self.__str__()
  
  """  
  def __hash__(self):
    return hash((self.p1, self.p2, self.p3))

  def __eq__(self, other):
    return (self.p1, self.p2, self.p3) == (other.p1, other.p2, other.p3)
  """
  
# holds all state (hypothesis) properties
# hold 4 state-specific properties as well as a Subproblem object with 3 
# more properties
class State(object):
  
  def __init__(self, subproblem=None, translationCurrentPhraseE=None, prob=sys.maxint*(-1), backpointer=None, recombPointers=[]):
    
    self.subproblem = subproblem # instance of class Subproblem, containing 3 properties
    
    self.translationCurrentPhraseE = translationCurrentPhraseE
    self.prob = prob #translation probability
    self.backpointer = backpointer # one backpointer to previous state
    self.recombPointers = recombPointers # "back"-pointers to recombined states
    
    self.nrFWordsTranslated = len(self.subproblem.translatedPositionsF) # nr. of foreign words translated
  
  # heapify by largest probability first
  def __lt__(self, other):
    return self.prob > other.prob
  
  def __str__(self):
     return "state: %.2f" % self.prob
  
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
    
  # largest prob. of all the states it contains
  def calcProb(self):
    return self.stateHeap[0].prob
  
  def __lt__(self, other):
    return self.calcProb() > other.calcProb()
      
  def __str__(self):
     return "\n\t\tstateHeap: %.2f" % self.calcProb()
  
  def __repr__(self):
    return self.__str__()
  
  # maintains heap invariant
  def addState(self, s):
    heapq.heappush(self.stateHeap, s)
    return self
    

#heap-dict of type
# Subproblem --> StatesSameSubproblem
class StackHeapDict(pqdict.PQDict):
  
  def __init__(self, *args, **kwargs):
    super(StackHeapDict, self).__init__(*args, **kwargs)
  
  # maintains heap invariant
  # also b/c it calls StatesSameSubproblem.assState which does
  def addState(self, key, state):
    self.updateitem(key, self[key].addState(state))


def run():
  
  
  subprobl1 = Subproblem([1,2],1,'I am')
  s1 = State(subproblem=subprobl1, prob=-2)
  s2 = State(subproblem=subprobl1, prob=-3)
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
  pq.addState(subprobl1, State(subproblem=subprobl1, prob=-0.5))
  
  print pq
  
  # returns two b/c
  print subprobl1States.stateHeap[0] == subprobl1States.stateHeap[1]
  
  print subprobl1States.stateHeap[0] == subprobl2States.stateHeap[0]
if __name__ == '__main__': #if this file is called by python
  

  
  run()
