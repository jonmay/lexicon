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
from subprocess import check_call, Popen, PIPE
import shlex
from jmutil import shchain
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
  parser = argparse.ArgumentParser(description="given domain text and base text (or ngrams), get domain-relevant patterns",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  addonoffarg(parser, 'debug', help="debug mode", default=False)
  parser.add_argument("--domainfile", "-d", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="input domain file")
  parser.add_argument("--basefile", "-b", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="input base file")
  addonoffarg(parser, 'basetext', help="base file is text, not ngram (if ngram, must match specified ngram)")
  parser.add_argument("--basengramfile", nargs='?', type=argparse.FileType('w'), default=None, help="output processing of base file; only used if not None and if basetext")
  parser.add_argument("--outfile", "-o", nargs='?', type=argparse.FileType('w'), default=sys.stdout, help="output file")
  parser.add_argument("--ngrams", "-n", type=int, default=6, help='ngrams to count') # TODO: generalize to multiple entries
  parser.add_argument("--masks", "-m", type=int, nargs='+', default=[1,2], help='number of words to mask')
  parser.add_argument("--tolower", default=os.path.join(scriptdir, 'tolower.py'), help='tolower file')
  parser.add_argument("--ngramcount", default=os.path.join(scriptdir, 'ngram-count'), help='ngram-count file')
  parser.add_argument("--maskngram", default=os.path.join(scriptdir, 'maskngram.py'), help='maskngram file')
  parser.add_argument("--uniqcount", default=os.path.join(scriptdir, 'uniqcount.py'), help='uniqcount file')
  



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

  domainfile = prepfile(args.domainfile, 'r')
  basefile = args.basefile
#  basefile = prepfile(args.basefile, 'r')
  _, domaintmpfile = tempfile.mkstemp(dir=workdir, text=True)
  domaintmpfile = prepfile(open(domaintmpfile, 'w'), 'w')
  outfile = prepfile(args.outfile, 'w')

  cmdchain = [args.tolower, # lowercase
              "sort",
              "uniq",
              args.ngramcount+" -order %d -write - -text -" % args.ngrams, # count ngrams
              args.maskngram+" -m %s" % (' '.join(map(str, args.masks))),  # mask out words
              "sort", # sort
              args.uniqcount] # counter-aware uniq
  shchain(cmdchain, input=domainfile, output=domaintmpfile)
  domaintmpfile.close()
  if args.basetext:
    if args.basengramfile is None:
      _, basengramfilename = tempfile.mkstemp(dir=workdir, text=True)
      basengramfile = prepfile(basengramfilename, 'w')
    else:
      basengramfile = prepfile(args.basengramfile, 'w')
      basengramfilename = basengramfile.name
    shchain(cmdchain, input=basefile, output=basengramfile)
    basefile = prepfile(basengramfilename, 'r')
  prochain = ["join -t'\t' %s %s" % (domaintmpfile.name, basefile.name), # common patterns
  #            "awk -F'\t' '{printf(\"%s\t%f\n\", $1,$2/$3)}'",
  #            "sort -t'\t' -k2nr",
  ]
  # doing it in an in-python step
  _, tfdftmpfile = tempfile.mkstemp(dir=workdir, text=True)
  tfdftmpfile = prepfile(tfdftmpfile, 'w')
  shchain(prochain, output=tfdftmpfile)
  tfdftmpfile.close()
  
  tfdftmpfile = prepfile(tfdftmpfile.name, 'r')
  res = []
  for line in tfdftmpfile:
    toks = line.strip().split('\t')
    res.append((toks[0], float(toks[1])/float(toks[2])))
  # ngrams not seen in base
  _, oovchainfile = tempfile.mkstemp(dir=workdir, text=True)
  oovchainfile = prepfile(oovchainfile, 'w')
  shchain(["join -t'\t' -v 1 %s %s" % (domaintmpfile.name, basefile.name),], output=oovchainfile)
  oovchainfile.close()
  oovchainfile = prepfile(oovchainfile.name, 'r')
  for line in oovchainfile:
    line = line.strip().split('\t')
    res.append((line[0], float(line[1])))
  for thek, thev in sorted(res, key=lambda tup: (tup[1], tup[0]), reverse=True):
    outfile.write("%s\t%f\n" % (thek, thev))

if __name__ == '__main__':
  main()
