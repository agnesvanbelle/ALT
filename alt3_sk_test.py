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

"""
- All hypotheses (states) that are comparable for pruning
  are in the same stack
- All hypotheses that can be recombined are in the same
  stack

- Before expanding the hypotheses in stack m:
--  All hypotheses (s) in stack m are sorted according to
    current cost(s)+future cost(s)
    
--  Prune hypotheses that are outside of the beam of the
    top-scoring hypothesis
    
--  Recombine all remaining hypotheses (where possible)

--  Histogram pruning: If there are k hypotheses in stack m and
    k > l, where l is the histogram pruning limit, remove the k-l
    lowest scoring hypotheses

"""
class State(object):
  
  def __init__(self, prob=sys.maxint*(-1)):
    self.prob = prob
  
  
  # heapify by largest probability first
  def __lt__(self, other):
    return self.prob > other.prob
  
  def __str__(self):
     return "state: %.2f" % self.prob
  
  def __repr__(self):
    return self.__str__()
    
class StatesSameSubproblem(object):
  
  def __init__(self, stateHeap ):
    self.stateHeap = stateHeap
    #self.prob = self.calcProb()
    
  # largest prob. of all the states it contains
  def calcProb(self):
    return self.stateHeap[0].prob
  
  def __lt__(self, other):
    return self.calcProb() > other.calcProb()
      
  def __str__(self):
     return "stateHeap: %.2f" % self.calcProb()
  
  def __repr__(self):
    return self.__str__()
  
  def addState(self, s):
    heapq.heappush(self.stateHeap, s)
    return self
    
class Subproblem(object):
  
  def __init__(self, p1, p2, p3):
    self.p1 = p1
    self.p2 = p2
    self.p3 = p3
    
  def __str__(self):
     return "subproblem: <%s,%s,%s>" % (self.p1, self.p2, self.p3)
  
  def __repr__(self):
    return self.__str__()
    
def run():
  
  s1 = State(-4)
  s2 = State(-2)
  s3 = State(-1.5)
  stateHeap = [s1,s2,s3]  
  heapq.heapify(stateHeap)
  
  
  
  subprobl1States = StatesSameSubproblem(stateHeap)
  
  
  
  s1 = State(-1)
  s2 = State(-8)
  stateHeap = [s1,s2]  
  heapq.heapify(stateHeap)
  
  subprobl2States = StatesSameSubproblem(stateHeap)
  
  print subprobl1States.stateHeap
  print subprobl1States
  print subprobl2States.stateHeap
  print subprobl2States

  subprobl1 = Subproblem('a','b','c')
  subprobl2 = Subproblem('a','d','e')
  
  pq = PQDict()
  pq.additem(subprobl1, subprobl1States)
  pq.additem(subprobl2, subprobl2States)
  
  print pq
  
  # idea is that we can easily add states to the right subproblem-heap
  # by using subproblem-based dictionary keys
  print pq[subprobl1]
  print pq[subprobl1].stateHeap
  
  pq.updateitem(subprobl1, pq[subprobl1].addState(State(-0.5)))
  
  print pq[subprobl1].stateHeap
  print pq
  
  
if __name__ == '__main__': #if this file is called by python
  

  
  run()
