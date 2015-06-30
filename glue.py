#!/usr/bin/env python
from __future__ import print_function

import pykeyboard
import re
import sys
import os
import functools

#   ALPHABET = [
#       'alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot', 'golf',
#       'hotel', 'india', 'juliet', 'kilo', 'lima', 'mike',
#       'november', 'oscar', 'papa', 'quebec', 'romeo', 'sierra', 'tango',
#       'uniform', 'victor', 'whiskey', 'x-ray', 'yankee', 'zulu'
#   ]

#   NUMBERS = [
#       (1, 'one'), (2, 'two'), (3, 'three'), (4, 'four'), (5, 'five'),
#       (6, 'six'), (7, 'seven'), (8, 'eight'), (9, 'nine'), (10, 'ten')
#   ]

CODE_COMMANDS = {
    'escape': '<Esc>',
    'delete': '<BS>',
    'tab': '<Tab>',
    'blank': ' ',

    'quote': '"',
    'raw': {'space': ' '},

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
    'increment': ' += ',
    'decrement': ' -= ',
    '&&': ' && ',  # dragon turns 'logical and' into this
    '||': ' || ',
}

# add lower-case, upper-case, control and alt letters
#   for word in ALPHABET:
#       CODE_COMMANDS[word] = word[0]
#       CODE_COMMANDS['big'][word] = word[0].upper()
#       CODE_COMMANDS['control'][word] = '<C-{0}>'.format(word[0])
#       CODE_COMMANDS['alternate'][word] = '<A-{0}>'.format(word[0])

# alt-number
#for i in NUMBERS:
#    CODE_COMMANDS['alternate'][i[0]] = '<A-{0}>'.format(i[0])
#    CODE_COMMANDS['alternate'][i[1]] = '<A-{0}>'.format(i[0])


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


def desktop_notification(message):
    pass
    #os.system("zenity --notification --text='{0}' &".format(message))
    #os.system("echo 'message: blah' | zenity --notification --listen'")


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
        self.just_switched_to_dictation = True

    def switch_to(self):
        super(ModeDictation, self).__init__()
        self.just_switched_to_dictation = True

    def parse(self, word):
        if word == ' ' and self.just_switched_to_dictation:
            # eat the first space after switching to this mode,
            # since it is spurious
            self.just_switched_to_dictation = False

            word = self.keypresser.next_input_fragment()
            # capitalize first word (since in this case Dragon won't do it for us)
            word = word[0].upper() + word[1:]

        self.keypresser.emit_keypresses(word)


