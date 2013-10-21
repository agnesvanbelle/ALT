import os
import math
from collections import defaultdict

# recursively get all filenames in (sub)directories
def getFileNames(directory, nameFilters=[], extensionFilters=[]) :
  l = os.listdir(directory)
  l2 = []
  for name in l :
    if not name[-4:] in extensionFilters and not name in nameFilters:
      if os.path.isdir(directory + "/" + name):
        print "%s is dir" % name
        l2.extend(getFileNames(directory + "/" + name + "/"))
      else :
        l2.append( directory + "/" + name)

  return l2

# print a dictionary neatly
def getDictString(d, depth=0) :
  s = ""
  if len(d) > 0:
    for k, v in d.iteritems():
      for i in range(0, depth):
          s += '\t'    
      if isinstance(v, defaultdict) or isinstance(v, dict):            
        s += "%s --> \n%s\n" % (k, getDictString(v, depth+1))
      else:     
        s += "%s --> %s\n" % (k, v)
  else:
    s =  "{}"
  return s

# returns variance, given values should be a list
def variance(avg, values, lengthList) :
  if lengthList <= 0:
    return 0
  else:
    return ( sum
                (map(lambda x : math.pow( x - avg, 2), values)) /
                float(lengthList)
            )


# Shannon entropy
def entropy(l, sumL=None):
  if sumL == None:
    sumL = float(sum(l))
  l = [x/sumL for x in l]

  entrSum = 0.0
  for prob in l:
    if prob != 0:
      entrSum += (prob * math.log(prob,2))

  return (-1) * entrSum
