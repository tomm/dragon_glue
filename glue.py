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

# simple key expansions that split operators but do not end operator mode 
CODE_EXPANSIONS = {
    'blank': ' ',
    '\xc2\x96': '-',
    'quote': '"',
    'tick': '\'',
    'raw': {'space': ' '},
    'square': '[',
    'unsquare': ']',
    'angle': '<',
    'unangle': '>',
    'bracket': '(',
    'unbracket': ')',

    'dereference': '->',
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
    '&&': ' && ',
    '||': ' || ',
}

# commands that end identifier mode 
CODE_COMMANDS = {
    'escape': '<Esc>',
    'tab': '<Tab>',

    '\x7f': '<BS>',
    '\x1b[11~': '<F1>',
    '\x1b[12~': '<F2>',
    '\x1b[13~': '<F3>',
    '\x1b[14~': '<F4>',
    '\x1b[15~': '<F5>',
    '\x1b[17~': '<F6>',
    '\x1b[18~': '<F7>',
    '\x1b[19~': '<F8>',
    '\x1b[20~': '<F9>',
    '\x1b[21~': '<F10>',
    '\x1b[23~': '<F11>',
    '\x1b[24~': '<F12>',
    '\x1b[a': '<Up>',
    '\x1b[b': '<Down>',
    '\x1b[d': '<Left>',
    '\x1b[c': '<Right>',
}


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

    # characters that may be mixed in with [A-Za-z] letters without splitting the word
    NON_SPLITTERS = "-'"

    word = ''
    word_timeout = 0
    while True:
        try:
            char = sys.stdin.read(1)

            if word == '':
                word_timeout = time.time() + WORD_TIMEOUT

            if char == '\x1b':
                # terminal escape code for special keys. read to terminating ~
                word += char
                # XXX note will timeout and be emitted for sequences not ending ~,
                # but should recognise them more sanely...
                while word[-1] != '~':
                    word += sys.stdin.read(1)
                yield(word)
                word = ''
            elif char == '\r' or char == '\n':
                yield(word)
                yield('\n')
                word = ''
            elif char == ' ':
                yield(word)
                yield(' ')
                word = ''
            elif len(word)>0 and char not in NON_SPLITTERS and char.isalpha() != word[0].isalpha():
                yield(word)
                word = char
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


class EntryMode(object):
    def __init__(self, separator, caps, capitalize_first, capitalize_subsequent,
            end_entry_on, separator_after_last_word, suppress_dragon_spaces):
        assert caps in (None, 'upper', 'lower')
        self.separator = separator
        self.caps = caps
        self.capitalize_first = capitalize_first
        self.capitalize_subsequent = capitalize_subsequent
        self.end_entry_on = end_entry_on
        self.separator_after_last_word = separator_after_last_word
        self.suppress_dragon_spaces = suppress_dragon_spaces

    def transform_word(self, word, mode_code):
        if self.caps:
            word = getattr(word, self.caps)()

        if self.capitalize_first and mode_code.current_identifier_length == 0:
            word = word[0].upper() + word[1:]

        if self.capitalize_subsequent and mode_code.current_identifier_length > 0:
            word = word[0].upper() + word[1:]

        if self.separator_after_last_word and self.separator:
            word = word + self.separator

        elif mode_code.current_identifier_length > 0 and self.separator:
            # not the first word, so add a separator
            word = self.separator + word

        return word


class CharacterEntryMode(EntryMode):
    """Single character entry, using first letter of word as character."""
    def __init__(self):
        super(CharacterEntryMode, self).__init__('', 'lower', False, False, (), False, True)

    def transform_word(self, word, mode_code):
        return word[0].lower()


class CapitalEntryMode(EntryMode):
    def __init__(self):
        super(CapitalEntryMode, self).__init__(None, 'lower', True, True, ('<Esc>', '\n'), False, True)

    def transform_word(self, word, mode_code):
        word = super(CapitalEntryMode, self).transform_word(word, mode_code)

        # special case. always capitalize all of 'ID'
        if word.lower() == 'id':
            return 'ID'
        else:
            return word


