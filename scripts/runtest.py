#!/usr/bin/env python
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
import shlex
from jmutil import shchain, mkdir_p

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
  parser = argparse.ArgumentParser(description="apply patterns to data, get in and out results, sample them.",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  addonoffarg(parser, 'debug', help="debug mode", default=False)
  parser.add_argument("--lexiconfile", "-l", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="input lexicon file")
  parser.add_argument("--toklcfile", "-t", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="toklc english file")
  parser.add_argument("--patternfile", "-p", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="pattern file")
  parser.add_argument("--sample", "-s", type=int, default=20, help="number of samples to catch")
  parser.add_argument("--applyprog", default=os.path.join(scriptdir, 'applymatches.py'), help='apply matches program')
  parser.add_argument("--sampleprog", default=os.path.join(scriptdir, 'sample.py'), help='sample program')
  parser.add_argument("--maskngram", default=os.path.join(scriptdir, 'maskngram.py'), help='maskngram file')
  parser.add_argument("--outdir", "-o", default=".", help="output directory")


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

  lexiconfile = prepfile(args.lexiconfile, 'r')
  toklcfile = prepfile(args.toklcfile, 'r')
  patternfile = prepfile(args.patternfile, 'r')

  mkdir_p(args.outdir)
  changefile=prepfile(os.path.join(args.outdir, "changes"), 'w')
  samefile=prepfile(os.path.join(args.outdir, "sames"), 'w')
  changesamplefile=prepfile(os.path.join(args.outdir, "changesamples"), 'w')
  samesamplefile=prepfile(os.path.join(args.outdir, "samesamples"), 'w')

  _, tmpfile = tempfile.mkstemp(dir=workdir, text=True)
  tmpfile = prepfile(tmpfile, 'w')

  for l, t in izip(lexiconfile, toklcfile):
    tmpfile.write("%s\t%s" % (l.strip(), t))
  tmpfile.close()

  shchain(["%s -i %s -t 5.0 --no-passthrough --scoremode" % (args.applyprog, tmpfile.name),], input=patternfile, output=changefile)
  shchain(["%s -i %s -t 5.0 --no-mods" % (args.applyprog, tmpfile.name),], input=patternfile, output=samefile)
  changefile.close()
  samefile.close()
  changefile = prepfile(changefile.name, 'r')
  _, tmpfile = tempfile.mkstemp(dir=workdir, text=True)
  tmpfile = prepfile(tmpfile, 'w')
  shchain(["%s -s %d" % (args.sampleprog, args.sample),], input=changefile, output=tmpfile)
  tmpfile.close()
  tmpfile=prepfile(tmpfile.name, 'r')
  for line in tmpfile:
    toks = line.strip().split('\t')
    changesamplefile.write('\t'.join(toks[:-1])+"\n")
    for tok in toks[-1].split('//'):
      changesamplefile.write("\t%s\n" % tok.strip())
  
if __name__ == '__main__':
  main()
