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
from collections import Counter

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
  parser = argparse.ArgumentParser(description="most frequent type baseline: predict most frequent class for each type",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  addonoffarg(parser, 'debug', help="debug mode", default=False)
  parser.add_argument("--train_text", "--tt", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="input train text file")
  parser.add_argument("--train_label", "--tl", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="input train label file")
  parser.add_argument("--test_text", "--st", nargs='?', type=argparse.FileType('r'), default=None, help="input test text file")
  parser.add_argument("--test_label", "--sl", nargs='?', type=argparse.FileType('r'), default=None, help="input test label file")
  parser.add_argument("--test_out", "-o", nargs='?', type=argparse.FileType('w'), default=sys.stdout, help="output test prediction file")




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


  train_text =  prepfile(args.train_text, 'r')
  train_label = prepfile(args.train_label, 'r')
  test_text =   None if args.test_text is None else  prepfile(args.test_text, 'r')
  test_label =  None if args.test_label is None else prepfile(args.test_label, 'r')

  outfile = prepfile(args.test_out, 'w')

  types = dd(Counter)
  
  for ln, (tline, lline) in enumerate(zip(train_text, train_label), start=1):
    tline = tline.strip().split()
    lline = lline.strip().split()
    if len(tline) != len(lline):
      sys.stderr.write("Length mismatch at %d: %d vs %d\n" % (ln, len(tline), len(lline)))
      continue
    for ttok, ltok in zip(tline, lline):
      types[ttok][ltok]+=1

  if test_text is not None:
    for line in test_text:
      labels = []
      for tok in line.strip().split():
        labels.append(types[tok].most_common(1)[0][0])
      outfile.write(' '.join(labels)+"\n")

if __name__ == '__main__':
  main()
