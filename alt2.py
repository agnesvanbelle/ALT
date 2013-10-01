# ALT Assignment 1
# Agnes van Belle
# Nikos Voskarides


# usage:
# python alt1.py
#   -a <alignments file>
#   -e <english sentence file>
#   -f <dutch sentence file>
#   -o <output dir for final file>
#
# example usage command:
# python2.7 alt1.py -a /home/cmonz1/alt2013/dutch-english/web/web.aligned  -e /home/cmonz1/alt2013/dutch-english/web/web.en -f /home/cmonz1/alt2013/dutch-english/web/web.nl -o ./output_web


import sys
import os
import math
import cPickle as pickle
import gc
import itertools
import copy
import collections
import argparse



MAXIMUM_READ_SENTENCES = 8 #10000 # for debug purposes

gc.disable()


class Orientation:
  MONOTONE = 0
  SWAP = 1
  DISC_LEFT = 2
  DISC_RIGHT = 3

  @staticmethod
  def getString( n):
    if n == 0:
      return "MONOTONE"
    elif n == 1:
      return "SWAP"
    elif n == 2:
      return "DISC_LEFT"
    elif n == 3 :
      return "DISC_RIGHT"
    else:
      return "<error>"
  

class DirectionName :
  LEFT_TO_RIGHT = 0
  RIGHT_TO_LEFT = 1
  
  @staticmethod
  def getString( n):
    if n == 0:
      return "LEFT_TO_RIGHT"
    elif n == 1:
      return "RIGHT_TO_LEFT"
    else:
      return "<error>"

  

# class containing:
#   - a dict from Orientation -> count
#   - a total count (over all Orientations)
class Direction (object):

  def __init__(self, orientations_dict=None):
    self.totalOrientations = 0

    if (orientations_dict == None):
      self.orientationsDict = collections.defaultdict(int)
    else :
      self.orientationsDict = orientations_dict


  def increaseOrientation(self, o) :
    self.orientationsDict[o] += 1
    self.totalOrientations += 1
  

# class containing:
#  directionLR :
#     total count + a dict from Direction->count
#  directionRL :
#     total count + a dict from Direction->count
class PhrasePairTableEntry(object) :


  def __init__(self, phrase_pair_count=0, direction_lr = None, direction_rl = None):
    self.phrasePairCount = phrase_pair_count

    if (direction_lr == None) :
      self.directionLR = Direction()
    else :
      self.directionLR = direction_lr

    if (direction_rl == None):
      self.directionRL = Direction()
    else :
      self.directionRL = direction_rl

  def increaseOrientation(self,  d,  o) :
    if d == DirectionName.LEFT_TO_RIGHT:
      self.directionLR.increaseOrientation(o)
    elif d == DirectionName.RIGHT_TO_LEFT:
      self.directionRL.increaseOrientation(o)
    else:
      raise ValueError("pass a DirectionName")




