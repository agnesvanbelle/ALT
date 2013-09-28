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

class DirectionName :
  LEFT_TO_RIGHT = 0
  RIGHT_TO_LEFT = 1

# class containing:
#   - a dict from Orientation -> count
#   - a total count (over all Orientations)
class Direction (object):
  
  def __init__(self, orientations_dict=None, total_orientations=0):
    self.totalOrientations = total_orientations
    
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
  maxPhraseLen = 7

  def __init__(self, reader, outputDir ):
    self.reader = reader
    self.tablePath = os.path.abspath(outputDir) + '/'

    self.table_nl = collections.defaultdict(int)
    self.table_en = collections.defaultdict(int)
    self.table_nl_en = collections.defaultdict(PhrasePairTableEntry)


    self.unique_nl = 0
    self.unique_en = 0
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
      self.writeStatsToFile()
      
      sys.stdout.write('Computing probabilities and writing to files...\n')

      # infer probabilities from the counts, 
      # phrase-translation prob.s as well as lexical prob.s
      self.normalizeTables()
      
   

      sys.stdout.write('Done .\n')

  # print stats
  def printStats(self) :
    sys.stdout.write('\n')
    sys.stdout.write('Extracted ' + str(self.total_extracted) + ' phrase pairs \n' +
                      '\t unique phrases for nl: ' + str(self.unique_nl) + '\n'+
                      '\t unique phrases for en: ' + str(self.unique_en) + '\n'+
                      '\t unique pairs: ' + str(self.unique_nl_en) + '\n' ) 
                      
    
  # write stats to file
  def writeStatsToFile(self) :
    f = open( self.tablePath+'/extraction_stats.txt', "a+b" )
    f.write('Extracted ' + str(self.total_extracted) + ' phrase pairs  from tables in' + str(self.tablePath) + '\n'
            '\t unique phrases for nl: ' + str(self.unique_nl) + '\n'+
            '\t unique phrases for en: ' + str(self.unique_en) + '\n'+
            '\t unique pairs: ' + str(self.unique_nl_en) + '\n'  )
    f.close()

  
  """
  # write everything to a file in format
  #  f ||| e ||| p(f|e) p(e|f) l(f|e) l(e|f) ||| freq(f) freq(e) freq(f,e) 
  def writeToFile(self, f1, nl_phrase, en_phrase) :
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
  """
  
  # infers considition phrase and lexical probabilities from the frequency tables
  def normalizeTables(self):
    
    f1 = open( self.tablePath +  'final_file.txt', "wb" );

    # for each phrase pair in frequency+alignments table
    for pair, phrasePairTableEntry in self.table_nl_en.iteritems():
      
      # convert frequencies to joint and single (log) probabilities 
      joint_log_prob = math.log(phrasePairTableEntry.phrasePairCount) - \
                                              math.log(self.total_extracted)
      
      nl_phrase = pair[0]
      en_phrase = pair[1]      
      
      nl_phrase_log_prob = math.log(self.table_nl[nl_phrase]) - math.log(self.total_extracted)
      en_phrase_log_prob = math.log(self.table_en[en_phrase]) - math.log(self.total_extracted)
      
      # put conditional (log) phrase probabilities in conditional probability table
      self.prob_nl_en[pair].phraseProb = joint_log_prob - en_phrase_log_prob # p (nl | en)
      self.prob_en_nl[pair].phraseProb = joint_log_prob - nl_phrase_log_prob # p (en | nl)
      
    
      #self.writeToFile(f1, nl_phrase, en_phrase)
    
    f1.close()  
 
    

  
  
  #extract phrases from one sentence pair
  # used in Extractor.extract()
  def parseSentencePair(self, alignments, list_nl, list_en):
    
    totalExtractedThisPhrase = 0


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


                self.addPair(list_nl, list_en, nl_index1, nl_index2, enRange[0], enRange[1], en_to_nl_lex, nl_to_en_lex)
                totalExtractedThisPhrase += 1


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
                  self.addPair(list_nl, list_en, unaligned_nl[0], unaligned_nl[1], enRange[0], enRange[1], en_to_nl_lex, nl_to_en_lex)
                  totalExtractedThisPhrase += 1
                # add unaligned en's for current dutch phrase
                for unaligned_en in en_unaligned_list :
                  self.addPair(list_nl, list_en, nl_index1, nl_index2, unaligned_en[0], unaligned_en[1], en_to_nl_lex, nl_to_en_lex)
                  totalExtractedThisPhrase += 1
                  # add unaliged nl / unaligned en combi's
                  for unaligned_nl in nl_unaligned_list :
                    self.addPair(list_nl, list_en, unaligned_nl[0], unaligned_nl[1], unaligned_en[0], unaligned_en[1], en_to_nl_lex, nl_to_en_lex)
                    totalExtractedThisPhrase += 1



            else:
              break



          nl_index2 +=1
        
    # TODO: calculate phrase based probs here
    
  
  # get relative (for phrase pair) lexical alignments
  def getLexicalAlignments(self, source_to_target_lex, start_source, end_source, start_target, end_target) :
    source_lex_list = []
    source_to_target_total = []
    relative_lex_index = 0
    
    for lex_index in range(start_source, end_source+1) :
      
      target_indices = source_to_target_lex[lex_index]
      if target_indices != ["NULL"]:
        target_indices =  map( lambda x : x - (start_target), source_to_target_lex[lex_index])
        source_to_target_total.extend( target_indices)      
        lex_tuple = (relative_lex_index, tuple(target_indices))  
      else :
        lex_tuple = (relative_lex_index, ("NULL",)) 
        
      source_lex_list.append(lex_tuple)
      relative_lex_index = relative_lex_index + 1    
    
    source_lex_tuple = tuple(source_lex_list)

    # add NULL -> ...
    null_to_target = [x for x in range(0, (end_target-start_target)+1) if x not in source_to_target_total] 
    if null_to_target != []:
      source_lex_tuple = tuple(itertools.chain((("NULL", tuple(null_to_target)),), source_lex_tuple))
    
    return source_lex_tuple
  
  
  # add the found subphrase and its relevant information to relevant dictionaries
  def addPair(self, list_nl, list_en, start_nl, end_nl, start_en, end_en, en_to_nl_lex, nl_to_en_lex):
    self.total_extracted = self.total_extracted + 1

    # update tables
    nlEntry = self.getSubstring(list_nl, range(start_nl,end_nl+1))
    enEntry = self.getSubstring(list_en, range(start_en,end_en+1))
    nl_enEntry = (nlEntry , enEntry) #tuple

    nl_to_en_aligns = self.getLexicalAlignments(nl_to_en_lex, start_nl, end_nl, start_en, end_en) 
    en_to_nl_aligns = self.getLexicalAlignments(en_to_nl_lex, start_en, end_en, start_nl, end_nl) 
    
    
    self.updateTables(nlEntry, enEntry, nl_enEntry, nl_to_en_aligns, en_to_nl_aligns)



  # update the dictionaries
  def updateTables(self, nlString, enString, nl_enString, nl_to_en_aligns, en_to_nl_aligns):

    if not (nlString in self.table_nl):
      self.unique_nl +=  1
    self.table_nl[nlString] = self.table_nl[nlString] + 1

    if not(enString in self.table_en):
      self.unique_en += 1
    self.table_en[enString] = self.table_en[enString] + 1
  
    if not(nl_enString in self.table_nl_en):
      self.unique_nl_en += 1

      

  # get the words in the word-list "line_list" that the indices
  # in "aligned_list" point to
  # return them as a string
  def getSubstring(self,line_list, aligned_list):
    wordList = map((lambda x : line_list[x]), aligned_list)
    return " ".join(wordList)



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
  run()


