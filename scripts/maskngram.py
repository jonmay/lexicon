#!/usr/bin/env python3
import argparse
import sys
import codecs
if sys.version_info[0] == 2:
  from itertools import izip
else:
  izip = zip
from collections import defaultdict as dd
import re
import os.path
import gzip
import tempfile
import shutil
import atexit
from itertools import combinations

scriptdir = os.path.dirname(os.path.abspath(__file__))


reader = codecs.getreader('utf8')
writer = codecs.getwriter('utf8')


def prepfile(fh, code):
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


def compress(tc):
  ''' remove adjacent <VAR> '''
  for i, v in enumerate(tc[1:], start=1):
    if v == "<VAR>" and (tc[i-1]=="<VAR>" or tc[i-1] == ""):
      tc[i] = ""
  return ' '.join(tc).split() # removes extra whitespace

def main():
  parser = argparse.ArgumentParser(description="mask out m words from ngrams in a tab-separated file",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("--infile", "-i", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="input file")
  parser.add_argument("--masks", "-m", nargs='+', type=int, default=[2,], help="number of words to maskout")
  parser.add_argument("--field", "-f", type=int, default=0, help="0-based field the ngram is in")
  parser.add_argument("--maskvalue", type=str, default="<VAR>", help="value the masked word is replaced with")
  addonoffarg(parser, 'compress', help='remove adjacent <VAR>')
  parser.add_argument("--outfile", "-o", nargs='?', type=argparse.FileType('w'), default=sys.stdout, help="output file")


  workdir = tempfile.mkdtemp(prefix=os.path.basename(__file__), dir=os.getenv('TMPDIR', '/tmp'))

  def cleanwork():
    shutil.rmtree(workdir, ignore_errors=True)
  atexit.register(cleanwork)


  try:
    args = parser.parse_args()
  except IOError as msg:
    parser.error(str(msg))

  infile = prepfile(args.infile, 'r')
  outfile = prepfile(args.outfile, 'w')


  for line in infile:
    # if fields are less than or equal to m, don't do anything
    # use some n choose k function to get all the mask positions
    # write out the masked fields
    fields = line.strip().split('\t')
    toks = fields[args.field].split()
    if len(toks) < 3:
      continue
    for maskkind in args.masks:
      if len(toks) > maskkind:
        for mask in combinations(range(len(toks)), maskkind):
          tc = toks.copy()
          for pos in mask:
            tc[pos] = args.maskvalue
          if args.compress:
            tc = compress(tc)
          fc = fields[:args.field]+[' '.join(tc),]+fields[args.field+1:]
          outfile.write('\t'.join(fc)+"\n")
    #outfile.write(line)

if __name__ == '__main__':
  main()
