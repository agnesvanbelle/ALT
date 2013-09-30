

phrase_pairs_indexes = [((0, 0), (0, 0)), ((1,1), (1, 1)), ((4, 4), (2,2)), ((2,3),(3,4)), ((5,5),(5,5))]

#given alignments in the following format:
	# 0:[0,1]
	# 1:[2]
	# 2:[3,4]
# from f to e
alignments = {0: [0], 1: [1], 2: [4], 3: [3], 4: [2], 5: [5]}

def alignment_exists(alignments, f_index,e_index):
	if f_index in alignments:
		if e_index in alignments[f_index]:
			return True
	return False

def word_lexical_reordering_left_right(phrase_pairs_indexes, alignments, n) :
	start = [((-1,-1), (-1,-1))]
	end = [((n,n), (n,n))]
	
	#TODO: check whether this block is needed
	alignments[-1] = [-1]
	alignments[n] = [n]
	#####################

	phrase_pairs = start+phrase_pairs_indexes+end

	for i in range(0, len(phrase_pairs)-1):
		if alignment_exists(alignments, phrase_pairs[i][0][1] + 1, phrase_pairs[i][1][1] + 1):
			print str(phrase_pairs[i]) + '\t' + 'm'
		elif alignment_exists(alignments, phrase_pairs[i][0][0] -1, phrase_pairs[i][1][1] + 1):
			print str(phrase_pairs[i]) + '\t' + 's'
		else:
			if phrase_pairs[i+1][0][1] > phrase_pairs[i][0][0]:
				print str(phrase_pairs[i])+'\t'+ 'd_l' #TODO: discontinuous to the left as we see from left to right
			else:
				print str(phrase_pairs[i])+'\t'+ 'd_r'


def word_lexical_reordering_right_left(phrase_pairs_indexes, alignments, n) :
	start = [((-1,-1), (-1,-1))]
	end = [((n,n), (n,n))]
	
	#TODO: check whether this block is needed
	alignments[-1] = [-1]
	alignments[n] = [n]
	#####################

	phrase_pairs = start+phrase_pairs_indexes+end

	phrase_pairs.reverse()

	for i in range(0, len(phrase_pairs)-1):
		if alignment_exists(alignments, phrase_pairs[i][0][0] - 1, phrase_pairs[i][1][0] - 1):
			print str(phrase_pairs[i]) + '\t' + 'm'
		elif alignment_exists(alignments, phrase_pairs[i][0][1] +1, phrase_pairs[i][1][0] - 1):
			print str(phrase_pairs[i]) + '\t' + 's'
		else:
			if phrase_pairs[i][0][1] > phrase_pairs[i+1][0][0]:
				print str(phrase_pairs[i])+'\t'+ 'd_l' #TODO: discontinuous to the left as we see from left to right
			else:
				print str(phrase_pairs[i])+'\t'+ 'd_r'




#word_lexical_reordering_left_right(phrase_pairs_indexes, alignments, 6)

word_lexical_reordering_right_left(phrase_pairs_indexes, alignments, 6)

