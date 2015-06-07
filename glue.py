#!/usr/bin/env python
from __future__ import print_function

import pykeyboard
import re
import sys

ALPHABET = [
    'alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot', 'golf',
    'hotel', 'india', 'juliet', 'kilo', 'lima', 'mike',
    'november', 'oscar', 'papa', 'quebec', 'romeo', 'sierra', 'tango',
    'uniform', 'victor', 'whiskey', 'x-ray', 'yankee', 'zebra'
]

NUMBERS = [
    (1, 'one'), (2, 'two'), (3, 'three'), (4, 'four'), (5, 'five'),
    (6, 'six'), (7, 'seven'), (8, 'eight'), (9, 'nine'), (10, 'ten')
]

CODE_COMMANDS = {
    'big': {},
    'control': {},
    'alternate': {},

    'escape': '<Esc>',
    'delete': '<BS>',
    'tab': '<Tab>',

    'quote': '"',

    'plus': ' + ',
    'minus': ' - ',
    'times': ' * ',
    'divided': {'by': ' / '},
    'equals': ' = ',
    'not': {'equals': ' != '},
    'double': {'equals': ' == '},
    'triple': {
        'equals': ' === ',
        'not': {'equals': ' !== '}
    },
    'greater': {
        'than': ' > ',
        'equals': ' >= '
    },
    'less': {
        'than': ' < ',
        'equals': ' <= '
    },
    'plus': {
        'equals': ' += '
    },
    'minus': {
        'equals': ' -= '
    },
    '&&': ' && ',  # dragon turns 'logical and' into this
    '||': ' || ',
}

# add lower-case, upper-case, control and alt letters
for word in ALPHABET:
    CODE_COMMANDS[word] = word[0]
    CODE_COMMANDS['big'][word] = word[0].upper()
    CODE_COMMANDS['control'][word] = '<C-{0}>'.format(word[0])
    CODE_COMMANDS['alternate'][word] = '<A-{0}>'.format(word[0])

# alt-number
for i in NUMBERS:
    CODE_COMMANDS['alternate'][i[0]] = '<A-{0}>'.format(i[0])
    CODE_COMMANDS['alternate'][i[1]] = '<A-{0}>'.format(i[0])


#   COMMAND_DEF['big {0}'.format(word)] = word[0].upper()
#   COMMAND_DEF['control {0}'.format(word)] = '<C-{0}>'.format(word[0])
#   #currently disabled in grammar
#   COMMAND_DEF['alt {0}'.format(word)] = '<A-{0}>'.format(word[0])
#COMMAND_DEF = {
#}
#COMMAND_DEF.update({

#   'exclamation': '!',
#   'quote': '"',
#   'dollar': '$',
#   'percent': '%',
#   'acute': '^',
#   'ampersand': '&',
#   'star': '*',
#   'bracket': '(',
#   'unbracket': ')',
#   #'raw minus': '-',
#   #'raw plus': '+',
#   #'raw equals': '=',
#   'underscore': '_',
#   'index': '[',
#   'unindex': ']',
#   'brace': '{',
#   'unbrace': '}',
#   'angle': '<',
#   'unangle': '>',
#   'hashtag': '#',
#   'apostrophe': '\'',
#   'colon': ':',
#   'clause': ';',
#   'curly thing': '~',
#   'curly at': '@',
#   'tick': ',',
#   'dot': '.',
#   'question': '?',
#   'slash': '/',
#   'pipe': '|',
#   'backslash': '\\',
#   'backtick': '`',