class ModeCode(SpeechMode):

    LANG_PYTHON = {
        'name': 'Python'
    }
    LANG_JAVASCRIPT = {
        'name': 'JavaScript'
    }
    IDENTIFIER_CAPITAL = 0
    IDENTIFIER_CAMEL = 1
    IDENTIFIER_UNDERSCORE = 2
    IDENTIFIER_HYPHEN = 3
    IDENTIFIER_SPACEY = 4

    def __init__(self, keypresser):
        self.keypresser = keypresser
        self.language = ModeCode.LANG_PYTHON
        self.key_mods = set([])

    def switch_to(self):
        super(ModeCode, self).__init__()
        self.identifier_type = None
        self.next_letter_big = False
        self.next_letter_control = False
        self.next_letter_alt = False
        self.last_word_was_identifier = False
        self.encountered_space_after_identifier = False

    def set_key_mod(self, val):
        self.key_mods.add(val)

    def emit_keypresses(self, keys):
        if 'shift' in self.key_mods:
            keys = keys[0].upper() + keys[1:]
        if 'control' in self.key_mods:
            self.keypresser.emit_keypresses('<C-{0}>'.format(keys[0].lower()))
            keys = keys[1:]
        if 'alternate' in self.key_mods:
            self.keypresser.emit_keypresses('<A-{0}>'.format(keys[0].lower()))

        if keys != ' ':
            # wipe modifiers on all keys but space
            # XXX not space because flow will be: ('big', ' ', 'word')
            self.key_mods = set([])

        if len(keys) > 0:
            self.keypresser.emit_keypresses(keys)

    def handle_as_command(self, word):
        return self.keypresser.match_command(word, CODE_COMMANDS)

    def change_language(self, lang):
        self.start_identifier(None)
        self.language = lang
        print("LANGUAGE ", lang['name'])
        desktop_notification('Language: ' + lang['name'])

    def start_identifier(self, type):
        self.identifier_type = type
        self.last_word_was_identifier = False
        self.encountered_space_after_identifier = False

    def parse(self, word):
        word = word.lower()
        if len(word) == 0:
            return

        #print ("CODE ({0})".format(word), end="\r\n")

        # special command to change code language or enter variable names
        if self.keypresser.match_command(
            word, {
                'language': {
                    'javascript': functools.partial(self.change_language, ModeCode.LANG_JAVASCRIPT),
                    'pie': functools.partial(self.change_language, ModeCode.LANG_PYTHON),
                    'python': functools.partial(self.change_language, ModeCode.LANG_PYTHON),
                },
                'capital': functools.partial(self.start_identifier, ModeCode.IDENTIFIER_CAPITAL),
                'camel': functools.partial(self.start_identifier, ModeCode.IDENTIFIER_CAMEL),
                'line': functools.partial(self.start_identifier, ModeCode.IDENTIFIER_UNDERSCORE),
                'strike': functools.partial(self.start_identifier, ModeCode.IDENTIFIER_HYPHEN),
                'spacey': functools.partial(self.start_identifier, ModeCode.IDENTIFIER_SPACEY),
                'big': functools.partial(self.set_key_mod, 'shift'),
                'alternate': functools.partial(self.set_key_mod, 'alternate'),
                'control': functools.partial(self.set_key_mod, 'control'),
            }
        ):
            # matched language command. done
            print ("Command "+word, end="\r\n")
            return

        if word == ' ':
            # we don't echo the spaces in code mode, since spaces are generally
            # inserted by specific operator commands
            if self.last_word_was_identifier:
                self.encountered_space_after_identifier = True
            return

        if self.handle_as_command(word):
            self.start_identifier(None)
            return

        elif word[0].isalpha():
            # if not part of an identifier then ignore
            if self.identifier_type is None:
                self.start_identifier(None)
                #print ("Word outside of identifier: " + word + ". Emitting first letter.")
                self.emit_keypresses(word[0])
                return

            if self.identifier_type == ModeCode.IDENTIFIER_CAPITAL:
                word = word[0].upper() + word[1:]

            if self.last_word_was_identifier:
                if self.identifier_type == ModeCode.IDENTIFIER_CAMEL or \
                   self.identifier_type == ModeCode.IDENTIFIER_CAPITAL:
                    word = word[0].upper() + word[1:]
                elif self.identifier_type == ModeCode.IDENTIFIER_UNDERSCORE and self.encountered_space_after_identifier:
                    self.emit_keypresses('_')
                elif self.identifier_type == ModeCode.IDENTIFIER_HYPHEN and self.encountered_space_after_identifier:
                    self.emit_keypresses('-')
                elif self.identifier_type == ModeCode.IDENTIFIER_SPACEY and self.encountered_space_after_identifier:
                    self.emit_keypresses(' ')

            self.emit_keypresses(word)
            self.last_word_was_identifier = True
            self.encountered_space_after_identifier = False

        else:
            # symbol, number or some other shit
            self.emit_keypresses(word)


class Keypresser(object):
    def __init__(self):
        self.kb = pykeyboard.PyKeyboard()
        self.commands_enabled = True
        self.mode_code = ModeCode(self)
        self.mode_dictation = ModeDictation(self)
        self.current_mode = self.mode_code
        self.current_mode.switch_to()
        self._words_in = input_word_generator()
        # words that might have been pushed back by a parser
        self._words_queued = []

    def next_input_fragment(self):
        if len(self._words_queued):
            return self._words_queued.pop()
        else:
            return self._words_in.next()

    def push_back_fragment(self, frag):
        self._words_queued.append(frag)

    def loop(self):

        def _enter_mode_code():
            print ("ENTERED MODE CODE", end="\r\n")
            desktop_notification('Voice entry mode: Code')
            self.current_mode = self.mode_code
            self.current_mode.switch_to()

        def _enter_mode_dictation():
            print ("ENTERED MODE DICTATION", end="\r\n")
            desktop_notification('Voice entry mode: Dictation')
            self.current_mode = self.mode_dictation
            self.current_mode.switch_to()

        while True:
            word = self.next_input_fragment()

            # special handling of mode change command
            if self.match_command(
                word.lower(), {
                    'mode': {
                        'code': _enter_mode_code,
                        'dictation': _enter_mode_dictation
                    }
                }
            ):
                continue

            self.current_mode.parse(word)

    def match_command(self, word, command_tree):
        # Traverses command_tree seeing if the spoken commands
        # can match. if so issue command keypresses, if not then push
        # back the keys we have peeked at so they can be handled by other routines.
        if word in command_tree:
            if isinstance(command_tree[word], dict):
                _space = self.next_input_fragment()
                next_word = self.next_input_fragment()
                if self.match_command(next_word.lower(), command_tree[word]):
                    return True
                else:
                    self.push_back_fragment(next_word)
                    self.push_back_fragment(_space)
                    return False
            elif isinstance(command_tree[word], basestring):
                # matched a command finally! issue it
                self.emit_keypresses(command_tree[word])
                return True
            else:
                # assume action is callable
                command_tree[word]()
                return True

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
        print ("KP: " + repr(keypresses), end='\r\n')
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
