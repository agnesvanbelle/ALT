
if __name__ == '__main__': #if this file is the argument to python
  
  lenSen = 9
  
  unCovered = list(set(range(0,lenSen+1)) - set([2,3,6]))
  unCovSpans = []

  print unCovered
  
  unCovSpan = None
  for i in unCovered:
    if unCovSpan == None:
      unCovSpan = [i,i]
    elif unCovSpan[1] == i-1:
      unCovSpan[1] = i
    else:
      unCovSpans.append(unCovSpan)
      unCovSpan = [i,i]
  
  print unCovSpan
  
  
  unCovSpans.append(unCovSpan)

  print unCovSpans

