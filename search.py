import os,sys

from kwindex import kw_index

"""
Query result candidate class
"""
class Candidate:
  def __init__(self, doc, title_match, body_match):
    self.doc = doc
    self.t_match = title_match
    self.b_match = body_match
    self._score = float(len(self.t_match)) * 5 / len(self.doc["t"]) + float(len(self.b_match)) / len(self.doc["b"])
    if doc["n"].startswith("release"):
      self._score = 0.0

  def name(self):
    return self.doc["n"]
  
  def title(self):
    return self.doc["t"]
  
  def body(self):
    return self.doc["b"]

  def score(self):
    return self._score

  def __cmp__(self, other):
    c = cmp(self.score(), other.score())
    if c == 0:
      c = cmp(self.name(), other.name())
    return c

"""
Main character class who does actual search work
"""
class Searcher:
  def __init__(self, query, version):
    res = []
    if query and len(query) > 0:
      for doc in kw_index:
        title_match = findall(doc["t"], query)
        body_match = findall(doc["b"], query)
        if title_match or body_match:
          cand = Candidate(doc, title_match, body_match)
          res.append(cand)
    res.sort()
    res.reverse()
    self._result = res
  
  def result(self):
    return self._result

"""
findall() returns all positions by list that the query matches in the string.
"""
def findall(s, q):
  n = len(s)
  res = []
  start = 0
  while True:
    pos = s.find(q, start)
    if pos > -1:
      res.append(pos)
      start = pos + 1
    else:
      return res

def main():
  if len(sys.argv) != 2:
    print "Usage: %s query" % sys.argv[0]
    quit()

  q = unicode(sys.argv[1], 'cp932')
  searcher = Searcher(q, "any")
  for cand in searcher.result():
    print "%f\t%s\t%s" % (cand.score(), cand.name(), cand.title().encode("shift_jis"))




if __name__ == '__main__':
  main()
