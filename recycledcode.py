import sys
import os
import math
import cPickle as pickle
import gc
import itertools
import copy
import collections

table_nl_file = 'table_nl.dat'
table_en_file = 'table_en.dat'
table_nl_en_file = 'table_nl_en.dat'


writeRawFiles = True


MAXIMUM_READ_SENTENCES = 8 #10000 # for debug purposes

gc.disable()


# phrasePairTableEntry: used in the table table_nl_en
# that goes from (phrase_nl, phrase_en ) -> phrasePairTableEntry
# used because tuples don't support item-assignment,
# while lists can't be pickled
# class containing:
# ( <int> phrase-pair-count, 
#   <dict: list to int> align_list_nl_en -> count, 
#   <dict: list to int> align_list_en_nl -> count
# )
class PhrasePairTableEntry(object) :    
  def __init__(self, phrase_pair_count=0, dict_nl_lex=None, dict_en_lex=None):
    self.phrasePairCount = phrase_pair_count
    if (dict_nl_lex == None) :
      self.dictNlLex = collections.defaultdict(int)
    else :
      self.dictNlLex = dict_nl_lex # dutch to english lexical alignments
    if (dict_en_lex == None):
      self.dictEnLex = collections.defaultdict(int)
    else :
      self.dictEnLex = dict_en_lex # english to dutch lexical alignments
  
  def increasePhrasePairCount(self) :
    self.phrasePairCount += 1
  
  def addNlLexAlignment(self, alignment) :
    #print "adding alignment key %s to nlLexAlignment " % (alignment,)
    self.dictNlLex[alignment] += 1
    #print "%d keys has nlLexAlignment now " % len(self.dictNlLex.keys())
  
  def addEnLexAlignment(self, alignment):
    self.dictEnLex[alignment] += 1


class LexicalTableEntry (object) :
  
  def __init__(self, word_count_dict=None, total_count=0.0) :
    self.totalCount = total_count
    if (word_count_dict == None):
      self.wordCountDict = collections.defaultdict(float)
    else :
      self.wordCountDict = word_count_dict

  def addTargetWord(self, word, count) :
    self.wordCountDict[word] += count
    self.totalCount += count

  def getTranslationProb(self, word) :
    if (self.totalCount > 0):
      return float(self.wordCountDict[word]) / self.totalCount 
    else:
      return 0.0
      
  def printEntry(self):
    print "Total: %3.2f " % self.totalCount
    print "Words: "
    for targetWord, count in self.wordCountDict.iteritems():
      print "\t%s : %3.2f" % (targetWord, count)


class ConditionalTableEntry (object) :
  def __init__(self, phrase_prob=0.0, lexical_prob=0.0) :
    self.phraseProb = phrase_prob
    self.lexicalProb = lexical_prob
    
