# ALT Assignment 2
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



MAXIMUM_READ_SENTENCES = 8 # for debug purposes

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
      raise ValueError("pass a Orientation")


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
      raise ValueError("pass a DirectionName")



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

  def increaseCount(self) :
    self.phrasePairCount += 1
    
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
  maxPhraseLen = 6 # should be one below the desired length...

  # smoothing factor when calculating probabilities
  smoothingFactor = 0.5

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
    self.directionLR_phraseBased = Direction()
    self.directionRL_phraseBased = Direction()

    self.directionLR_wordBased = Direction()
    self.directionRL_wordBased = Direction()
    
    self.len_nl_phraseBased = collections.defaultdict(PhrasePairTableEntry)
    self.len_en_phraseBased = collections.defaultdict(PhrasePairTableEntry)
    self.len_avg_phraseBased = collections.defaultdict(PhrasePairTableEntry)
    self.len_nl_wordBased = collections.defaultdict(PhrasePairTableEntry)
    self.len_en_wordBased = collections.defaultdict(PhrasePairTableEntry)
    self.len_avg_wordBased = collections.defaultdict(PhrasePairTableEntry)

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

      # print/write stats
      print self.getStats()
      self.writeStats()

      sys.stdout.write('Done extracting.\n')

      print "size table_nl_en_phraseBased: %d " % len(self.table_nl_en_phraseBased)
      print "size table_nl_en_wordBased: %d " % len(self.table_nl_en_wordBased)


      print "Calculating probabilities, writing them to file..."
      self.toProbsToFile(phraseBased=True)
      self.toProbsToFile(phraseBased=False)
      print "Done calculating/writing."



  def printPhrasePair(self,phrasePair) :

    print "phrasePair: %s" % (phrasePair,)

    if phrasePair in self.table_nl_en_phraseBased:
      te =  self.table_nl_en_phraseBased[phrasePair]
      teLR =  te.directionLR

      print "LR:"
      #print teLR.orientationsDict
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
  def writeStats(self) :
    f = open( self.tablePath+'/extraction_stats.txt', "wb" )
    f.write(self.getStats())
    f.close()



  def getStats(self):
    s = ''
    s += '\n'
    s += 'Extracted ' + str(self.total_extracted) + ' phrase pairs \n' + '\t unique pairs: ' + str(self.unique_nl_en) + '\n'
    s += 'Nr. orientations l->r pb: ' + str(self.directionLR_phraseBased.totalOrientations)  + '\n'
    s += 'Nr. orientations r->l pb: ' + str(self.directionRL_phraseBased.totalOrientations)  + '\n'
    s += 'Nr. orientations l->r wb: ' + str(self.directionLR_wordBased.totalOrientations)  + '\n'
    s += 'Nr. orientations r->l wb: ' + str(self.directionRL_wordBased.totalOrientations)  + '\n'
    
    s += '\n\nl->r monotone pb: ' + str(self.directionLR_phraseBased.orientationsDict[Orientation.MONOTONE])
    s += '\nl->r swap pb: ' + str(self.directionLR_phraseBased.orientationsDict[Orientation.SWAP])
    s += '\nl->r d_l pb: ' + str(self.directionLR_phraseBased.orientationsDict[Orientation.DISC_LEFT])
    s += '\nl->r d_r pb: ' + str(self.directionLR_phraseBased.orientationsDict[Orientation.DISC_RIGHT])
    s += '\n\nr->l monotone pb: ' + str(self.directionRL_phraseBased.orientationsDict[Orientation.MONOTONE])
    s += '\nr->l swap pb: ' + str(self.directionRL_phraseBased.orientationsDict[Orientation.SWAP])
    s += '\nr->l d_l pb: ' + str(self.directionRL_phraseBased.orientationsDict[Orientation.DISC_LEFT])
    s += '\nr->l d_r pb: ' + str(self.directionRL_phraseBased.orientationsDict[Orientation.DISC_RIGHT])
    
    s += '\n\n\nl->r monotone wb: ' + str(self.directionLR_wordBased.orientationsDict[Orientation.MONOTONE])
    s += '\nl->r swap wb: ' + str(self.directionLR_wordBased.orientationsDict[Orientation.SWAP])
    s += '\nl->r d_l wb: ' + str(self.directionLR_wordBased.orientationsDict[Orientation.DISC_LEFT])
    s += '\nl->r d_r wb: ' + str(self.directionLR_wordBased.orientationsDict[Orientation.DISC_RIGHT])
    s += '\n\nr->l monotone wb: ' + str(self.directionRL_wordBased.orientationsDict[Orientation.MONOTONE])
    s += '\nr->l swap wb: ' + str(self.directionRL_wordBased.orientationsDict[Orientation.SWAP])
    s += '\nr->l d_l wb: ' + str(self.directionRL_wordBased.orientationsDict[Orientation.DISC_LEFT])
    s += '\nr->l d_r wb: ' + str(self.directionRL_wordBased.orientationsDict[Orientation.DISC_RIGHT])
    
    s += '\n\n'
    
    s+= 'Dutch l->r per length (phrase-based):\n'
    for nl_length in self.len_nl_phraseBased.keys() :
      s += str(nl_length) + '\t'
      s += str(self.len_nl_phraseBased[nl_length].directionLR.totalOrientations)
      s += '\n'
    
    s+= '\n'
    s+= 'English l->r per length (phrase-based):\n'
    for en_length in self.len_en_phraseBased.keys() :
      s += str(en_length) + '\t'
      s += str(self.len_en_phraseBased[en_length].directionLR.totalOrientations)
      s += '\n'
      
    s+= '\n'
    s+= 'Dutch r->l per length (phrase-based):\n'
    for nl_length in self.len_nl_phraseBased.keys() :
      s += str(nl_length) + '\t'
      s += str(self.len_nl_phraseBased[nl_length].directionRL.totalOrientations)
      s += '\n'
    
    s+='\n'
    s+= 'English r->l per length (phrase-based):\n'
    for en_length in self.len_en_phraseBased.keys() :
      s += str(en_length) + '\t'
      s += str(self.len_en_phraseBased[en_length].directionRL.totalOrientations)
      s += '\n'
  
    s += '\n\n\n'
    
    s+= 'Dutch l->r per length (word-based):\n'
    for nl_length in self.len_nl_wordBased.keys() :
      s += str(nl_length) + '\t'
      s += str(self.len_nl_phraseBased[nl_length].directionLR.totalOrientations)
      s += '\n'
    
    s+= '\n'
    s+= 'English l->r per length (word-based):\n'
    for en_length in self.len_en_wordBased.keys() :
      s += str(en_length) + '\t'
      s += str(self.len_en_phraseBased[en_length].directionLR.totalOrientations)
      s += '\n'
      
    s+= '\n'
    s+= 'Dutch r->l per length (word-based):\n'
    for nl_length in self.len_nl_wordBased.keys() :
      s += str(nl_length) + '\t'
      s += str(self.len_nl_phraseBased[nl_length].directionRL.totalOrientations)
      s += '\n'
    
    s+='\n'
    s+= 'English r->l per length (word-based):\n'
    for en_length in self.len_en_wordBased.keys() :
      s += str(en_length) + '\t'
      s += str(self.len_en_phraseBased[en_length].directionRL.totalOrientations)
      s += '\n'
      
    return s

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


    for nl_index1 in range(0, len_list_nl): # do not check as start-word the period at the end

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


    # update phrase pair table counts
    # and global counts
    self.calcOrientationCounts(listOfPairsAsRanges, listOfPairsAsText, nl_to_en_lex, len_list_nl, len_list_en)

    # print pair
    """
    print listOfPairsAsText
    print ""
    print listOfPairsAsRanges
    print "\n"
    for phrasePair in listOfPairsAsText:
      self.printPhrasePair(phrasePair)
    """

  def updatePairStats (self, listOfPairsAsText, listOfPairsAsRanges, list_nl, list_en, start_nl, end_nl, start_en, end_en):
    listOfPairsAsText.append(( self.getRangeAsText(list_nl, start_nl,end_nl),
                               self.getRangeAsText(list_en, start_en, end_en)))
    listOfPairsAsRanges.append( ((start_nl, end_nl), (start_en, end_en)))

    return (listOfPairsAsText, listOfPairsAsRanges)

  def updateLengthStats(self, nlLen, enLen, d, o, phraseBased=True):
    
    if phraseBased:
      (len_nl, len_en, len_avg) = (self.len_nl_phraseBased, self.len_en_phraseBased, self.len_avg_phraseBased)
    else:
      (len_nl, len_en, len_avg) = (self.len_nl_wordBased, self.len_en_wordBased, self.len_avg_wordBased)
      
    len_nl[nlLen].increaseCount()
    len_nl[nlLen].increaseOrientation(d, o)
    len_en[enLen].increaseCount()
    len_en[enLen].increaseOrientation(d,o)
    len_avg[round((nlLen+enLen)/2.0)].increaseCount()
    len_avg[round((nlLen+enLen)/2.0)].increaseOrientation(d,o)
    
  def calcOrientationCounts(self, listOfPairsAsRanges, listOfPairsAsText, nl_to_en_alignments, len_nl, len_en) :

    rc = ReorderingCalculator()
    dictPhrasesLR = rc.phrase_lexical_reordering_left_right(listOfPairsAsRanges, len_en, len_nl)
    #print
    dictPhrasesRL = rc.phrase_lexical_reordering_right_left(listOfPairsAsRanges, len_en, len_nl)
    #print
    dictWordsLR = rc.word_lexical_reordering_left_right(listOfPairsAsRanges, nl_to_en_alignments, len_en, len_nl)
    #print
    dictWordsRL = rc.word_lexical_reordering_right_left(listOfPairsAsRanges, nl_to_en_alignments, len_en, len_nl)
    #print

    for i in range(0, len(listOfPairsAsRanges)) :
      phrasePairRange = listOfPairsAsRanges[i]
      phrasePairText = listOfPairsAsText[i]

      self.total_extracted += 1
      if not (phrasePairText in self.table_nl_en_phraseBased) :
        self.unique_nl_en += 1

      self.table_nl_en_phraseBased[phrasePairText].increaseCount()
      ## phrase-based

      nl = phrasePairText[0]
      nlLen =  len(nl.split())
      en = phrasePairText[1]
      enLen = len(en.split())
        
      for orientation in dictPhrasesLR[phrasePairRange]:
        # for pair
        self.table_nl_en_phraseBased[phrasePairText].increaseOrientation(DirectionName.LEFT_TO_RIGHT,  orientation)
        # for total
        self.directionLR_phraseBased.increaseOrientation(orientation)
        #length statistics
        if orientation != Orientation.MONOTONE:
          self.updateLengthStats(nlLen, enLen, DirectionName.LEFT_TO_RIGHT, orientation, phraseBased=True)
        
      for orientation in dictPhrasesRL[phrasePairRange]:
        #print Orientation.getString(orientation)
        self.table_nl_en_phraseBased[phrasePairText].increaseOrientation(DirectionName.RIGHT_TO_LEFT,  orientation)
        self.directionRL_phraseBased.increaseOrientation(orientation)
        
        if orientation != Orientation.MONOTONE:
          self.updateLengthStats(nlLen, enLen, DirectionName.RIGHT_TO_LEFT, orientation, phraseBased=True)
        
      ## word-based
      for orientation in dictWordsLR[phrasePairRange]:
        self.table_nl_en_wordBased[phrasePairText].increaseOrientation(DirectionName.LEFT_TO_RIGHT,  orientation)
        self.directionLR_wordBased.increaseOrientation(orientation)
        
        if orientation != Orientation.MONOTONE:
          self.updateLengthStats(nlLen, enLen, DirectionName.LEFT_TO_RIGHT, orientation, phraseBased=False)
        
      for orientation in dictWordsRL[phrasePairRange]:
        self.table_nl_en_wordBased[phrasePairText].increaseOrientation(DirectionName.RIGHT_TO_LEFT,  orientation)
        self.directionRL_wordBased.increaseOrientation(orientation)
        
        if orientation != Orientation.MONOTONE:
          self.updateLengthStats(nlLen, enLen, DirectionName.RIGHT_TO_LEFT, orientation, phraseBased=False)



  def calcProbability(self, pair, direction, orientation, phraseBased=True):


    if phraseBased :
      phraseTable = self.table_nl_en_phraseBased
      totalLR = self.directionLR_phraseBased
      totalRL = self.directionRL_phraseBased
    else:
      phraseTable = self.table_nl_en_wordBased
      totalLR = self.directionLR_wordBased
      totalRL = self.directionRL_wordBased

    if direction == DirectionName.LEFT_TO_RIGHT:

      totalCountForOrientation = totalLR.orientationsDict[orientation]
      totalCountAllOrientations = totalLR.totalOrientations
      probOrientation = float(totalCountForOrientation)/totalCountAllOrientations

      numerator = (self.smoothingFactor * probOrientation) + phraseTable[pair].directionLR.orientationsDict[orientation]
      denominator = self.smoothingFactor + phraseTable[pair].directionLR.totalOrientations


      normalProb = float(numerator)/denominator

      if numerator == 0:
        normalProb = sys.float_info.min
      return math.log(normalProb)

    elif direction == DirectionName.RIGHT_TO_LEFT:
      totalCountForOrientation = totalRL.orientationsDict[orientation]
      totalCountAllOrientations = totalRL.totalOrientations
      probOrientation = float(totalCountForOrientation)/totalCountAllOrientations

      numerator = (self.smoothingFactor * probOrientation) + phraseTable[pair].directionRL.orientationsDict[orientation]
      denominator = self.smoothingFactor + phraseTable[pair].directionRL.totalOrientations

      if denominator == 0:
        return 0
      return float(numerator)/denominator

    else :
      raise ValueError("Not a valid DirectionName")


  # f ||| e ||| p1 p2 p3 p4 p5 p6 p7 p8
    """
    where
     p1=p_l->r(m|(f; e))
     p2=p_l->r(s|(f; e))
     p3=p_l->r(dl|(f; e))
     p4=p_l->r(dr|(f; e))
     p5=p_r->l(m|(f; e))
     p6=p_r->l(s|(f; e))
     p7=p_r->l(dl|(f; e))
     p8=p_r->l(dr|(f; e))
  """
  def writePairToFile(self, f1, pair, phraseBased=True) :
    (nl_phrase, en_phrase) = pair
    delimiter = " ||| "

    # get probabilities
    p_LR_m = self.calcProbability(pair, DirectionName.LEFT_TO_RIGHT, Orientation.MONOTONE, phraseBased)
    p_LR_s = self.calcProbability(pair, DirectionName.LEFT_TO_RIGHT, Orientation.SWAP, phraseBased)
    p_LR_dl = self.calcProbability(pair, DirectionName.LEFT_TO_RIGHT, Orientation.DISC_LEFT, phraseBased)
    p_LR_dr = self.calcProbability(pair, DirectionName.LEFT_TO_RIGHT, Orientation.DISC_RIGHT, phraseBased)

    p_RL_m = self.calcProbability(pair, DirectionName.RIGHT_TO_LEFT, Orientation.MONOTONE, phraseBased)
    p_RL_s = self.calcProbability(pair, DirectionName.RIGHT_TO_LEFT, Orientation.SWAP, phraseBased)
    p_RL_dl = self.calcProbability(pair, DirectionName.RIGHT_TO_LEFT, Orientation.DISC_LEFT, phraseBased)
    p_RL_dr = self.calcProbability(pair, DirectionName.RIGHT_TO_LEFT, Orientation.DISC_RIGHT, phraseBased)

    # write to file
    f1.write(str(nl_phrase) + delimiter + str(en_phrase) + delimiter)

    # '%.4f' % (2.2352341234)
    f1.write(str(self.formatNr( p_LR_m)) + " " + str(self.formatNr(p_LR_s)) + " " + str(self.formatNr(p_LR_dl)) + " " + str(self.formatNr(p_LR_dr)))
    f1.write(" ")
    f1.write(str(self.formatNr(p_RL_m)) + " " + str(self.formatNr(p_RL_s)) + " " + str(self.formatNr(p_RL_dl)) + " " + str(self.formatNr(p_RL_dr)))

    f1.write('\n')


  def formatNr(self, nr) :
    return '%.4f' % nr

  def toProbsToFile(self, phraseBased=True):

    fileName = 'final_file'
    if phraseBased :
      fileName += '_phraseBased'
      phraseTable = self.table_nl_en_phraseBased
    else:
      fileName += '_wordBased'
      phraseTable = self.table_nl_en_wordBased
    fileName += '.txt'

    f1 = open( self.tablePath +  fileName, "wb" );

    # for each phrase pair in table
    for pair in phraseTable:

      self.writePairToFile(f1 , pair, phraseBased)
      
    f1.close()


  def getRangeAsText(self, list_sentence, start, end) :
    return self.getSubstring(list_sentence, range(start, end+1))


  # get the words in the word-list "line_list" that the indices
  # in "aligned_list" point to
  # return them as a string
  def getSubstring(self,line_list, aligned_list):
    wordList = map((lambda x : line_list[x]), aligned_list)
    return " ".join(wordList)

