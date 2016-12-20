#!/usr/bin/env python3

# dict2inst (various approaches): given a dictionary, come up with a set of
# modification instructions for it

# simplifydict: given a dictionary and its instruction set, return a modified dictionary

# scoredict (this): given a dictionary, a partially scored parallel corpus, and a set of entries to modify, apply the entries to the corpus and return the score

import argparse
import sys
import codecs
if sys.version_info[0] == 2:
  from itertools import izip
else:
  izip = zip

from collections import defaultdict as dd, Counter
import re
import os.path
import gzip
import tempfile
import shutil
import atexit
import unicodedata as ud

scriptdir = os.path.dirname(os.path.abspath(__file__))


reader = codecs.getreader('utf8')
writer = codecs.getwriter('utf8')


def prepfile(fh, code):
  if type(fh) is str:
    fh = open(fh, code)
  ret = gzip.open(fh.name, code if code.endswith("t") else code+"t") if fh.name.endswith(".gz") else fh
  if sys.version_info[0] == 2:
    if code.startswith('r'):
      ret = reader(fh)
    elif code.startswith('w'):
      ret = writer(fh)
    else:
      sys.stderr.write("I didn't understand code "+code+"\n")
      sys.exit(1)
  return ret

def addonoffarg(parser, arg, dest=None, default=True, help="TODO"):
  ''' add the switches --arg and --no-arg that set parser.arg to true/false, respectively'''
  group = parser.add_mutually_exclusive_group()
  dest = arg if dest is None else dest
  group.add_argument('--%s' % arg, dest=dest, action='store_true', default=default, help=help)
  group.add_argument('--no-%s' % arg, dest=dest, action='store_false', default=default, help="See --%s" % arg)

def oraclematch(choices, golds):
  """ find the best choice that matches the golds """
  max = 0
  argmax = choices[0]
  for choice in choices:
    _, _, f = stats(choice, golds)
    if f > max:
      max = f
      argmax = choice
  return argmax


def stats(hyps, golds, matches=None):
  """ p, r, f from hypothesis and correct counters """
  if matches is None:
    matches = golds & hyps
  m = float(sum(matches.values()))
  h = float(sum(hyps.values()))
  g = float(sum(golds.values()))
  p = 0.0 if h==0 else m/h
  r = 0.0 if g==0 else m/g
  f = 0.0 if (p==0 or r==0) else (2*p*r)/(p+r)
  return (p, r, f)

def matchcount(words, length, dictionary):
  """ how many matches available for given sequence on the given word list? """
  if length > len(words):
    return 0
  tot = 0
  for spos in range(len(words)-length+1):
    if ' '.join(words[spos:spos+length]) in dictionary:
      tot+=1
  return tot


def isnotallpunc(word, debug=False):
  ''' return true if any characters are not exclusively symbol/punc '''
  unis = map(ud.category, word)
  if(debug):
    print([x for x in unis])
  for uni in unis:
    if not uni.startswith('P') and not uni.startswith('S'):
      return True
  return False


def isTrue(word):
  ''' always true '''
  return True

def main():
  parser = argparse.ArgumentParser(description="given a dictionary, a partially scored parallel corpus, and a set of entries to modify, return future scoring information and a score",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  addonoffarg(parser, 'debug', help="debug mode", default=False)
  parser.add_argument("--dictfile", "-d", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="dict file (foreign tab english)")
  parser.add_argument("--corpfile", "-c", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="parallel corpus file (foreign tab english)")
  parser.add_argument("--scorefile", "-s", nargs='?', type=argparse.FileType('r'), default=None, help="file describing partial scoring")
  parser.add_argument("--entries", "-e", nargs='+', default=None,  help="input entries")
  parser.add_argument("--outfile", "-o", nargs='?', type=argparse.FileType('w'), default=sys.stdout, help="output score file")
  addonoffarg(parser, 'persent', default=False, help="print per-sentence statistics and debug info")
  addonoffarg(parser, 'puncfilt', default=True, help="don't consider all-punctuation tokens in this scoring")


  try:
    args = parser.parse_args()
  except IOError as msg:
    parser.error(str(msg))

  workdir = tempfile.mkdtemp(prefix=os.path.basename(__file__), dir=os.getenv('TMPDIR', '/tmp'))

  def cleanwork():
    shutil.rmtree(workdir, ignore_errors=True)
  if args.debug:
    print(workdir)
  else:
    atexit.register(cleanwork)


  dictfile = prepfile(args.dictfile, 'r')
  corpfile = prepfile(args.corpfile, 'r')
  scorefile = prepfile(args.scorefile, 'r') if args.scorefile is not None else None
  outfile = prepfile(args.outfile, 'w')
  thefilt = isnotallpunc if args.puncfilt else isTrue

  dictionary = dd(lambda: dd(list))
  # TODO: incremental scoring only based on existing scorefile and entries!!!
  for line in dictfile:
    toks = line.strip().split('\t')
    if len(toks) < 2:
      sys.stderr.write("Malformed entry: %s" % line)
      continue
    srctoks = toks[0].split()
    trgtoks = filter(thefilt, toks[1].split())
    dictionary[len(srctoks)][toks[0]].append(Counter(trgtoks))
  # for k in dictionary.keys():
  #   print(k, len(dictionary[k].values()))
  goldstats = Counter()
  hypstats = Counter()
  matchstats = Counter()
  # is dp worth it? how many >1s are available?
  # 2s are ~ 3% of 1s and 3s are barely there; not worth it
  #matches = dd(int)
  for line in corpfile:
    fsent, esent = line.strip().split('\t')
    esenttok = filter(thefilt, esent.split())
    ecounter = Counter(esenttok)
    goldstats +=ecounter
    fwords = fsent.split()
    #for k in dictionary.keys():
    #  matches[k] += matchcount(fwords, k, dictionary[k])
    sentmatch = Counter()
    for fword in fwords:
      if fword in dictionary[1]:
        sentmatch += oraclematch(dictionary[1][fword], ecounter)
    if args.persent:
      (lp, lr, lf) = stats(sentmatch, ecounter)
      outfile.write("p %f r %f f %f\t[[[%s]]]\t[[[%s]]]\n" % (lp, lr, lf, '///'.join(sentmatch.keys()), esent))
    hypstats += sentmatch
    matchstats += sentmatch&ecounter
  (p, r, f) = stats(hypstats, goldstats, matches=matchstats)
  outfile.write("Precision: %f\nRecall: %f\nF1: %f\n" % (p,r,f))
  #for k, v in matches.items():
  #  print("%d matches of length %d" %(v, k))

if __name__ == '__main__':
  main()
