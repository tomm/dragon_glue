#!/usr/bin/env python
from __future__ import print_function

import pykeyboard
import re
import sys

ALPHABET = [
    'alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot', 'golf',
    'hotel', 'india', 'juliett', 'kilo', 'lima', 'mike',
    'november', 'oscar', 'papa', 'quebec', 'romeo', 'sierra', 'tango',
    'uniform', 'victor', 'whiskey', 'x-ray', 'yankee', 'zebra'
]

COMMAND_DEF = {
    # system commands
    'system off': None,
    'system on': None,
}

# add lower-case, upper-case, control and alt letters
for word in ALPHABET:
    COMMAND_DEF[word] = word[0]
    COMMAND_DEF['big {0}'.format(word)] = word[0].upper()
    COMMAND_DEF['control {0}'.format(word)] = '<C-{0}>'.format(word[0])
    #currently disabled in grammar
    COMMAND_DEF['alt {0}'.format(word)] = '<A-{0}>'.format(word[0])

for i in range(0, 10):
    COMMAND_DEF['alt {0}'.format(i)] = '<A-{0}>'.format(i)

COMMAND_DEF.update({
    'string': None,
    'number': None,

    # generic keypress stuff
    '9': '9',
    '8': '8',
    '7': '7',
    '6': '6',
    '5': '5',
    '4': '4',
    '3': '3',
    '2': '2',
    '1': '1',
    '0': '0',
    '10': '10',

    'space': ' ',
    'key': None,
    'escape': '<Esc>',
    'new line': '<Return>',
    'delete': '<BS>',
    'tab': '<Tab>',

    'exclamation': '!',
    'quote': '"',
    'dollar': '$',
    'percent': '%',
    'acute': '^',
    'ampersand': '&',
    'star': '*',
    'bracket': '(',
    'unbracket': ')',
    #'raw minus': '-',
    #'raw plus': '+',
    #'raw equals': '=',
    'underscore': '_',
    'index': '[',
    'unindex': ']',
    'brace': '{',
    'unbrace': '}',
    'angle': '<',
    'unangle': '>',
    'hashtag': '#',
    'apostrophe': '\'',
    'colon': ':',
    'clause': ';',
    'curly thing': '~',
    'curly at': '@',
    'tick': ',',
    'dot': '.',
    'question': '?',
    'slash': '/',
    'pipe': '|',
    'backslash': '\\',
    'backtick': '`',

    'assign': ' = ',
    'equals': ' == ',
    'plus': ' + ',
    'minus': ' - ',
    'times': ' * ',
    'divided by': ' / ',
    'not equals': ' != ',
    #'code percent': ' % ',
    'greater than': ' > ',
    'less than': ' < ',
    'logical or': ' || ',
    'logical and': ' && ',

   #'keyword class': 'class ',
    'keyword function': 'function',
    'keyword else': 'else',
    'keyword break': 'break',
    'keyword continue': 'continue',
    'keyword return': 'return',
   #'keyword for': 'for ',
   #'keyword if': 'if ',
   #'keyword python true': 'True',
   #'keyword python false': 'False',
   #'keyword python self': 'self',
   #'keyword python deaf': 'def ',
   #'keyword python import': 'import ',
   #'keyword python none': 'None',
})


def input_word_generator():
    import tty
    import time
    import fcntl
    import os
    tty.setcbreak(sys.stdin)
    # make stdin a non-blocking file
    fd = sys.stdin.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    # seconds dragon has to complete typing a word before we chop it up!
    WORD_TIMEOUT = 0.1

    word = ''
    word_timeout = 0
    while True:
        try:
            char = sys.stdin.read(1)

            if word == '':
                word_timeout = time.time() + WORD_TIMEOUT

            if char == '\r' or char == '\n':
                yield(word)
                yield('\n')
                word = ''
            elif char == ' ':
                yield(word)
                yield(' ')
                word = ''
            else:
                word += char
        except IOError:
            if time.time() > word_timeout and word != '':
                yield word
                word = ''
            time.sleep(0.1)


class SpeechMode(object):

    def switch_to(self):
        pass


class ModeDictation(SpeechMode):

    def __init__(self, keypresser):
        self.keypresser = keypresser

    def switch_to(self):
        super(ModeDictation, self).__init__()

    def parse(self, word):
        self.keypresser.emit_keypresses(word)

LANG_PYTHON = 0
LANG_JAVASCRIPT = 1

