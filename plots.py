import numpy as np
import matplotlib.pyplot as plt
	
def stddev_reorderings(input_file):
	means = []
	stds = []
	f = open(input_file,"r")

	for line in f.readlines():
		a,b = line.split()
		means.append(int(a))
		stds.append(int(b))	

	N = len(means)

	ind = np.arange(N)  # the means locations for the groups
	width = 0.45       # the width of the bars

	fig, ax = plt.subplots()
	rects1 = ax.bar(ind, means, width, color='c', yerr=stds, ecolor='b')

	ax.set_ylabel('Mean count')
	ax.set_title('Mean and standard deviation of each reordering')
	ax.set_xticks(ind+width/2)
	ax.set_xticklabels( ('p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8') )

def draw_bar_chart(input_file, title, xlabel, ylabel, width):
	x = []
	y = []

	f = open(input_file, "r")
	for line in f.readlines():
		a,b = line.split()
		x.append(int(a))
		y.append(int(b))

	x = np.asarray(x)	

	fig, ax = plt.subplots()
	rects1 = ax.bar(x, y, width, color='b')

	ax.set_ylabel(ylabel)
	ax.set_xlabel(xlabel)
	ax.set_title(title)
	ax.set_xticks(x+width/2)
	ax.set_xticklabels(x)

	plt.savefig(input_file[0:input_file.find('.')]+'.pdf')
	#plt.show()

def draw_histogram(m,s,d_r,d_l, title, xlabel, ylabel, width, output_file):
	N = 2
	ind = np.arange(N)

	fig, ax = plt.subplots()
	rects1 = ax.bar(ind, m, width, color='b')
	rects2 = ax.bar(ind+width, s, width, color='c')
	rects3 = ax.bar(ind+2*width, d_r, width, color='g')
	rects4 = ax.bar(ind+3*width, d_l, width, color='r')

	ax.set_position([0.1,0.1,0.6,0.8])
	ax.set_ylabel(ylabel)
	ax.set_xlabel(xlabel)
	ax.set_title(title)
	ax.set_xticks(ind+2*width)
	ax.set_xticklabels(('Left to right', 'Right to left'))
   	
	ax.legend( (rects1, rects2, rects3, rects4), ('Monotone', 'Swap', 'Disc_left', 'Disc_right'), loc=1, bbox_to_anchor=(1.5,1))

	#plt.show()
	plt.savefig(output_file+'.pdf')


#m = [1,2]
#s = [3,4]
#d_r = [2,2]
#d_l = [4,4]
draw_histogram(m,s,d_r,d_l,'title','Direction','Count',0.2, 'count_histogram')


#stddev_reorderings('mean_std.txt')
#draw_bar_chart('bar.txt', 'title', 'xxx', 'yyy', 0.4)
