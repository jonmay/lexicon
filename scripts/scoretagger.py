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

def main():
  parser = argparse.ArgumentParser(description="Accuracy scores for a tagger",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  addonoffarg(parser, 'debug', help="debug mode", default=False)
  parser.add_argument("--infile", "-i", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="input file")
  parser.add_argument("--reffile", "-r", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="reference file")
  parser.add_argument("--outfile", "-o", nargs='?', type=argparse.FileType('w'), default=sys.stdout, help="output file")
  addonoffarg(parser, 'perline', default=False, help="Show scores per line")



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


  infile = prepfile(args.infile, 'r')
  reffile = prepfile(args.reffile, 'r')
  outfile = prepfile(args.outfile, 'w')


  allitems = 0.0
  allhits = 0.0
  for ln, (hypline, refline) in enumerate(zip(infile, reffile), start=1):
    hypline = hypline.strip().split()
    refline = refline.strip().split()
    if len(hypline) != len(refline):
      sys.stderr.write("Length mismatch at %d: %d vs %d\n" % (ln, len(hypline), len(refline)))
      continue
    items = 0.0
    hits = 0.0
    for hyp, ref in zip(hypline, refline):
      items+=1.0
      if hyp == ref:
        hits+=1.0
    if args.perline:
      outfile.write("%.2f %d %d\n" % (hits/items, int(hits), int(items)))
    allitems+=items
    allhits+=hits
  outfile.write("%.2f %d %d\n" % (allhits/allitems, int(allhits), int(allitems)))
if __name__ == '__main__':
  main()