# class that extract phrase pairs and computes phrase-translation and
# lexical translation probabilities from the counts, and finally writes it to a file
class Extractor(object):


  # maximum phrase length
  maxPhraseLen = 2

  def __init__(self, reader, outputDir ):
    self.reader = reader
    self.tablePath = os.path.abspath(outputDir) + '/'

    
    self.table_nl_en_phraseBased = collections.defaultdict(PhrasePairTableEntry)
    self.table_nl_en_wordBased = collections.defaultdict(PhrasePairTableEntry)

    self.unique_nl_en = 0

    self.total_extracted = 0

    # for both directions (l->r and r->l),
    # keep track of all orientation
    # counts for all phrase pairs
    self.directionLR = Direction()
    self.directionRL = Direction()

    if not os.path.exists(self.tablePath):
      os.makedirs(self.tablePath)


  # increase global orientation count
  def increaseOrientation(self,  d,  o) :
    if d == DirectionName.LEFT_TO_RIGHT:
      self.directionLR.increaseOrientation(o)
    elif d == DirectionName.RIGHT_TO_LEFT:
      self.directionRL.increaseOrientation(o)
    else:
      raise ValueError("pass a DirectionName")



  # extract phrases for all sentence pairs  (provided by the "Reader")
  def extract(self):
      self.reader.line_list_aligns = "Meaningless init value because python has no do..while"
      while (self.reader.line_list_aligns != None and self.reader.counter < MAXIMUM_READ_SENTENCES): # the fixed limit is only for debug

        if (self.reader.counter > 0 and self.reader.counter % 500 == 0):
          sys.stdout.write('Reached line ' + str(self.reader.counter) + ' \n')
        self.reader.load_next_line()
        if (self.reader.line_list_aligns != None):
          # parse phrases using  the dutch sentence, the english sentence and their alignments-list
          self.parseSentencePair(self.reader.line_list_aligns, self.reader.line_nl_words, self.reader.line_en_words)

      # print stats
      self.printStats()

      # write stats to file
      #self.writeStatsToFile()

      sys.stdout.write('Done .\n')
      
      print "size table_nl_en_phraseBased: %d " % len(self.table_nl_en_phraseBased)
      #phrasePair = ("mevrouw", "madam")
      
      
      
      

  def printPhrasePair(self,phrasePair) :
    
    print "phrasePair: %s" % (phrasePair,)
    
    if phrasePair in self.table_nl_en_phraseBased:
      te =  self.table_nl_en_phraseBased[phrasePair]
      teLR =  te.directionLR

      print "LR:"
      for o, c in teLR.orientationsDict.iteritems() :
        print "\torientation: %s, count: %d" % (Orientation.getString(o), c)
      print "\ttotal # of orientations LR: %d" % teLR.totalOrientations
      
      teRL =  te.directionRL
      print "RL:"
      for o, c in teRL.orientationsDict.iteritems() :
        print "\torientation: %s, count: %d" % (Orientation.getString(o), c)
      print "\ttotal # of orientations RL: %d" % teRL.totalOrientations
    else:
      print "not in phrase table"
    
  # print stats
  def printStats(self) :
    sys.stdout.write('\n')
    sys.stdout.write('Extracted ' + str(self.total_extracted) + ' phrase pairs \n' +
                      '\t unique pairs: ' + str(self.unique_nl_en) + '\n' )







  #extract phrases from one sentence pair
  # used in Extractor.extract()
  def parseSentencePair(self, alignments, list_nl, list_en):


    len_list_nl = len(list_nl)
    len_list_en = len(list_en)
    len_alignments = len(alignments)

    nl_to_en = [[100, -1] for i in range(len_list_nl)] #coverage range: [minimum, maximum]
    en_to_nl = [[100, -1] for i in range(len_list_en)]

    #print nl_to_en

    nl_to_en_lex = collections.defaultdict(list)
    en_to_nl_lex = collections.defaultdict(list)

    for a_pair in alignments:
      #print a_pair

      nl_index = a_pair[0]
      en_index = a_pair[1]

      nl_to_en[nl_index][0] = min(en_index, nl_to_en[nl_index][0])
      nl_to_en[nl_index][1] = max(en_index, nl_to_en[nl_index][1])

      en_to_nl[en_index][0] = min(nl_index, en_to_nl[en_index][0])
      en_to_nl[en_index][1] = max(nl_index, en_to_nl[en_index][1])

      nl_to_en_lex[nl_index].append(en_index)
      en_to_nl_lex[en_index].append(nl_index)



    nl_to_null = []
    en_to_null = []

    listOfPairsAsText = []
    listOfPairsAsRanges = []


    for nl_index1 in range(0, len_list_nl-1): # do not check as start-word the period at the end

      enRange = nl_to_en[nl_index1]

      if (enRange != [100, -1]): #if nl start-word is aligned

        nlFromEnMin = min(en_to_nl[enRange[0]][0], en_to_nl[enRange[1]][0])
        nlFromEnMax = max(en_to_nl[enRange[0]][1], en_to_nl[enRange[1]][1])

        nl_index2 = nl_index1
        while(nl_index2 < min(nl_index1 + self.maxPhraseLen, len_list_nl)):

          enRangeThisIndex = nl_to_en[nl_index2]


          if (enRangeThisIndex != [100, -1]): #if nl end-word is aligned
            # update the nl-to-en range
            enRange = [min(enRange[0], enRangeThisIndex[0]), max(enRange[1], enRangeThisIndex[1])]

            if (enRange[1] - enRange[0] < self.maxPhraseLen):
              # update the nl-to-en-to-nl range
              for  enIndex in range(enRange[0], enRange[1]+1):
                nlFromEnMin = min(nlFromEnMin, en_to_nl[enIndex][0], en_to_nl[enIndex][1])
                nlFromEnMax = max(nlFromEnMax, en_to_nl[enIndex][0], en_to_nl[enIndex][1])

              # nl-to-en-to-nl range minimum is below nl-range minimum
              if nlFromEnMin < nl_index1:
                break



              #####################################################################
              # nl-to-en-to-nl range is same as nl-to-en range: got consistent pair
              #####################################################################
              elif [nl_index1, nl_index2] == [nlFromEnMin, nlFromEnMax] :


                #self.addPair(list_nl, list_en, nl_index1, nl_index2, enRange[0], enRange[1])
                (listOfPairsAsText, listOfPairsAsRanges) = self.updatePairStats ( listOfPairsAsText, 
                                                                                  listOfPairsAsRanges, 
                                                                                  list_nl, list_en, 
                                                                                  nl_index1, nl_index2, enRange[0], enRange[1])


                ####################
                #check for unaligned
                ######################
                nl_unaligned_list = []
                en_unaligned_list = []

                ## unaligned on dutch  side
                #above unlimited
                nl_index2_copy = nl_index2 + 1
                while nl_index2_copy < min(nl_index1 + self.maxPhraseLen, len_list_nl) and nl_to_en[nl_index2_copy] == [100, -1] :
                  nl_unaligned_list.append([nl_index1, nl_index2_copy])
                  nl_index2_copy += 1

                # below unlimited
                nl_index1_copy = nl_index1 - 1
                while nl_index1_copy >= 0  and nl_to_en[nl_index1_copy] == [100,-1] :
                  nl_unaligned_list.append([nl_index1_copy, nl_index2])

                  # above unlimited for this below-level
                  nl_index2_copy = nl_index2 + 1
                  while nl_index2_copy < min(nl_index1_copy + self.maxPhraseLen, len_list_nl)  and nl_to_en[nl_index2_copy] == [100, -1] :
                    nl_unaligned_list.append([nl_index1_copy, nl_index2_copy])
                    nl_index2_copy += 1

                  nl_index1_copy -= 1

                ## unaligned on english  side
                en_index1 = enRange[0]
                en_index2 = enRange[1]

                #above unlimited
                en_index2_copy = en_index2 + 1
                while en_index2_copy < min(en_index1 + self.maxPhraseLen, len_list_en) and en_to_nl[en_index2_copy] == [100, -1] :
                  en_unaligned_list.append([en_index1, en_index2_copy])
                  en_index2_copy += 1

                # below unlimited
                en_index1_copy = en_index1 - 1
                while en_index1_copy >= 0  and en_to_nl[en_index1_copy] == [100,-1] :
                  en_unaligned_list.append([en_index1_copy, en_index2])

                  # above unlimited for this below-level
                  en_index2_copy = en_index2 + 1
                  while en_index2_copy < min(en_index1_copy + self.maxPhraseLen, len_list_en)  and en_to_nl[en_index2_copy] == [100, -1] :
                    en_unaligned_list.append([en_index1_copy, en_index2_copy])
                    en_index2_copy += 1

                  en_index1_copy -= 1


                # add unaligned nl's for current english phrase
                for unaligned_nl in nl_unaligned_list :
                  
                  #self.addPair(list_nl, list_en, unaligned_nl[0], unaligned_nl[1], enRange[0], enRange[1])
                  (listOfPairsAsText, listOfPairsAsRanges) = self.updatePairStats ( listOfPairsAsText, 
                                                                                  listOfPairsAsRanges, 
                                                                                  list_nl, list_en, 
                                                                                  unaligned_nl[0], unaligned_nl[1], 
                                                                                  enRange[0], enRange[1])

                # add unaligned en's for current dutch phrase
                for unaligned_en in en_unaligned_list :
                  #self.addPair(list_nl, list_en, nl_index1, nl_index2, unaligned_en[0], unaligned_en[1])
                  (listOfPairsAsText, listOfPairsAsRanges) = self.updatePairStats ( listOfPairsAsText, 
                                                                                  listOfPairsAsRanges, 
                                                                                  list_nl, list_en, 
                                                                                  nl_index1, nl_index2, 
                                                                                  unaligned_en[0], unaligned_en[1])

                  # add unaliged nl / unaligned en combi's
                  for unaligned_nl in nl_unaligned_list :
                    #self.addPair(list_nl, list_en, unaligned_nl[0], unaligned_nl[1], unaligned_en[0], unaligned_en[1])
                    (listOfPairsAsText, listOfPairsAsRanges) = self.updatePairStats ( listOfPairsAsText, 
                                                                                      listOfPairsAsRanges, 
                                                                                      list_nl, list_en, 
                                                                                      unaligned_nl[0], unaligned_nl[1], 
                                                                                      unaligned_en[0], unaligned_en[1])


            else:
              break



          nl_index2 +=1

    # TODO: calculate phrase based probs here\
    self.calcOrientationCounts(listOfPairsAsRanges, listOfPairsAsText, nl_to_en_lex, len_list_nl, len_list_en)
    
    # update phrase table
    print listOfPairsAsText
    print ""
    print listOfPairsAsRanges
    print "\n"
    
    for phrasePair in listOfPairsAsText:
      self.printPhrasePair(phrasePair)
  
  
  def updatePairStats (self, listOfPairsAsText, listOfPairsAsRanges, list_nl, list_en, start_nl, end_nl, start_en, end_en):
    listOfPairsAsText.append(( self.getRangeAsText(list_nl, start_nl,end_nl),
                               self.getRangeAsText(list_en, start_en, end_en)))
    listOfPairsAsRanges.append( ((start_nl, end_nl), (start_en, end_en)))

    return (listOfPairsAsText, listOfPairsAsRanges)


  def calcOrientationCounts(self, listOfPairsAsRanges, listOfPairsAsText, nl_to_en_alignments, len_nl, len_en) :
    
    rc = ReorderingCalculator()
    dictPhrasesLR = rc.phrase_lexical_reordering_left_right(listOfPairsAsRanges, len_en, len_nl)
    print
    dictPhrasesRL = rc.phrase_lexical_reordering_right_left(listOfPairsAsRanges, len_en, len_nl)
    print
    dictWordsLR = rc.word_lexical_reordering_left_right(listOfPairsAsRanges, nl_to_en_alignments, len_en, len_nl)
    print
    dictWordsRL = rc.word_lexical_reordering_right_left(listOfPairsAsRanges, nl_to_en_alignments, len_en, len_nl)
    print
    
    for i in range(0, len(listOfPairsAsRanges)) :
      phrasePairRange = listOfPairsAsRanges[i]
      phrasePairText = listOfPairsAsText[i]
      
      self.total_extracted += 1
      if not (phrasePairText in self.table_nl_en_phraseBased) :
        self.unique_nl_en += 1
      
      self.table_nl_en_phraseBased[phrasePairText].increaseOrientation(DirectionName.LEFT_TO_RIGHT,  dictPhrasesLR[phrasePairRange]) 
      #print "increasing orientation for phrase %s, direction %s, orientation %s" % (phrasePairText, DirectionName.LEFT_TO_RIGHT, dictPhrasesLR[phrasePairRange])
      
      self.table_nl_en_phraseBased[phrasePairText].increaseOrientation(DirectionName.RIGHT_TO_LEFT,  dictPhrasesRL[phrasePairRange]) 
      

      self.table_nl_en_wordBased[phrasePairText].increaseOrientation(DirectionName.LEFT_TO_RIGHT,  dictWordsLR[phrasePairRange]) 
      self.table_nl_en_wordBased[phrasePairText].increaseOrientation(DirectionName.RIGHT_TO_LEFT,  dictWordsRL[phrasePairRange]) 
      
  # f ||| e ||| p1 p2 p3 p4 p5 p6 p7 p8
  def writePairToFile(self, ) :
    pair = (nl_phrase, en_phrase)
    delimiter = " ||| "

    f1.write(str(nl_phrase) + delimiter + str(en_phrase) + delimiter)

    f1.write(str(self.prob_nl_en[pair].phraseProb ))
    f1.write(" ")
    f1.write(str(self.prob_en_nl[pair].phraseProb ))
    f1.write(" ")
    f1.write(str(self.prob_nl_en[pair].lexicalProb ))
    f1.write(" ")
    f1.write(str(self.prob_en_nl[pair].lexicalProb ))

    f1.write(delimiter)

    f1.write(str(self.table_nl[nl_phrase]))
    f1.write(" ")
    f1.write(str(self.table_en[en_phrase]))
    f1.write(" ")
    f1.write(str(self.table_nl_en[pair].phrasePairCount))
    f1.write('\n')
  

  def getRangeAsText(self, list_sentence, start, end) :
    return self.getSubstring(list_sentence, range(start, end+1))


  # get the words in the word-list "line_list" that the indices
  # in "aligned_list" point to
  # return them as a string
  def getSubstring(self,line_list, aligned_list):
    wordList = map((lambda x : line_list[x]), aligned_list)
    return " ".join(wordList)