class Extractor(object):
  """
    extract phrases
    write tables to files
  """
  maxPhraseLen = 7

  def __init__(self, reader, tableDir ):
    self.reader = reader
    self.tablePath = os.path.abspath(tableDir) + '/'

    self.table_nl = collections.defaultdict(int)
    self.table_en = collections.defaultdict(int)
    self.table_nl_en = collections.defaultdict(PhrasePairTableEntry)

    self.table_nl_lex = collections.defaultdict(LexicalTableEntry) # nl -> en, p(en|nl)
    self.table_en_lex = collections.defaultdict(LexicalTableEntry) # en -> nl, p(nl|en)
    
    self.prob_nl_en = collections.defaultdict(ConditionalTableEntry) # nl | en
    self.prob_en_nl = collections.defaultdict(ConditionalTableEntry) # en | nl
    
    self.unique_nl = 0
    self.unique_en = 0
    self.unique_nl_en = 0

    self.total_extracted = 0


    if not os.path.exists(self.tablePath):
      os.makedirs(self.tablePath)


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

      
      # test for lexical probabilities      
      
      print " === table_nl_lex: ==="
      for key, value in self.table_nl_lex.iteritems():
        print "Word: %s" % key
        print "Targets:" 
        value.printEntry()
      
      print "=== table_en_lex: === "
      for key, value in self.table_en_lex.iteritems():
        print "Word: %s" % key
        print "Targets:" 
        value.printEntry()      
       
      print "p(wil|point):"
      print self.table_en_lex["point"].getTranslationProb("wil")

      print "p(point|wil):"
      print self.table_nl_lex["wil"].getTranslationProb("point")
      

      
  def get_most_frequent_alignment(self, alignments):
    maxV = 0
    best_alignment = None
    for alignment, count in alignments.iteritems():
      print "count: %d, alignment: %s" %  (count,(alignment,))
      if count > maxV :
        best_alignment = alignment
        
    
    return best_alignment
  
    
  #compute (log) lexical probability 
  def compute_lex_prob(self, nl, en, en_given_nl, best_alignment):
    
    (e,f) = (en, nl)
    if not en_given_nl:
      (e,f) = (nl, en) 
    
    print "sentence pair:\ne='%s'\nf='%s'\n" % (e, f)
    e_split = e.split()
    f_split = f.split()    
    len_e = len(e_split)
    
    lex_prob = 0.0
    
    best_alignment = best_alignment
    
    # for all e-side words
    for i in range (0, len_e):
      sub_prob = 0
      
      #every word must be aligned to at least one word
      aligned_indexes = best_alignment[i]
      
      print "aligned_indexes: %s" % (aligned_indexes,)
      print "%s aligned to %s" % (aligned_indexes[0],(aligned_indexes[1],))
      aligned_indexes_num = len(aligned_indexes[1])
      
      if aligned_indexes[0] == "NULL":
        en_word = "NULL"
      else :
        en_word = e_split[i] 
      print "nr. aligned indexes of i (%d, %s): %d" % (i, en_word, aligned_indexes_num)
      for j in aligned_indexes[1]:
        
        print "sub-alignment e->f: %s->%s" % (aligned_indexes[0], f_split[j])
        """#w(e|f) = c(e,f) / c(f)
        count_f = 0
        count_e_f = 0
        if en_given_nl:
          count_f = table_nl[f]
          count_e_f = table_nl_en[(f_split[j], e_split[i])][0]
        else:
          count_f = table_en[f]
          count_e_f = table_nl_en[(e_split[i], f_split[j])][0]]

        sub_prob += count_e_f / (float)count_f
        """
        #print "p(wil|point):"
        #print self.table_en_lex["point"].getTranslationProb("wil")
        if en_given_nl:
          sub_prob += self.table_nl_lex[f_split[j]].getTranslationProb(en_word)
          print "pr(%s|%s): %2.2f" % ( en_word, f_split[j], self.table_nl_lex[f_split[j]].getTranslationProb(en_word))
        else:
          self.table_en_lex[f_split[j]].printEntry()
          
          sub_prob += self.table_en_lex[f_split[j]].getTranslationProb(en_word)
          print "pr(%s|%s): %2.2f" % (en_word, f_split[j], self.table_en_lex[f_split[j]].getTranslationProb(en_word))
          
      sub_prob = math.log(sub_prob / float(aligned_indexes_num))
      lex_prob += sub_prob

    return lex_prob


  #en_given_nl = True if lex(en|nl, a), False otherwise
  def lexical_weighting(self, nl, en, en_given_nl):

    if en_given_nl:
      alignments = self.table_nl_en[(nl,en)].dictEnLex  # english to dutch lexical alignments
    else:
      alignments = self.table_nl_en[(nl,en)].dictNlLex  # dutch to english lexical alignments
      
    best_alignment = self.get_most_frequent_alignment(alignments)

    return self.compute_lex_prob(nl, en, en_given_nl, best_alignment)



  # check if both phrases consist of a sinlge word
  def is_length_one(self, nl, en):
    if " " not in nl and " " not in en:
      return True
    return False
  
  #compute lexical probabilites
  def compute_lexical_probabilities(self, nl, en):

    if self.is_length_one(nl, en):
      #lexical probability is directly from lexical w(en|nl) or w(nl|en) table
      lex_nl_en = self.table_en_lex[en].getTranslationProb(nl) # p(nl|en)
      lex_en_nl = self.table_nl_lex[nl].getTranslationProb(en)    
      
    else:
      lex_nl_en = self.lexical_weighting(nl, en,  en_given_nl=False)
      lex_en_nl = self.lexical_weighting(nl, en,  en_given_nl=True)
    
    return (lex_nl_en, lex_en_nl)
  
  
  # infers considition phrase and lexical probabilities from the frequency tables
  def normalizeTables(self):

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
      
      # get conditional (log) lexical weights/probabilities
      (lex_nl_en_prob, lex_en_nl_prob) = self.compute_lexical_probabilities(nl_phrase, en_phrase)
      
      self.prob_nl_en[pair].lexicalProb = lex_nl_en_prob
      self.prob_en_nl[pair].lexicalProb = lex_en_nl_prob
      
      # TODO: write to file here?
      
    """
    for nl, value in self.table_nl.iteritems():
      value_new = math.log(value) - math.log(self.total_extracted)
      self.table_nl[nl] = value_new

    for en, value in self.table_en.iteritems():
      value_new = math.log(value) - math.log(self.total_extracted)
      self.table_en[en] = value_new
    """
    

  def pickleTables(self):
    f1 = open( self.tablePath + table_nl_file, "wb" )
    f2 = open( self.tablePath +  table_en_file, "wb" )
    f3 = open( self.tablePath +  table_nl_en_file, "wb" )

    pickle.dump(self.table_nl, f1)
    pickle.dump(self.table_en, f2)
    pickle.dump(self.table_nl_en, f3)

    f1.close()
    f2.close()
    f3.close()


  def writeTables(self):

    f1 = open( self.tablePath +  table_nl_file[:-4] + '_raw.txt', "wb" );
    f2 = open( self.tablePath +  table_en_file[:-4] + '_raw.txt', "wb" );
    f3 = open( self.tablePath +  table_nl_en_file[:-4] + '_raw.txt', "wb" );


    for nl, value in self.table_nl.iteritems():
      f1.write(str(value) + ' : ' + str(nl) + '\n')
    for en, value in self.table_en.iteritems():
      f2.write(str(value) + ' : ' + str(en) + '\n')
    for pair, phrasePairTableEntry in self.table_nl_en.iteritems():      
      f3.write(str(phrasePairTableEntry.phrasePairCount) + ' : ' + str(pair) + ' ')
      f3.write('\n nl->en alignments: ')
      for alignment, count in phrasePairTableEntry.dictNlLex.iteritems() :       
        f3.write(str(alignment) + ': ' + str(count) + ' ')
      f3.write('\n en->nl alignments: ')
      for alignment, count in phrasePairTableEntry.dictEnLex.iteritems() :
        f3.write(str(alignment) + ': ' + str(count) + ' ')
      f3.write('\n')
    f1.close()
    f2.close()
    f3.close()

  # assume dutch word f_1 goes to english words e_1, e_2, e_3
  # then add 1/3 to table_en_lex[e_1][f_1] ( f_1 given e_1), 
  #     add 1/3 to table_en_lex[e_1][f_2] ( f_1 given e_2)
  # etc.
  # Then invoking table_en_lex.getTranslationProb(f_1)
  # p(f_1|e_1) will be (1/3) / 1 == 1/3
  def populateLexicalTable(self, source_lex_index, list_source, list_target, source_to_target_lex, table_target_lex) :
    target_words_indices = source_to_target_lex[source_lex_index]
    nr_target_words = len(target_words_indices)
    add_count = 1.0 / nr_target_words
    source_word = list_source[source_lex_index]
    
    for t_i in target_words_indices :
      if t_i == "NULL":
        t_word = "NULL"
      else :
        t_word = list_target[t_i]
      table_target_lex[t_word].addTargetWord(source_word, add_count)
  
  
  def populateLexicalTableNULL(self, target_words_indices,  list_target, table_target_lex) :
    
    add_count = 1
 
    
    for t_i in target_words_indices :
      if t_i == "NULL":
        t_word = "NULL"
      else :
        t_word = list_target[t_i]
      table_target_lex[t_word].addTargetWord("NULL", add_count)
        
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
    
    for lex_index in range(0, len_list_nl) :
      if nl_to_en_lex[lex_index] == [] :
        nl_to_en_lex[lex_index] = ["NULL"]
        #en_to_nl_lex["NULL"].append(lex_index)      
        nl_to_null.append(lex_index)
        
      self.populateLexicalTable(lex_index, list_nl, list_en, nl_to_en_lex, self.table_en_lex) # p(nl | en)
      
      

    for lex_index in range(0, len_list_en) :
      if en_to_nl_lex[lex_index] == [] :
        en_to_nl_lex[lex_index] = ["NULL"]
        #nl_to_en_lex["NULL"].append(lex_index)
        en_to_null.append(lex_index)
        
      self.populateLexicalTable(lex_index, list_en, list_nl, en_to_nl_lex, self.table_nl_lex) # p(en | nl)

    
   
    
    self.populateLexicalTableNULL( nl_to_null, list_nl, self.table_nl_lex) # p(NULL | nl)
    self.populateLexicalTableNULL( en_to_null, list_en, self.table_en_lex) # p(NULL | en)
    
    print nl_to_en
    print en_to_nl
    
    print nl_to_en_lex
    print en_to_nl_lex

    print ""

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
              nlFromEnMin = min(nlFromEnMin, en_to_nl[enRange[0]][0], en_to_nl[enRange[1]][0])
              nlFromEnMax = max(nlFromEnMax, en_to_nl[enRange[0]][1], en_to_nl[enRange[1]][1])

              # nl-to-en-to-nl range minimum is below nl-range minimum
              if nlFromEnMin < nl_index1:
                break

              # nl-to-en-to-nl range maximum is above nl-range maximum
              elif nlFromEnMax > nl_index2:
              # this is erroreous, you can't skip over nl_range without updating the nl_to_en range etc.
              #  print "nl_index1 is %s. going from nl_index2 %s to %s " % (nl_index1, nl_index2, nlFromEnMax)
                # next nl end-word is the one on the nl-to-en-to-nl range maximum (if within range)
             #   nl_index2 = nlFromEnMax
                if nl_index2 - nl_index1 >= self.maxPhraseLen :                  
                  break
              #  else :
              #    break

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
        
          
  # get relative lexical alignments
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
    
    #source_targets_tuples = [tuple(x) for xe in source_lex_list for x in xe]
    return source_lex_tuple
  
  
  
  def addPair(self, list_nl, list_en, start_nl, end_nl, start_en, end_en, en_to_nl_lex, nl_to_en_lex):
    self.total_extracted = self.total_extracted + 1

    # update tables
    nlEntry = self.getSubstring(list_nl, range(start_nl,end_nl+1))
    enEntry = self.getSubstring(list_en, range(start_en,end_en+1))
    nl_enEntry = (nlEntry , enEntry) #tuple


    nl_to_en_aligns = self.getLexicalAlignments(nl_to_en_lex, start_nl, end_nl, start_en, end_en) 
    en_to_nl_aligns = self.getLexicalAlignments(en_to_nl_lex, start_en, end_en, start_nl, end_nl) 

 
    print "nl entry: '%s', en entry: '%s' " % (nlEntry, enEntry)
    print "nl range: %s, en range: %s, lex list: %s " % ((start_nl, end_nl), (start_en, end_en), (nl_to_en_aligns,))
    print "en range: %s, nl range: %s, lex list: %s " % ((start_en, end_en), (start_nl, end_nl), (en_to_nl_aligns,))
    print ""

    self.updateTables(nlEntry, enEntry, nl_enEntry, nl_to_en_aligns, en_to_nl_aligns)

  # update the hash tables (phrase (pair) --> count)
  def updateTables(self, nlString, enString, nl_enString, nl_to_en_aligns, en_to_nl_aligns):

    if not (nlString in self.table_nl):
      self.unique_nl +=  1
    self.table_nl[nlString] = self.table_nl[nlString] + 1

    if not(enString in self.table_en):
      self.unique_en += 1
    self.table_en[enString] = self.table_en[enString] + 1

  
    if not(nl_enString in self.table_nl_en):
      self.unique_nl_en += 1

    self.table_nl_en[nl_enString].increasePhrasePairCount()
    
    self.table_nl_en[nl_enString].addNlLexAlignment(nl_to_en_aligns)
    self.table_nl_en[nl_enString].addEnLexAlignment(en_to_nl_aligns)
    
    
    if  nlString == "ik wil een motie":
      self.table_nl_en[nl_enString].increasePhrasePairCount()
      self.table_nl_en[nl_enString].addNlLexAlignment(nl_to_en_aligns)
      self.table_nl_en[nl_enString].addEnLexAlignment(en_to_nl_aligns)
      
    """for key, value in self.table_nl_en.iteritems():
      print key
      print value.phrasePairCount
      print value.dictNlLex
      print value.dictEnLex
      print ""
    """
    
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



