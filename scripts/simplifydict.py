#!/usr/bin/env python3

# dict2inst (various approaches): given a dictionary, come up with a set of
# modification instructions for it

# simplifydict (this): given a dictionary and its instruction set, return a modified dictionary

# scoredict: given a dictionary, a partially scored parallel corpus, and a set of entries to modify, apply the entries to the corpus and return the score

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



# instruction set: map of instruction to state modification function
# state: set of source -> target* entries, specification of a single entry and its position



class Definition:
  """ 
  list of words paired with instructions OR
  lists of word strings OR
  a mix of the two, plus a ternary flag indicating progress
  """
  PRE = "pre"
  MID = "mid"
  POST = "post"
  # legal moves: interface must be simply 'state'
  moves = {}
  def keep(self, state):
    """ move the word to the current definition """
    self.defs[-1].append(self.queue.pop(0)[0])
  moves["K"] = keep
  def delete(self, state):
    """ ignore the word """
    self.queue.pop(0)
  moves["D"] = delete
  def split(self, state):
    """ start a new definition """
    self.defs.append([])
    self.queue.pop(0)
  moves["S"] = split
  def transfer(self, state):
    """ insert results from another defintion """
    stub = self.defs.pop()
    word = self.queue.pop(0)[0]
    state.process(word)
    for res in state.get(word).defs:
      self.defs.append(stub+res)
  moves["T"] = transfer

  def __init__(self)
    self.state = Definition.PRE
    self.queue = []
    self.defs = [[]]

  def merge(self, text, instruction):
    if self.state is not Definition.PRE:
      raise Exception("Can only merge in PRE state")
    for tw, iw in zip(split(text), split(instruction)):
      self.queue.append((tw, moves[iw]))

  def process(self, state):
    """ consume instructions """
    if self.state==Definition.POST:
      return
    self.state = Definition.MID
    while len(self.queue) > 0:
      self.queue[0][1](state)
    # unravel
    self.defs = [item for sublist in self.defs for item in sublist]:
    self.state = Definition.POST


class State:
  """
  all the entries, processed and unprocessed, of a dictionary
  """

  def __init__(self, textfile, instructionfile):
    self.entries = dd(Definition)
    for tline, iline in izip(textfile, instructionfile):
      tline = tline.strip().split('\t')
      self.entries[tline[0]].merge((tline[1], iline.strip()))
  def get(self, word):
    self.process(word)
    return self.entries.get(word)
  def process(self, word=None):
    words = [self.entries.keys()] if word is None else [word,]
    for w in words:
      self.entries.get(w).process(self)


def main():
  parser = argparse.ArgumentParser(description="Given a dictionary and per-word instructions for the dictionary, output a modified dictionary",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  addonoffarg(parser, 'debug', help="debug mode", default=False)
  parser.add_argument("--dictfile", "-d", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="dictionary file")
  parser.add_argument("--instfile", "-i", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="instruction file")
  parser.add_argument("--outfile", "-o", nargs='?', type=argparse.FileType('w'), default=sys.stdout, help="output file")




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


  instfile = prepfile(args.instfile, 'r')
  dictfile = prepfile(args.dictfile, 'r')
  outfile = prepfile(args.outfile, 'w')


  dictstate = State(dictfile, instfile)
  dictstate.process()
  for sword in dictstate.entries.keys():
    for definition in dictstate.get(sword):
      outfile.write("%s\t\%s\n" % (sword, ' '.join(definition)))

if __name__ == '__main__':
  main()