class ReorderingCalculator(object) :
  # do for ALL adjacent phrase pairs?
  # or just one?
  
  def phrase_lexical_reordering_left_right(self, phrase_pairs_indexes, len_e, len_f) :
    
    rangesToOrientation = {}
    
    start = [((-1,-1), (-1,-1))]
    end = [((len_f, len_f), (len_e,len_e))]

    phrase_pairs = start+phrase_pairs_indexes+end
    
    for i in range(0, len(phrase_pairs)-1):
      if phrase_pairs[i+1][1][0] == phrase_pairs[i][1][1] + 1 and phrase_pairs[i+1][0][0] == phrase_pairs[i][0][1] + 1 :
        print str(phrase_pairs[i]) +'\t'+ 'm'
        rangesToOrientation[phrase_pairs[i]] = Orientation.MONOTONE
      elif phrase_pairs[i+1][1][0] == phrase_pairs[i][1][1] + 1 and phrase_pairs[i+1][0][1] == phrase_pairs[i][0][0] - 1:
        print str(phrase_pairs[i])+'\t'+ 's'
        rangesToOrientation[phrase_pairs[i]] = Orientation.SWAP
      else :
        if phrase_pairs[i+1][0][1] > phrase_pairs[i][0][0]:
          print str(phrase_pairs[i])+'\t'+ 'd_r' 
          rangesToOrientation[phrase_pairs[i]] = Orientation.DISC_RIGHT
        else:
          print str(phrase_pairs[i])+'\t'+ 'd_r'
          rangesToOrientation[phrase_pairs[i]] = Orientation.DISC_LEFT
    
    return rangesToOrientation

  def phrase_lexical_reordering_right_left(self, phrase_pairs_indexes, len_e, len_f) :
    
    rangesToOrientation = {}
    
    start = [((-1,-1), (-1,-1))]
    end = [((len_f, len_f), (len_e, len_e))]

    phrase_pairs = start+phrase_pairs_indexes+end
    phrase_pairs.reverse()	

    for i in range(0, len(phrase_pairs)-1):
      if phrase_pairs[i+1][1][1] == phrase_pairs[i][1][0] - 1 and phrase_pairs[i+1][0][1] == phrase_pairs[i][0][0] - 1:
        print str(phrase_pairs[i]) +'\t'+ 'm'
        rangesToOrientation[phrase_pairs[i]] = Orientation.MONOTONE
      elif phrase_pairs[i+1][1][1] == phrase_pairs[i][1][0] - 1 and phrase_pairs[i+1][0][0] == phrase_pairs[i][0][1] + 1:
        print str(phrase_pairs[i]) + '\t' + 's'
        rangesToOrientation[phrase_pairs[i]] = Orientation.SWAP
      else:
        if phrase_pairs[i][0][1] > phrase_pairs[i+1][0][0]:
          print str(phrase_pairs[i])+'\t'+ 'd_l' #discontinuous to the left as we see from right to left
          rangesToOrientation[phrase_pairs[i]] = Orientation.DISC_LEFT
        else:
          print str(phrase_pairs[i])+'\t' + 'd_r'
          rangesToOrientation[phrase_pairs[i]] = Orientation.DISC_RIGHT

    return rangesToOrientation


  def word_lexical_reordering_left_right(self, phrase_pairs_indexes, alignments, len_e, len_f) :
    
    rangesToOrientation = {}
    
    start = [((-1,-1), (-1,-1))]
    end = [((len_f, len_f), (len_e,len_e))]
    
    #TODO: check whether this block is needed
    alignments[-1] = [-1]
    alignments[len_f] = [len_e]
    #####################

    phrase_pairs = start+phrase_pairs_indexes+end

    for i in range(0, len(phrase_pairs)-1):
      if self.alignment_exists(alignments, phrase_pairs[i][0][1] + 1, phrase_pairs[i][1][1] + 1):
        print str(phrase_pairs[i]) + '\t' + 'm'
        rangesToOrientation[phrase_pairs[i]] = Orientation.MONOTONE
        
      elif self.alignment_exists(alignments, phrase_pairs[i][0][0] -1, phrase_pairs[i][1][1] + 1):
        print str(phrase_pairs[i]) + '\t' + 's'
        rangesToOrientation[phrase_pairs[i]] = Orientation.SWAP
      else:
        if phrase_pairs[i+1][0][1] > phrase_pairs[i][0][0]:
          print str(phrase_pairs[i])+'\t'+ 'd_l' #discontinuous to the left as we see from left to right
          rangesToOrientation[phrase_pairs[i]] = Orientation.DISC_LEFT
        else:
          print str(phrase_pairs[i])+'\t'+ 'd_r'
          rangesToOrientation[phrase_pairs[i]] = Orientation.DISC_RIGHT
    
    return rangesToOrientation


  def word_lexical_reordering_right_left(self, phrase_pairs_indexes, alignments,  len_e, len_f):
    
    rangesToOrientation = {}
    
    start = [((-1,-1), (-1,-1))]
    end = [((len_f,len_f), (len_e,len_e))]
    
    #TODO: check whether this block is needed
    alignments[-1] = [-1]
    alignments[len_f] = [len_e]
    #####################

    phrase_pairs = start+phrase_pairs_indexes+end

    phrase_pairs.reverse()

    for i in range(0, len(phrase_pairs)-1):
      if self.alignment_exists(alignments, phrase_pairs[i][0][0] - 1, phrase_pairs[i][1][0] - 1):
        print str(phrase_pairs[i]) + '\t' + 'm'
        rangesToOrientation[phrase_pairs[i]] = Orientation.MONOTONE
      elif self.alignment_exists(alignments, phrase_pairs[i][0][1] +1, phrase_pairs[i][1][0] - 1):
        print str(phrase_pairs[i]) + '\t' + 's'
        rangesToOrientation[phrase_pairs[i]] = Orientation.SWAP
      else:
        if phrase_pairs[i][0][1] > phrase_pairs[i+1][0][0]:
          print str(phrase_pairs[i])+'\t'+ 'd_l' # discontinuous to the left as we see from left to right
          rangesToOrientation[phrase_pairs[i]] = Orientation.DISC_LEFT
        else:
          print str(phrase_pairs[i])+'\t'+ 'd_r'
          rangesToOrientation[phrase_pairs[i]] = Orientation.DISC_RIGHT
    
    return rangesToOrientation
  
  # the direction of the alignments should be the same as the direction of
  # the phrase pair ranges
  # e.g.
  # e_1 -> [f_2, f_4]
  # and
  # [((e_i, e_j), (f_k, f_m)), ... ]
  # in this case: other way around
  def alignment_exists(self,alignments, f_index,e_index):
    if f_index in alignments:
      if e_index in alignments[f_index]:
        return True
    return False