class ModeCode(SpeechMode):

    ENTRY_MODES = {
        'spell': CharacterEntryMode(),
        'capital': CapitalEntryMode(),
        'camel': EntryMode(None, 'lower', False, True, ('<Esc>', '\n'), False, True),
        'line': EntryMode('_', 'lower', False, False, ('<Esc>', '\n'), False, True),
        'strike': EntryMode('-', 'lower', False, False, ('<Esc>', '\n'), False, True),
        'spacey': EntryMode(' ', 'lower', False, False, ('<Esc>', '\n'), False, True),
        'squeeze': EntryMode(None, 'lower', False, False, ('<Esc>', '\n'), False, True),
        'sequel': EntryMode(' ', 'upper', False, False, ('<Esc>', '\n'), True, True),
        'keyword': EntryMode(' ', 'lower', False, False, ('<FirstWord>', '<Esc>', '\n'), True, True),
        'single': EntryMode(None, 'lower', False, False, ('<FirstWord>', '<Esc>', '\n'), False, True),
        'constant': EntryMode('_', 'upper', False, False, ('<Esc>', '\n'), False, True),
        'dictate': EntryMode(None, None, True, False, ('<Esc>', '\n'), False, False)
    }

    def __init__(self, keypresser):
        self.keypresser = keypresser
        self.key_mods = set([])
        # don't interpret next word as a command or expansion
        self.escape_next_word = False
        self.current_identifier_length = 0
        # just a stack of integer length of previously entered words
        self.undo_stack = []
        self.entry_mode = ModeCode.ENTRY_MODES['spell']

    def switch_to(self):
        super(ModeCode, self).__init__()
        self.entry_mode = ModeCode.ENTRY_MODES['spell']

    def set_key_mod(self, val):
        if val != 'shift':
            # end identifier runs on pressing mod keys (except shift)
            self.set_entry_mode('spell')
        self.key_mods.add(val)

    def set_escape_next_word(self):
        self.escape_next_word = True

    def emit_keypresses(self, keys, add_to_undo_stack=True):
        if 'shift' in self.key_mods:
            i = 0
            for i in xrange(0, len(keys)):
                if keys[i].isalpha():
                    break
            if i < len(keys):
                keys = keys[0:i] + keys[i].upper() + keys[i+1:]
        if 'control' in self.key_mods:
            self.keypresser.emit_keypresses('<C-{0}>'.format(keys[0].lower()))
            keys = keys[1:]
            add_to_undo_stack = False
        if 'alternate' in self.key_mods:
            self.keypresser.emit_keypresses('<A-{0}>'.format(keys[0].lower()))
            keys = keys[1:]
            add_to_undo_stack = False
        if 'win' in self.key_mods:
            self.keypresser.emit_keypresses('<Mod4-{0}>'.format(keys[0].lower()))
            keys = keys[1:]
            add_to_undo_stack = False

        if keys != ' ':
            # wipe modifiers on all keys but space
            # XXX not space because flow will be: ('big', ' ', 'word')
            self.key_mods = set([])

        if len(keys) > 0:
            self.keypresser.emit_keypresses(keys)
            if add_to_undo_stack:
                self.undo_stack.append(len(keys))
                # maximum undo stack length
                self.undo_stack = self.undo_stack[-30:]

    def handle_as_expansion(self, word):
        return self.keypresser.match_command(
            word,
            CODE_EXPANSIONS,
            strip_spaces_from_keypresses=self.entry_mode == ModeCode.ENTRY_MODES['squeeze']
        )

    def handle_as_command(self, word):
        return self.keypresser.match_command(
            word,
            CODE_COMMANDS,
            strip_spaces_from_keypresses=self.entry_mode == ModeCode.ENTRY_MODES['squeeze']
        )

    def set_entry_mode(self, type):
        self.current_identifier_length = 0
        self.entry_mode = ModeCode.ENTRY_MODES[type]

    def split_identifier(self):
        """and previous operator and start new operator of same type"""
        self.current_identifier_length = 0

    def delete_last_word(self):
        print (self.undo_stack)
        if len(self.undo_stack) > 0:
            length = self.undo_stack.pop()
            self.current_identifier_length -= length
            if self.current_identifier_length == 0:
                # if we deleted our way all the way to the start, remember we're starting an identifier
                self.split_identifier()
            self.emit_keypresses('<BS>' * length, add_to_undo_stack=False)

    def delete_current_identifier(self):
        if self.current_identifier_length > 0:
            self.emit_keypresses('<BS>' * self.current_identifier_length, add_to_undo_stack=False)
            self.split_identifier()
            
    def parse(self, word):
        if len(word) == 0:
            return

        if word != ' ': print ("SAID '{0}'".format(word), end="\r\n")

        # special command to change code language or enter variable names
        if not self.escape_next_word and self.keypresser.match_command(
            word.lower(), {
                # end identifier entry and return to single keypress mode
                'delete': self.delete_last_word,
                'junk': self.delete_current_identifier,
                'literal': self.set_escape_next_word,
                'spell': functools.partial(self.set_entry_mode, 'spell'),
                'capital': functools.partial(self.set_entry_mode, 'capital'),
                'camel': functools.partial(self.set_entry_mode, 'camel'),
                'line': functools.partial(self.set_entry_mode, 'line'),
                'strike': functools.partial(self.set_entry_mode, 'strike'),
                'spacey': functools.partial(self.set_entry_mode, 'spacey'),
                'squeeze': functools.partial(self.set_entry_mode, 'squeeze'),
                'sequel': functools.partial(self.set_entry_mode, 'sequel'),
                'keyword': functools.partial(self.set_entry_mode, 'keyword'),
                'single': functools.partial(self.set_entry_mode, 'single'),
                'constant': functools.partial(self.set_entry_mode, 'constant'),
                'dictate': functools.partial(self.set_entry_mode, 'dictate'),
                'big': functools.partial(self.set_key_mod, 'shift'),
                'alternate': functools.partial(self.set_key_mod, 'alternate'),
                'control': functools.partial(self.set_key_mod, 'control'),
                'windows': {
                    'key': functools.partial(self.set_key_mod, 'win'),
                }
            }
        ):
            # matched language command. done
            print ("Command "+word.lower(), end="\r\n")
            return

        if word == ' ':
            if self.entry_mode.suppress_dragon_spaces is False and \
                    self.current_identifier_length > 0:
                self.emit_keypresses(' ')

            return

        if not self.escape_next_word and self.handle_as_command(word.lower()):
            self.set_entry_mode('spell')
            return

        elif self.entry_mode.suppress_dragon_spaces is True and \
                not self.escape_next_word and \
                self.handle_as_expansion(word.lower()):
            self.split_identifier()
            return

        elif word[0].isalpha():
            word = self.entry_mode.transform_word(word, self)

            self.current_identifier_length += len(word)
            self.emit_keypresses(word)

        else:
            if word == '\n':
                # end identifier entry on newline
                self.set_entry_mode('spell')
            elif self.entry_mode.suppress_dragon_spaces is True:
                # split the identifier on other symbol entry
                self.split_identifier()
            self.emit_keypresses(word[0])
            self.parse(word[1:])

        # clear escaping flag since 'next word' has happened
        self.escape_next_word = False


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
            word = self._words_queued.pop()
        else:
            word = self._words_in.next()
        #print('raw: \'{0}\''.format(repr(word)))
        return word

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

    def match_command(self, word, command_tree, strip_spaces_from_keypresses=False):
        # Traverses command_tree seeing if the spoken commands
        # can match. if so issue command keypresses, if not then push
        # back the keys we have peeked at so they can be handled by other routines.
        if word in command_tree:
            if isinstance(command_tree[word], dict):
                _space = self.next_input_fragment()
                next_word = self.next_input_fragment()
                if self.match_command(next_word.lower(), command_tree[word], strip_spaces_from_keypresses):
                    return True
                else:
                    self.push_back_fragment(next_word)
                    self.push_back_fragment(_space)
                    return False
            elif isinstance(command_tree[word], basestring):
                # matched a command finally! issue it
                if strip_spaces_from_keypresses:
                    cmd = command_tree[word].strip()
                else:
                    cmd = command_tree[word]
                self.emit_keypresses(cmd)
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
        print ("KEY: " + repr(keypresses), end='\r\n')
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
            elif re.match(r'^<Mod4\-(\w)>', keypresses):
                char = re.match(r'^<Mod4\-(\w)>', keypresses).groups()[0]
                self.emit_modified(char, self.kb.super_l_key)
                keypresses = keypresses[8:]
            elif re.match(r'^<F(\d+)>', keypresses):
                num = re.match(r'^<F(\d+)>', keypresses).groups()[0]
                self.kb.tap_key(self.kb.function_keys[int(num)])
                keypresses = keypresses[3+len(num):]
            elif keypresses[:4] == '<Up>':
                self.kb.tap_key(self.kb.up_key)
                keypresses = keypresses[4:]
            elif keypresses[:6] == '<Down>':
                self.kb.tap_key(self.kb.down_key)
                keypresses = keypresses[6:]
            elif keypresses[:6] == '<Left>':
                self.kb.tap_key(self.kb.left_key)
                keypresses = keypresses[6:]
            elif keypresses[:7] == '<Right>':
                self.kb.tap_key(self.kb.right_key)
                keypresses = keypresses[7:]
            else:
                self.tap_key(keypresses[0])
                keypresses = keypresses[1:]

if __name__ == '__main__':
    kp = Keypresser()
    kp.loop()