class ReorderingCalculator(object) :


  def get_next_pairs_lr(self,i, phrase_pairs):
    a = []
    for j in range(i+1, len(phrase_pairs)):
      if phrase_pairs[i][1][1] + 1 == phrase_pairs[j][1][0]:
        a.append(j)
    return a

  def get_next_pairs_rl(self,i, phrase_pairs):
    a = []
    for j in range(i+1, len(phrase_pairs)):
      if phrase_pairs[i][1][0] -1 == phrase_pairs[j][1][1]:
        a.append(j)
    return a

  def phrase_lexical_reordering_left_right(self, phrase_pairs_indexes, len_e, len_f) :

    rangesToOrientation = collections.defaultdict(tuple)

    start = [((-1,-1), (-1,-1))]
    end = [((len_f, len_f), (len_e,len_e))]

    phrase_pairs = start+phrase_pairs_indexes+end

    for i in range(0, len(phrase_pairs)-1):
      next_phrase_pairs = self.get_next_pairs_lr(i, phrase_pairs)
      for j in range(0, len(next_phrase_pairs)):
        k = next_phrase_pairs[j]
        if phrase_pairs[k][1][0] == phrase_pairs[i][1][1] + 1 and phrase_pairs[k][0][0] == phrase_pairs[i][0][1] + 1 :
          #print str(phrase_pairs[i]) +'\t'+ 'm'
          rangesToOrientation[phrase_pairs[i]] += ( Orientation.MONOTONE,)
        elif phrase_pairs[k][1][0] == phrase_pairs[i][1][1] + 1 and phrase_pairs[k][0][1] == phrase_pairs[i][0][0] - 1:
          #print str(phrase_pairs[i])+'\t'+ 's'
          rangesToOrientation[phrase_pairs[i]] += ( Orientation.SWAP,)
        else :
          if phrase_pairs[k][0][1] > phrase_pairs[i][0][0]:
            #print str(phrase_pairs[i])+'\t'+ 'd_r'
            rangesToOrientation[phrase_pairs[i]] += (Orientation.DISC_LEFT,)
          else:
            #print str(phrase_pairs[i])+'\t'+ 'd_l'
            rangesToOrientation[phrase_pairs[i]] += (Orientation.DISC_RIGHT,)


    return rangesToOrientation

  def phrase_lexical_reordering_right_left(self, phrase_pairs_indexes, len_e, len_f) :

    rangesToOrientation = collections.defaultdict(tuple)

    start = [((-1,-1), (-1,-1))]
    end = [((len_f, len_f), (len_e, len_e))]

    phrase_pairs = start+phrase_pairs_indexes+end
    phrase_pairs.reverse()

    for i in range(0, len(phrase_pairs)-1):
      next_phrase_pairs = self.get_next_pairs_rl(i, phrase_pairs)
      for j in range(0, len(next_phrase_pairs)):
        k = next_phrase_pairs[j]
        if phrase_pairs[k][1][1] == phrase_pairs[i][1][0] - 1 and phrase_pairs[k][0][1] == phrase_pairs[i][0][0] - 1:
          #print str(phrase_pairs[i]) +'\t'+ 'm'
          rangesToOrientation[phrase_pairs[i]] += (Orientation.MONOTONE,)
        elif phrase_pairs[k][1][1] == phrase_pairs[i][1][0] - 1 and phrase_pairs[k][0][0] == phrase_pairs[i][0][1] + 1:
          #print str(phrase_pairs[i]) + '\t' + 's'
          rangesToOrientation[phrase_pairs[i]] += (Orientation.SWAP,)
        else:
          if phrase_pairs[i][0][1] > phrase_pairs[k][0][0]:
            #print str(phrase_pairs[i])+'\t'+ 'd_l'
            rangesToOrientation[phrase_pairs[i]] += (Orientation.DISC_LEFT,)
          else:
            #print str(phrase_pairs[i])+'\t' + 'd_r'
            rangesToOrientation[phrase_pairs[i]] += (Orientation.DISC_RIGHT,)


    return rangesToOrientation


  def word_lexical_reordering_left_right(self, phrase_pairs_indexes, alignments, len_e, len_f) :

    rangesToOrientation = collections.defaultdict(tuple)

    start = [((-1,-1), (-1,-1))]
    end = [((len_f, len_f), (len_e,len_e))]

    #TODO: check whether this block is needed
    alignments[-1] = [-1]
    alignments[len_f] = [len_e]
    #####################

    phrase_pairs = start+phrase_pairs_indexes+end

    for i in range(0, len(phrase_pairs)-1):
      if self.alignment_exists(alignments, phrase_pairs[i][0][1] + 1, phrase_pairs[i][1][1] + 1):
        #print str(phrase_pairs[i]) + '\t' + 'm'
        rangesToOrientation[phrase_pairs[i]] += (Orientation.MONOTONE,)

      elif self.alignment_exists(alignments, phrase_pairs[i][0][0] -1, phrase_pairs[i][1][1] + 1):
        #print str(phrase_pairs[i]) + '\t' + 's'
        rangesToOrientation[phrase_pairs[i]] += (Orientation.SWAP,)
      else:
        if phrase_pairs[i+1][0][1] > phrase_pairs[i][0][0]:
          #print str(phrase_pairs[i])+'\t'+ 'd_l' #discontinuous to the left as we see from left to right
          rangesToOrientation[phrase_pairs[i]] += (Orientation.DISC_LEFT,)
        else:
          #print str(phrase_pairs[i])+'\t'+ 'd_r'
          rangesToOrientation[phrase_pairs[i]] += (Orientation.DISC_RIGHT,)

    return rangesToOrientation


  def word_lexical_reordering_right_left(self, phrase_pairs_indexes, alignments,  len_e, len_f):

    rangesToOrientation = collections.defaultdict(tuple)

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
        #print str(phrase_pairs[i]) + '\t' + 'm'
        rangesToOrientation[phrase_pairs[i]] += (Orientation.MONOTONE,)
      elif self.alignment_exists(alignments, phrase_pairs[i][0][1] +1, phrase_pairs[i][1][0] - 1):
        #print str(phrase_pairs[i]) + '\t' + 's'
        rangesToOrientation[phrase_pairs[i]] += (Orientation.SWAP,)
      else:
        if phrase_pairs[i][0][1] > phrase_pairs[i+1][0][0]:
          #print str(phrase_pairs[i])+'\t'+ 'd_l' # discontinuous to the left as we see from left to right
          rangesToOrientation[phrase_pairs[i]] += (Orientation.DISC_LEFT,)
        else:
          #print str(phrase_pairs[i])+'\t'+ 'd_r'
          rangesToOrientation[phrase_pairs[i]]+=(Orientation.DISC_RIGHT,)

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
  alignsFileName = localDir + "clean.aligned"
  nlFileName = localDir + "clean.nl"
  enFileName = localDir + "clean.en"

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
  runTest()


