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


def stats(hyps, golds):
  """ p, r, f from hypothesis and correct counters """
  m = float(sum((golds & hyps).values()))
  h = float(sum(hyps.values()))
  g = float(sum(golds.values()))
  p = m/h
  r = m/g
  f = (2*p*r)/(p+r)
  return (p, r, f)

def main():
  parser = argparse.ArgumentParser(description="given a dictionary, a partially scored parallel corpus, and a set of entries to modify, return future scoring information and a score",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  addonoffarg(parser, 'debug', help="debug mode", default=False)
  parser.add_argument("--dictfile", "-i", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="dict file (foreign tab english)")
  parser.add_argument("--corpfile", "-c", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="parallel corpus file (foreign tab english)")
  parser.add_argument("--scorefile", "-s", nargs='?', type=argparse.FileType('r'), default=None, help="file describing partial scoring")
  parser.add_argument("--entries", "-e", nargs='+', default=None,  help="input entries")
  parser.add_argument("--outfile", "-o", nargs='?', type=argparse.FileType('w'), default=sys.stdout, help="output score file")




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
  scorefile = prepfile(args.scorefile, 'r')
  outfile = prepfile(args.outfile, 'w')


  dictionary = dd(list)
  # TODO: incremental scoring only based on existing scorefile and entries!!!
  for line in dictfile:
    toks = line.strip().split('\t')
    dictionary[toks[0]].append(Counter(toks[1].split()))
  goldstats = Counter()
  hypstats = Counter()
  for line in corpfile:
    fsent, esent = line.strip().split('\t')
    ecounter = Counter(esent.split())
    goldstats +=ecounter
    for fword in fsent.split():
      if fword in dictionary:
        hypstats += oraclematch(dictionary[fword], ecounter)
  (p, r, f) = stats(hypstats, goldstats)
  print("Precision: %f\nRecall: %f\nF1: %f" % (p,r,f))

if __name__ == '__main__':
  main()