def run():

  alignDir = '/run/media/root/ss-ntfs/3.Documents/huiswerk_20132014/ALT/ass1/dutch-english/clean/'
  alignsFileName = 'clean.aligned'
  nlFileName = 'clean.nl'
  enFileName = 'clean.en'

  tableDir = 'tables/'

  reader = Reader(alignDir, alignsFileName, nlFileName, enFileName)
  extractorOfCounts = Extractor(reader, tableDir )

  extractorOfCounts.extract()

  """
  phraseTables = PhraseTables(tableDir)
  initPhraseTables(self.phraseTables, alignDir, tableDir, alignsFileName, nlFileName, enFileName)


  # some example outputs
  sys.stdout.write( 'Pr(\"en\" , \"and\") = ' + str(self.phraseTables.getConditionalProbabilityNl('en', 'and', False)) + '\n')
  sys.stdout.write( 'Pr(\"universiteit\" , \"university\") = ' + str(self.phraseTables.getConditionalProbabilityNl('universiteit', 'university', False)) + '\n')
  sys.stdout.write( 'Pr(\"gebrek aan transparantie bij\" , \"lack of transparency in\") = ' + str(self.phraseTables.getConditionalProbabilityNl('gebrek aan transparantie bij', 'lack of transparency in', False)) + '\n')
  sys.stdout.write( 'Pr(\"economisch beleid\" , \"economic guidelines\") = ' + str(self.phraseTables.getConditionalProbabilityNl('economisch beleid', 'economic guidelines', False)) + '\n')

  """

if __name__ == '__main__': #if this file is called by python

  run()