class ModeCode(SpeechMode):

    def __init__(self, keypresser):
        self.keypresser = keypresser
        self.language = LANG_PYTHON

    def switch_to(self):
        super(ModeCode, self).__init__()
        self.last_word_was_identifier = False

    def parse(self, word):
        word = word.lower()
        print ("CODE ({0})".format(word), end="\r\n")

        # special command to change code language
        if word == 'language':
            # next 2 fragments (1 is space)
            wanted_lang = self.keypresser.next_input_fragments(2).strip().lower()
            if wanted_lang == 'javascript':
                self.language = LANG_JAVASCRIPT
                print("LANGUAGE JAVASCRIPT")
            elif wanted_lang == 'pie':
                self.language = LANG_PYTHON
                print("LANGUAGE PYTHON")

            return

        elif word == ' ':
            if self.last_word_was_identifier:
                if self.language == LANG_PYTHON:
                    self.keypresser.emit_keypresses('_')
            else:
                self.keypresser.emit_keypresses(' ')

        elif word.isalpha():
            # part of an identifier
            if self.last_word_was_identifier and self.language == LANG_JAVASCRIPT:
                # camel-case identifiers
                word = word[0].upper() + word[1:]
            self.keypresser.emit_keypresses(word)
            self.last_word_was_identifier = True

        else:
            self.keypresser.emit_keypresses(word)
            self.last_word_was_identifier = False


##      utterance = utterance.lower()

##      # silly padding at end to help dumb matching
##      utterance = utterance + ' '

##      while len(utterance) > 0:

##          matched = False
##          for cmd in COMMAND_DEF:
##              if utterance[:len(cmd)+1] == cmd+' ':
##                  # strip out successfully matched command
##                  utterance = utterance[len(cmd)+1:]
##                  self.last_word_was_identifier = False

##                  if COMMAND_DEF[cmd] is not None:
##                      # normal commands
##                      print ("Emitting translated keypress command: " + cmd, end="\r\n")
##                      self.keypresser.emit_keypresses(COMMAND_DEF[cmd])
##                  else:
##                      # system commands
##                      print ("Emitting system comand: " + cmd, end="\r\n")
##                      #system_command(cmd)

##                  matched = True
##                  break
##          if matched is False:
##              text = utterance[:utterance.find(' ')]
##              print ("Emitting literal ({0})".format(text), end="\r\n")
##              if self.last_word_was_identifier is True:
##                  self.keypresser.emit_keypresses(self.identified_separator)
##              self.keypresser.emit_keypresses(text)
##              self.last_word_was_identifier = True
##              # skip to next word
##              utterance = utterance[len(text)+1:]


class Keypresser(object):
    def __init__(self):
        self.kb = pykeyboard.PyKeyboard()
        self.commands_enabled = True
        self.mode_code = ModeCode(self)
        self.mode_dictation = ModeDictation(self)
        self.current_mode = self.mode_dictation
        self.current_mode.switch_to()
        self._words_in = input_word_generator()

    def next_input_fragments(self, num=1):
        output = ''
        while num > 0:
            output += self._words_in.next()
            num -= 1
        return output

    def loop(self):

        while True:
            word = self.next_input_fragments()
            print ("Yielded "+repr(word), end="\r\n")

            # special handling of mode change command
            if word.lower() == 'mode':
                # next 2 fragments (1 is space)
                wanted_mode = self.next_input_fragments(2).strip().lower()
                print ("Wanted mode: ", wanted_mode, end="\r\n")

                if wanted_mode == 'code':
                    print ("ENTERED MODE CODE", end="\r\n")
                    self.current_mode = self.mode_code
                    self.current_mode.switch_to()

                elif wanted_mode == 'dictation':
                    print ("ENTERED MODE DICTATION", end="\r\n")
                    self.current_mode = self.mode_dictation
                    self.current_mode.switch_to()

                else:
                    # didn't get a valid mode command. pass words
                    # to speech mode parse method
                    self.current_mode.parse('mode')
                    self.current_mode.parse(wanted_mode)

                continue

            self.current_mode.parse(word)

    def emit_modified(self, char, modifier):
        self.kb.press_key(modifier)
        self.kb.tap_key(char)
        self.kb.release_key(modifier)

    def emit(self, string):
        self.kb.type_string(string)

    def emit_keypresses(self, keypresses):
        while len(keypresses) > 0:
            if keypresses[:5] == '<Esc>':
                self.kb.tap_key(self.kb.escape_key)
                keypresses = keypresses[5:]
            elif keypresses[:8] == '<Return>':
                self.kb.tap_key(self.kb.return_key)
                keypresses = keypresses[8:]
            elif keypresses[:4] == '<BS>':
                self.kb.tap_key(self.kb.backspace_key)
                keypresses = keypresses[4:]
            elif keypresses[:5] == '<Tab>':
                self.kb.tap_key(self.kb.tab_key)
                keypresses = keypresses[5:]
            elif re.match(r'^<C\-(\w)>', keypresses):
                char = re.match(r'^<C\-(\w)>', keypresses).groups()[0]
                self.emit_modified(char, self.kb.control_key)
                keypresses = keypresses[5:]
            elif re.match(r'^<A\-(\w)>', keypresses):
                char = re.match(r'^<A\-(\w)>', keypresses).groups()[0]
                self.emit_modified(char, self.kb.alt_key)
                keypresses = keypresses[5:]
            else:
                self.kb.tap_key(keypresses[0])
                keypresses = keypresses[1:]

if __name__ == '__main__':
    kp = Keypresser()
    kp.loop()
