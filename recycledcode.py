import sys
import os
import math
import cPickle as pickle
import gc
import itertools
import copy

table_nl_file = 'table_nl.dat'
table_en_file = 'table_en.dat'
table_nl_en_file = 'table_nl_en.dat'


basicDebug = True
moreDebug = False
writeRawFiles = True


MAXIMUM_READ_SENTENCES = 1000000 #10000 # for debug purposes

gc.disable() 


class Extractor(object):
  """
    extract phrases
    write tables to files
  """
  maxPhraseLen = 4

  def __init__(self, reader, tablePath ):
    self.reader = reader
    self.tablePath = tablePath

    self.table_nl = {}
    self.table_en = {}
    self.table_nl_en = {}

    self.unique_nl = 0
    self.unique_en = 0
    self.unique_nl_en = 0

    self.total_extracted = 0


    if not os.path.exists(tablePath):
      os.makedirs(tablePath)


  # extract phrases for all sentence pairs  (provided by the "Reader")
  def extract(self):
      self.reader.line_list_aligns = "Meaningless init value because python has no do..while"
      while (self.reader.line_list_aligns != None and self.reader.counter < MAXIMUM_READ_SENTENCES): # the fixed limit is only for debug
        if basicDebug:
          if (self.reader.counter > 0 and self.reader.counter % 500 == 0):
            sys.stdout.write('Reached line ' + str(self.reader.counter) + ' \n')
        self.reader.load_next_line()
        if (self.reader.line_list_aligns != None):
          # parse phrases using  the dutch sentence, the english sentence and their alignments-list
          self.parseSentencePair(self.reader.line_list_aligns, self.reader.line_nl_words, self.reader.line_en_words)

      # print stats
      sys.stdout.write('\n')
      sys.stdout.write('Extracted ' + str(self.total_extracted) + ' phrase pairs \n' +
                        '\t unique phrases for nl: ' + str(self.unique_nl) + '\n'+
                        '\t unique phrases for en: ' + str(self.unique_en) + '\n'+
                        '\t unique pairs: ' + str(self.unique_nl_en) + '\n')

      # write stats to file
      f = open( 'extraction_stats.txt', "a+b" )
      f.write('Extracted ' + str(self.total_extracted) + ' phrase pairs  from tables in' + str(self.tablePath) + '\n' 
              '\t unique phrases for nl: ' + str(self.unique_nl) + '\n'+
              '\t unique phrases for en: ' + str(self.unique_en) + '\n'+
              '\t unique pairs: ' + str(self.unique_nl_en) + '\n\n')
      f.close()
      
      sys.stdout.write('Writing to files...\n')

      self.normalizeTables() #make probabilities of the counts
      self.pickleTables()

      if writeRawFiles:
        self.writeTables()

      sys.stdout.write('Done writing to files.\n')



  def normalizeTables(self):

    for pair, value in self.table_nl_en.iteritems():
      value_new = math.log(value) - math.log(self.total_extracted)
      self.table_nl_en[pair] = value_new

    for nl, value in self.table_nl.iteritems():
      value_new = math.log(value) - math.log(self.total_extracted)
      self.table_nl[nl] = value_new

    for en, value in self.table_en.iteritems():
      value_new = math.log(value) - math.log(self.total_extracted)
      self.table_en[en] = value_new



  def pickleTables(self):
    f1 = open( self.tablePath + table_nl_file, "wb" )
    f2 = open( self.tablePath +  table_en_file, "wb" )
    f3 = open( self.tablePath +  table_nl_en_file, "wb" )

    pickle.dump(self.table_nl, f1)
    if basicDebug:
        sys.stdout.write(table_nl_file + ' pickled.\n')
    pickle.dump(self.table_en, f2)
    if basicDebug:
        sys.stdout.write(table_en_file + ' pickled.\n')
    pickle.dump(self.table_nl_en, f3)
    if basicDebug:
        sys.stdout.write(table_nl_en_file + ' pickled.\n')

    f1.close()
    f2.close()
    f3.close()


  def writeTables(self):

    f1 = open( self.tablePath +  table_nl_file[:-4] + '_raw.txt', "wb" );
    f2 = open( self.tablePath +  table_en_file[:-4] + '_raw.txt', "wb" );
    f3 = open( self.tablePath +  table_nl_en_file[:-4] + '_raw.txt', "wb" );


    for nl, value in self.table_nl.iteritems():
      f1.write(str(value) + ' : ' + str(nl) + '\n')
    if basicDebug:
        sys.stdout.write(table_nl_file[:-4] + '_raw.txt' + ' written.\n')
    for en, value in self.table_en.iteritems():
      f2.write(str(value) + ' : ' + str(en) + '\n')
    if basicDebug:
        sys.stdout.write(table_en_file[:-4] + '_raw.txt' + ' written.\n')
    for pair, value in self.table_nl_en.iteritems():
      f3.write(str(value) + ' : ' + str(pair) + '\n')
    if basicDebug:
        sys.stdout.write(table_nl_en_file[:-4] + '_raw.txt' + ' written.\n')

    f1.close()
    f2.close()
    f3.close()


  #extract phrases from one sentence pair
  # used in Extractor.extract()
  def parseSentencePair(self, alignments, list_nl, list_en):

    if moreDebug:
      sys.stdout.write('\n pair '+ str(self.reader.counter-1) + ':\n')
      print alignments
      print list_nl
      print list_en

    totalExtractedThisPhrase = 0

    len_list_nl = len(list_nl)
    len_list_en = len(list_en)
    len_alignments = len(alignments)

    nl_to_en = [[100, -1] for i in range(len_list_nl)] #coverage range: [minimum, maximum]
    en_to_nl = [[100, -1] for i in range(len_list_en)]

    #print nl_to_en

    for a_pair in alignments:
      #print a_pair

      nl_index = a_pair[0]
      en_index = a_pair[1]
     
      nl_to_en[nl_index][0] = min(en_index, nl_to_en[nl_index][0])
      nl_to_en[nl_index][1] = max(en_index, nl_to_en[nl_index][1])

      en_to_nl[en_index][0] = min(nl_index, en_to_nl[en_index][0])
      en_to_nl[en_index][1] = max(nl_index, en_to_nl[en_index][1])


    if moreDebug:
      print nl_to_en
      print en_to_nl


    for nl_index1 in range(0, len_list_nl-1): # do not check as start-word the period at the end
      if moreDebug:
        sys.stdout.write('nl_index1: ' + str(nl_index1) + '\n')


      enRange = nl_to_en[nl_index1]

      if (enRange != [100, -1]): #if nl start-word is aligned

        nlFromEnMin = min(en_to_nl[enRange[0]][0], en_to_nl[enRange[1]][0])
        nlFromEnMax = max(en_to_nl[enRange[0]][1], en_to_nl[enRange[1]][1])

        nl_index2 = nl_index1
        while(nl_index2 < min(nl_index1 + self.maxPhraseLen, len_list_nl)):
          if moreDebug:
            sys.stdout.write('\tnl_index2: ' + str(nl_index2) + ', ')
            sys.stdout.write('\tchecking: ' + self.getSubstring(list_nl, range(nl_index1, nl_index2+1)) + '\n')

          enRangeThisIndex = nl_to_en[nl_index2]


          if (enRangeThisIndex != [100, -1]): #if nl end-word is aligned
            # update the nl-to-en range
            enRange = [min(enRange[0], enRangeThisIndex[0]), max(enRange[1], enRangeThisIndex[1])]

            if (enRange[1] - enRange[0] < self.maxPhraseLen):
              # update the nl-to-en-to-nl range
              nlFromEnMin = min(nlFromEnMin, en_to_nl[enRange[0]][0], en_to_nl[enRange[1]][0])
              nlFromEnMax = max(nlFromEnMax, en_to_nl[enRange[0]][1], en_to_nl[enRange[1]][1])

              # nl-to-en-to-nl range minimum is below nl-range minimum
              if nlFromEnMin < nl_index1:
                if moreDebug:
                  sys.stdout.write('\tnlFromEnMin < nl_index1: ' + str(nlFromEnMin) + ' < ' + str(nl_index1) + '\n')
                break

              # nl-to-en-to-nl range maximum is above nl-range maximum
              elif nlFromEnMax > nl_index2:
                if moreDebug:
                  sys.stdout.write('\tnlFromEnMax > nl_index2: ' + str(nlFromEnMax) + ' > ' + str(nl_index2) + '\n')
                # next nl end-word is the one on the nl-to-en-to-nl range maximum (if within range)
                nl_index2 = nlFromEnMax
                if nl_index2 - nl_index1 < self.maxPhraseLen :
                  continue
                else :
                  break

              # nl-to-en-to-nl range is same as nl-to-en range: got consistent pair
              elif [nl_index1, nl_index2] == [nlFromEnMin, nlFromEnMax] :
                if moreDebug:
                  sys.stdout.write ('\t' + str([nl_index1, nl_index2]) + ' == ' + str([nlFromEnMin, nlFromEnMax]) + '\n')
                  sys.stdout.write ('\t'+ self.getSubstring(list_nl, range(nl_index1, nl_index2+1)) + ' == ')
                  sys.stdout.write ( self.getSubstring(list_en, range(enRange[0], enRange[1]+1)) + '\n')


                self.addPair(list_nl, list_en, nl_index1, nl_index2, enRange[0], enRange[1])
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

                if moreDebug:
                  sys.stdout.write('\tunaligned nl list: ' + str(nl_unaligned_list) + '\n')
                  sys.stdout.write('\tunaligned en list: ' + str(en_unaligned_list) + '\n')

                # add unaligned nl's for current english phrase
                for unaligned_nl in nl_unaligned_list :
                  self.addPair(list_nl, list_en, unaligned_nl[0], unaligned_nl[1], enRange[0], enRange[1])
                  totalExtractedThisPhrase += 1
                # add unaligned en's for current dutch phrase
                for unaligned_en in en_unaligned_list :
                  self.addPair(list_nl, list_en, nl_index1, nl_index2, unaligned_en[0], unaligned_en[1])
                  totalExtractedThisPhrase += 1
                  # add unaliged nl / unaligned en combi's
                  for unaligned_nl in nl_unaligned_list :
                    self.addPair(list_nl, list_en, unaligned_nl[0], unaligned_nl[1], unaligned_en[0], unaligned_en[1])
                    totalExtractedThisPhrase += 1


              else : #it wasn't a consistent phrase pair
                if moreDebug:
                  sys.stdout.write ('\t' + str([nl_index1, nl_index2]) + ' != ' + str([nlFromEnMin, nlFromEnMax]) + '\n')
                  sys.stdout.write ('\t'+ self.getSubstring(list_nl, range(nl_index1, nl_index2+1)) + ' != ' )
                  sys.stdout.write ( self.getSubstring(list_en, range(enRange[0], enRange[1]+1)) + '\n')

            else:
              if moreDebug:
                sys.stdout.write ('\t too long: ' + self.getSubstring(list_en, range(enRange[0], enRange[1]+1)) + '\n')
              break

          else:
            if moreDebug:
              sys.stdout.write('\t ' + str(nl_index2) + ' is unaligned\n')

          if moreDebug:
            sys.stdout.write('we have extracted ' + str(totalExtractedThisPhrase) + ' phrase pairs \n')

          nl_index2 +=1


    # makes little sense
    # if the decoder makes sense
    #self.addPeriod()




  def addPeriod(self):
    self.total_extracted = self.total_extracted + 1

    # update tables
    nlEntry = '.'
    enEntry = '.'
    nl_enEntry = ('.' , '.') #tuple

    self.updateTables(nlEntry, enEntry, nl_enEntry)

  def addPair(self, list_nl, list_en, start_nl, end_nl, start_en, end_en):
    self.total_extracted = self.total_extracted + 1

    # update tables
    nlEntry = self.getSubstring(list_nl, range(start_nl,end_nl+1))
    enEntry = self.getSubstring(list_en, range(start_en,end_en+1))
    nl_enEntry = (nlEntry , enEntry) #tuple

    self.updateTables(nlEntry, enEntry, nl_enEntry)

  # update the hash tables (phrase (pair) --> count)
  def updateTables(self, nlString, enString, nl_enString):

    if nlString in self.table_nl:
      self.table_nl[nlString] = self.table_nl[nlString] + 1
    else:
      self.table_nl[nlString] = 1
      self.unique_nl = self.unique_nl + 1

    if enString in self.table_en:
      self.table_en[enString] = self.table_en[enString] + 1
    else:
      self.table_en[enString] = 1
      self.unique_en = self.unique_en + 1

    if nl_enString in self.table_nl_en:
      self.table_nl_en[nl_enString] = self.table_nl_en[nl_enString] + 1
    else:
      self.table_nl_en[nl_enString] = 1
      self.unique_nl_en = self.unique_nl_en + 1



  # get the words in the word-list "line_list" that the indices
  # in "aligned_list" point to
  # return them as a string
  def getSubstring(self,line_list, aligned_list):
    wordList = map((lambda x : line_list[x]), aligned_list)
    return " ".join(wordList)




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

  def __init__(self, path, alignsFileName, nlFileName, enFileName):
    self.aligns = path+alignsFileName
    self.nl = path+nlFileName
    self.en = path+enFileName


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
