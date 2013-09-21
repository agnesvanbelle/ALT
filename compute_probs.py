import math

#table_nl : {nl:count}
#table_en : {en:count}
#table_nl_en : {(nl,en):(phrase_count, {[alignment_nl_en]:count}, {[alignment_en_nl]:count})}

#example alignment : [(0,[1]), (1,[0,2,3])]

#prob_nl_en = {(nl,en) :  (p(nl|en), l(nl|en))}
prob_nl_en = dict()
#prob_en_nl = {(en,nl) :  (p(en|nl), l(e|nl))}
prob_en_nl = dict()


def is_length_one(nl, en):
	if " " not in nl and " " not in en:
		return True
	return False


def get_most_frequent_alignment(alignments):
	max = 0
	best_alignment = None
	for alignment, count in alignments.items():
		if count > max :
			best_alignment = alignment
	return best_alignment



def compute_lex_prob(nl, en, table_nl, table_en, table_nl_en, direct, best_alignment):
	e = None
	f = None
	table_f = None
	if direct:
		e = en
		f = nl
	else
		e = nl
		f = en
	
	#compute log probability
	
	e_split = e.split()
	f_split = f.split()
	
	lex_prob = 0

	for i in range (0, len(e_split)):
		sub_prob = 0
		#every word must be aligned to at least one word
		aligned_indexes = best_alignment[i][1]
		aligned_indexes_num = len(aligned_indexes)
		for j in range(0, aligned_indexes_num):
			#w(e|f) = c(e,f) / c(f)
			count_f = 0
			count_e_f = 0
			if direct:
				count_f = table_nl[f]
				count_e_f = table_nl_en[(f_split[j], e_split[i])][0]
			else:
				count_f = table_en[f]
				count_e_f = table_nl_en[(e_split[i], f_split[j])][0]]

			sub_prob += count_e_f / (float)count_f

		sub_prob = math.log(sub_prob/(float)aligned_indexes_num)
		lex_prob += sub_prob

	return lex_prob


#direct = True if lex(en|nl, a), False otherwise
def lexical_weighting(nl, en, table_nl, table_en, table_nl_en, direct):

	if direct:
		alignments = table_nl_en[(nl,en)][2]
	else:
		alignments = table_en_nl[(nl,en)][1]
		
	best_alignment = get_most_frequent_alignment(alignments)


	return compute_lex_prob(nl, en, table_nl, table_en, table_nl_en, direct, best_alignment)


def compute_probabilities(table_nl, table_en, table_nl_en):
	for (nl, en) in table_nl_en.keys():
		#compute translation probabilities 
	
		trans_nl_en = math.log(table_nl_en[(nl,en)][0] / float(table_en[en]))
		
		trans_en_nl = math.log(table_nl_en[(nl,en)][0] / float(table_nl[nl]))

		#compute lexical probabilites
		if is_length_one(nl, en):
			#lexical probability is the same as translation probability
			lex_nl_en = trans_nl_en
			lex_en_nl = trans_en_nl
		else:
			lex_nl_en = lexical_weighting(nl, en, table_nl, table_en, table_nl_en, False)
			lex_en_nl = lexical_weighting(nl, en, table_nl, table_en, table_nl_en, True)
		
		prob_nl_en[(nl,en)] = (trans_nl_en, lex_nl_en)
		prob_en_nl[(en,nl)] = (trans_en_nl, lex_en_nl)