#   'assign': ' =',
#   'equals': ' ==',
#   'plus': ' +',
#   'minus': ' -',
#   'times': ' *',
#   'divided by': ' /',
#   'not equals': ' !=',
#   #'code percent': ' % ',
#   'greater than': ' >',
#   'less than': ' <',
#   'logical or': ' ||',
#   'logical and': ' &&',
#)


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
        self.encountered_space_after_identifier = False

    def handle_as_command(self, word):
        # Traverses CODE_COMMANDS tree seeing if the spoken commands
        # can match. if so issue command keypresses, if not then push
        # back the keys we have peeked at so they can be handled as
        # normal voice entry.
        def match_command(word, command_tree):
            if word in command_tree:
                if isinstance(command_tree[word], dict):
                    _space = self.keypresser.next_input_fragment()
                    next_word = self.keypresser.next_input_fragment()
                    if match_command(next_word.lower(), command_tree[word]):
                        return True
                    else:
                        self.keypresser.push_back_fragment(next_word)
                        self.keypresser.push_back_fragment(_space)
                        return False
                elif isinstance(command_tree[word], basestring):
                    # matched a command finally! issue it
                    self.keypresser.emit_keypresses(command_tree[word])
                    return True
                else:
                    assert False

        return match_command(word, CODE_COMMANDS)

    def parse(self, word):
        word = word.lower()
        if len(word) == 0:
            return

        print ("CODE ({0})".format(word), end="\r\n")

        # special command to change code language
        if word == 'language':
            # next 2 fragments (1 is space)
            _space = self.keypresser.next_input_fragment()
            wanted_lang = self.keypresser.next_input_fragment().lower()
            if wanted_lang == 'javascript':
                self.language = LANG_JAVASCRIPT
                print("LANGUAGE JAVASCRIPT")
                return
            elif wanted_lang == 'pie':
                self.language = LANG_PYTHON
                print("LANGUAGE PYTHON")
                return
            else:
                # push back those 2 words we peeked at since 'language' is
                # going to be handled as an identifier
                self.keypresser.push_back_fragment(wanted_lang)
                self.keypresser.push_back_fragment(_space)

        if word == ' ':
            # we don't echo the spaces in code mode, since spaces are generally
            # inserted by specific operator commands
            if self.last_word_was_identifier:
                self.encountered_space_after_identifier = True
            #else:
            #    self.keypresser.emit_keypresses(' ')
            return

        if self.handle_as_command(word):
            self.last_word_was_identifier = False
            return

        elif word.isalpha():
            # part of an identifier
            if self.last_word_was_identifier:
                if self.language == LANG_JAVASCRIPT:
                    # camel-case identifiers
                    word = word[0].upper() + word[1:]
                elif self.language == LANG_PYTHON and self.encountered_space_after_identifier:
                    self.keypresser.emit_keypresses('_')

            self.keypresser.emit_keypresses(word)
            self.last_word_was_identifier = True
            self.encountered_space_after_identifier = False

        else:
            # symbol, number or some other shit
            self.keypresser.emit_keypresses(word)
            self.last_word_was_identifier = False


class Keypresser(object):
    def __init__(self):
        self.kb = pykeyboard.PyKeyboard()
        self.commands_enabled = True
        self.mode_code = ModeCode(self)
        self.mode_dictation = ModeDictation(self)
        self.current_mode = self.mode_dictation
        self.current_mode.switch_to()
        self._words_in = input_word_generator()
        # words that might have been pushed back by a parser
        self._words_queued = []

    def next_input_fragment(self):
        print ("Word queue: ", self._words_queued, end="\r\n")
        if len(self._words_queued):
            return self._words_queued.pop()

        else:
            return self._words_in.next()

    def push_back_fragment(self, frag):
        self._words_queued.append(frag)

    def loop(self):

        while True:
            word = self.next_input_fragment()
            print ("Yielded "+repr(word), end="\r\n")

            # special handling of mode change command
            if word.lower() == 'mode':
                # next 2 fragments (1 is space)
                _space = self.next_input_fragment()
                wanted_mode = self.next_input_fragment().lower()
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
                    self.current_mode.parse('')
                    self.current_mode.parse(wanted_mode)

                continue

            self.current_mode.parse(word)

    def tap_key(self, char):
        try:
            self.kb.tap_key(char)
        except KeyError:
            # error looking up keysym
            pass

    def emit_modified(self, char, modifier):
        self.kb.press_key(modifier)
        self.tap_key(char)
        self.kb.release_key(modifier)

    #def emit(self, string):
    #    self.kb.type_string(string)

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
                self.tap_key(keypresses[0])
                keypresses = keypresses[1:]

if __name__ == '__main__':
    kp = Keypresser()
    kp.loop()
