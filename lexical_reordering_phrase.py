phrase_pairs_indexes = [((0, 0), (0, 0)), ((1,1), (1, 1)), ((4, 4), (2,2)), ((2,3),(3,4)), ((5,5),(5,5))]

#phrase_pairs_indexes = [((0, 0), (0, 0)), ((1, 2), (1, 1)), ((3, 3), (2, 2)), ((3, 4), (2, 3)), ((4, 4), (3, 3)), ((6, 6), (4, 4)), ((8, 8), (6, 6)), ((8, 9), (6, 7)), ((9, 9), (7, 7)), ((9, 10), (7, 7))]


def get_next_pairs_lr(i, phrase_pairs):
	a = []
	for j in range(i+1, len(phrase_pairs)):
		if phrase_pairs[i][1][1] + 1 == phrase_pairs[j][1][0]:
			a.append(j)
	return a

def get_next_pairs_rl(i, phrase_pairs):
	a = []
	for j in range(i+1, len(phrase_pairs)):
		if phrase_pairs[i][1][0] -1 == phrase_pairs[j][1][1]:
			a.append(j)
	return a


def lexical_reordering_left_right(phrase_pairs_indexes,len_e, len_f) :
	start = [((-1,-1), (-1,-1))]
	end = [((len_f, len_f), (len_e,len_e))]

	phrase_pairs = start+phrase_pairs_indexes+end
	#print phrase_pairs
	
	for i in range(0, len(phrase_pairs)-1):
		next_phrase_pairs = get_next_pairs_lr(i, phrase_pairs)
		for j in range(0, len(next_phrase_pairs)):
			k = next_phrase_pairs[j]
			if phrase_pairs[k][1][0] == phrase_pairs[i][1][1] + 1 and phrase_pairs[k][0][0] == phrase_pairs[i][0][1] + 1 :
				print str(phrase_pairs[i]) +'\t'+ 'm'
			elif phrase_pairs[k][1][0] == phrase_pairs[i][1][1] + 1 and phrase_pairs[k][0][1] == phrase_pairs[i][0][0] - 1:
				print str(phrase_pairs[i])+'\t'+ 's'
			else :
				if phrase_pairs[k][0][1] > phrase_pairs[i][0][0]:
					print str(phrase_pairs[i])+'\t'+ 'd_r'
				else:
					print str(phrase_pairs[i])+'\t'+ 'd_l'


def lexical_reordering_right_left(phrase_pairs_indexes, len_e, len_f) :
	start = [((-1,-1), (-1,-1))]
	end = [((len_f, len_f), (len_e,len_e))]

	phrase_pairs = start+phrase_pairs_indexes+end
	phrase_pairs.reverse()	

	for i in range(0, len(phrase_pairs)-1):
		next_phrase_pairs = get_next_pairs_rl(i, phrase_pairs)
		for j in range(0, len(next_phrase_pairs)):
			k = next_phrase_pairs[j]
			if phrase_pairs[k][1][1] == phrase_pairs[i][1][0] - 1 and phrase_pairs[k][0][1] == phrase_pairs[i][0][0] - 1:
				print str(phrase_pairs[i]) +'\t'+ 'm'
			elif phrase_pairs[k][1][1] == phrase_pairs[i][1][0] - 1 and phrase_pairs[k][0][0] == phrase_pairs[i][0][1] + 1:
				print str(phrase_pairs[i]) + '\t' + 's'
			else:
				if phrase_pairs[i][0][1] > phrase_pairs[k][0][0]:
					print str(phrase_pairs[i])+'\t'+ 'd_l'
				else:
					print str(phrase_pairs[i])+'\t' + 'd_r'


lexical_reordering_left_right(phrase_pairs_indexes, 6,6)

#lexical_reordering_right_left(phrase_pairs_indexes, 6,6)
