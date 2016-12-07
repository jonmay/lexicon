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
import difflib

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
  parser = argparse.ArgumentParser(description="turn before after file into instruction file",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  addonoffarg(parser, 'debug', help="debug mode", default=False)
  parser.add_argument("--infile", "-i", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="input file")
  parser.add_argument("--outfile", "-o", nargs='?', type=argparse.FileType('w'), default=sys.stdout, help="output file")
  addonoffarg(parser, 'insert', help="Allow split insertion")



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
  outfile = prepfile(args.outfile, 'w')


  currsource = None
  for line in infile:
    toks = line.strip().split('\t')
    if len(toks) < 3:
      continue
    before = toks[1].split()
    after = toks[2].split()
    opcodes = difflib.SequenceMatcher(None, before, after).get_opcodes()
    res = []
    ok = True
    for code in opcodes:
      # insertion of splits breaks tagging assumption; may be ok if we do it encoder-decoder
      if code[0] == 'insert':
        if not args.insert:
          ok = False
          break
        for pos in range(code[3],code[4]):
          if after[pos] == 'SPLIT':
            res.append('S')
          else:
            sys.stderr.write("Weird insertion: %s in [%s] -> [%s]\n" % (after[pos], toks[1], toks[2]))
            ok = False
            break
      else:
        for pos in range(code[1],code[2]):
          if code[0] == 'equal':
            res.append('K')
          elif code[0] == 'delete':
            res.append('D')
          elif code[0] == 'replace': # expecting single SPLIT insertion; possible deletion
            if code[4]-code[3] == 1 and after[code[3]] == 'SPLIT':
              if pos == code[1]:
                res.append('S')
              else:
                res.append('D')
            else:
              sys.stderr.write("Weird replacement: %s -> %s in [%s] -> [%s]\n" % (' '.join(before[code[1]:code[2]]), ' '.join(after[code[3]:code[4]]), toks[1], toks[2]))
              ok = False
              break
              #sys.exit(1)
          else:
            sys.stderr.write("Unexpected: "+str(code)+"\n")
            sys.exit(1)
    if ok:
      outfile.write('\t'.join(toks)+"\t"+' '.join(res)+"\n")
    #outfile.write('\t'.join(toks)+"\t"+' '.join([str(x) for x in difflib.SequenceMatcher(None, toks[1].split(), toks[2].split()).get_opcodes()])+"\n")

if __name__ == '__main__':
  main()