# reads a file line-by-line
class Reader(object):
  """
    read relevant data line-wise from files
  """
  inputFileName = "";

  aligns = ''
  nl = ''
  en = ''


  f_aligns = None
  f_nl = None
  f_en = None

  counter = 0

  line_list_aligns = None
  line_nl_words = None
  line_en_words = None

  def __init__(self, alignsFileName, nlFileName, enFileName):
    self.aligns = alignsFileName
    self.nl = nlFileName
    self.en = enFileName


  def load_data(self):
    #open the input files
    self.f_aligns = open(self.aligns)
    self.f_nl = open(self.nl)
    self.f_en = open(self.en)

    self.counter = 0

  #get the next line of each file
  def load_next_line(self):

    if (self.f_aligns == None):
      self.load_data()

    line_aligns = self.f_aligns.readline()
    line_nl = self.f_nl.readline()
    line_en = self.f_en.readline()


    if not line_aligns: #EOF
      sys.stdout.write('\nEnd of files reached\n')
      self.f_aligns.close()
      self.f_nl.close()
      self.f_en.close()
      self.line_list_aligns = None

    else:
      self.line_list_aligns = self.get_align_list(line_aligns)
      self.line_nl_words = self.get_words (line_nl)
      self.line_en_words = self.get_words (line_en)

      self.counter = self.counter+1

  def get_align_list(self, line):
    splitted = line.split()
    pairs = []
    for pair in splitted:
      pairList = pair.split('-')
      x = int(pairList[0])
      y = int(pairList[1])
      pairs.append((x,y))
    return pairs

  def get_words (self, line):
    return line.split()


