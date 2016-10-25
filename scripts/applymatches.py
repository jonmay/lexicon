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


def makepattern(text):
  ''' turn text interpretation of pattern into real regex pattern '''
  text, score = text.split('\t')
  toks = text.split()
  for i, tok in enumerate(toks):
    if tok == "<VAR>":
      toks[i] = "(.*)"
    elif tok == "<s>":
      toks[i] = "^"
    elif tok == "</s>":
      toks[i] = "$"
    else:
      toks[i] = r"\b"+re.escape(tok)+r"\b"
  retxt = ' '.join(toks)
  retxt = re.sub(r'^\^ ', '^', retxt)
  retxt = re.sub(r' \$$', '$', retxt)
  return re.compile(retxt)

def applydelete(text, patterns):
  ''' apply patterns in a way that deletes words from single entry '''
  for pattern in patterns:
    while True:
      res = pattern.search(text)
      if res is None:
        break
      #print("matched %s to %s" % (pattern, text))
      text = text[:res.span()[0]]+' '.join(res.groups())+text[res.span()[1]:]
  return text

def applysplit(texts, patterns): # may have to change interface
  ''' recursively apply patterns in a way that splits words and queues them '''
  newtexts = []
  oldtexts = []
  for text in texts:
    handled = False
    for pattern in patterns:
      res = pattern.search(text)
      if res is not None:
        #print("matched %s to %s" % (pattern, text))
        handled = True
        pre = text[:res.span()[0]]
        if len(pre) > 0:
          newtexts.append(pre)
        for group in res.groups():
          newtexts.append(group)
        post = text[res.span()[1]:]
        if len(post) > 0:
          newtexts.append(post)
        break
    if not handled:
      oldtexts.append(text)
  if len(newtexts) > 0:
    return oldtexts+applysplit(newtexts, patterns)
  else:
    return oldtexts

def main():
  parser = argparse.ArgumentParser(description="use auto-found matches to split up lexicon entries",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("--infile", "-i", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="input file")
  parser.add_argument("--patternfile", "-p", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="pattern file")
  parser.add_argument("--threshhold", "-t", type=float, default=5.0, help="minimum ratio of pattern")
  parser.add_argument("--outfile", "-o", nargs='?', type=argparse.FileType('w'), default=sys.stdout, help="output file")
  addonoffarg(parser, 'passthrough', help='print if nothing changes')
  addonoffarg(parser, 'mods', help='print if something changes')
  addonoffarg(parser, 'scoremode', default=False, help='put splits in "score mode" output')

  workdir = tempfile.mkdtemp(prefix=os.path.basename(__file__), dir=os.getenv('TMPDIR', '/tmp'))

  def cleanwork():
    shutil.rmtree(workdir, ignore_errors=True)
  atexit.register(cleanwork)


  try:
    args = parser.parse_args()
  except IOError as msg:
    parser.error(str(msg))

  infile = prepfile(args.infile, 'r')
  patternfile = prepfile(args.patternfile, 'r')
  outfile = prepfile(args.outfile, 'w')

  patterns = []
  for line in patternfile:
    score = float(line.strip().split('\t')[-1])
    if score >= args.threshhold:
      patterns.append(makepattern(line))

  for line in infile:
    # split source from target

    toks = line.strip().split('\t')

    target = toks[-1]
    prefix = '\t'.join(toks[:-1])
    # for each pattern
    # recursively apply to pattern as deletion
    delxform = applydelete(target, patterns)
    if args.passthrough or (args.mods and delxform != target):
      outfile.write("%s\t%s\n" % (prefix, delxform))
    # separately, recursively apply to pattern as splits
    if args.scoremode and args.mods:
      scoretarg = ' // '.join(applysplit([target,], patterns))
      if scoretarg != target:
        outfile.write("%s\t%s\n" % (prefix, scoretarg))
    else:
      for splittarg in applysplit([target,], patterns):
        if splittarg != target and args.mods:
          outfile.write("%s\t%s\n" % (prefix, splittarg.strip()))


if __name__ == '__main__':
  main()
