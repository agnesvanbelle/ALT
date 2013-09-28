

phrase_pairs_indexes = [((0, 0), (0, 0)), ((1,1), (1, 1)), ((4, 4), (2,2)), ((2,3),(3,4)), ((5,5),(5,5))]

def lexical_reordering_left_right(phrase_pairs_indexes, n) :
	start = [((-1,-1), (-1,-1))]
	end = [((n,n), (n,n))]

	phrase_pairs = start+phrase_pairs_indexes+end

	for i in range(0, len(phrase_pairs)-1):
		if phrase_pairs[i+1][1][0] == phrase_pairs[i][1][1] + 1 and phrase_pairs[i+1][0][0] == phrase_pairs[i][0][1] + 1 :
			print str(phrase_pairs[i]) +'\t'+ 'm'
		elif phrase_pairs[i+1][1][0] == phrase_pairs[i][1][1] + 1 and phrase_pairs[i+1][0][1] == phrase_pairs[i][0][0] - 1:
			print str(phrase_pairs[i])+'\t'+ 's'
		else :
			if phrase_pairs[i+1][0][1] > phrase_pairs[i][0][0]:
				print str(phrase_pairs[i])+'\t'+ 'd_l' #TODO: discontinuous to the left as we see from left to right
			else:
				print str(phrase_pairs[i])+'\t'+ 'd_r'


def lexical_reordering_right_left(phrase_pairs_indexes, n) :
	start = [((-1,-1), (-1,-1))]
	end = [((n,n), (n,n))]

	phrase_pairs = start+phrase_pairs_indexes+end
	phrase_pairs.reverse()	

	for i in range(0, len(phrase_pairs)-1):
		if phrase_pairs[i+1][1][1] == phrase_pairs[i][1][0] - 1 and phrase_pairs[i+1][0][1] == phrase_pairs[i][0][0] - 1:
			print str(phrase_pairs[i]) +'\t'+ 'm'
		elif phrase_pairs[i+1][1][1] == phrase_pairs[i][1][0] - 1 and phrase_pairs[i+1][0][0] == phrase_pairs[i][0][1] + 1:
			print str(phrase_pairs[i]) + '\t' + 's'
		else:
			if phrase_pairs[i][0][1] > phrase_pairs[i+1][0][0]:
				print str(phrase_pairs[i])+'\t'+ 'd_l' #TODO: discontinuous to the left as we see from right to left
			else:
				print str(phrase_pairs[i])+'\t' + 'd_r'


#lexical_reordering_left_right(phrase_pairs_indexes, 6)

lexical_reordering_right_left(phrase_pairs_indexes, 6)