def runTest():
  localDir = "/run/media/root/ss-ntfs/3.Documents/huiswerk_20132014/ALT/dutch-english/clean/"
  alignsFileName = localDir + "clean.aligned1"
  nlFileName = localDir + "clean.nl1"
  enFileName = localDir + "clean.en1"

  outputDir = "./output/"

  reader = Reader(alignsFileName, nlFileName, enFileName)
  extractorOfCounts = Extractor(reader, outputDir )
  extractorOfCounts.extract()


def run():
	parser = argparse.ArgumentParser(description = "Phrase extraction/probabilities")
	parser.add_argument('-a', '--alignments', help='Alignments filepath', required=True)
	parser.add_argument('-e', '--english', help='English sentences filepath', required=True)
	parser.add_argument('-f', '--foreign', help='Foreign sentences filepath', required=True)
	parser.add_argument('-o', '--output', help='Output folder', required=True)
	args = parser.parse_args()
	if not(args.alignments and args.english and args.foreign and args.output):
		print 'Error: Please provide the files required'

	alignsFileName = args.alignments
	nlFileName = args.foreign
	enFileName = args.english
	outputDir = args.output

	reader = Reader(alignsFileName, nlFileName, enFileName)
	extractorOfCounts = Extractor(reader, outputDir )

	extractorOfCounts.extract()



if __name__ == '__main__': #if this file is called by python
  run()


