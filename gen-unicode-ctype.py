#!/usr/bin/python3
#
# Generate a Unicode conforming LC_CTYPE category from a UnicodeData file.
# Copyright (C) 2014 Free Software Foundation, Inc.
# This file is part of the GNU C Library.
# Contributed by Mike FABIAN <maiku.fabian@gmail.com>, 2014.
# Based on gen-unicode-ctype.c by Bruno Haible <haible@clisp.cons.org>, 2000.
#
# The GNU C Library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# The GNU C Library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with the GNU C Library; if not, see
# <http://www.gnu.org/licenses/>.

import argparse
import sys
import time
import re

unicode_attributes = {}
derived_core_properties = {}

def fill_attribute(code_point, fields):
    unicode_attributes[code_point] =  {
        'name': fields[1],
        'category': fields[2],
        'combining': fields[3],
        'bidi': fields[4],
        'decomposition': fields[5],
        'decdigit': fields[6],
        'digit': fields[7],
        'numeric': fields[8],
        'mirrored': fields[9],
        'oldname': fields[10],
        'comment': fields[11],
        'upper': int(fields[12], 16) if fields[12] else None,
        'lower': int(fields[13], 16) if fields[13] else None,
        'title': int(fields[14], 16) if fields[14] else None,
    }

def fill_attributes(filename):
    with open(filename, mode='r') as file:
        lines = file.readlines()
        for lineno in range(0, len(lines)):
            fields = lines[lineno].strip().split(';')
            if len(fields) != 15:
                sys.stderr.write(
                    'short line in file "%(f)s": %(l)s\n' %{
                    'f': filename, 'l': lines[lineno]})
                exit(1)
            if fields[2] == 'Cs':
                # Surrogates are UTF-16 artefacts,
                # not real characters. Ignore them.
                continue
            if fields[1].endswith(', Last>'):
                continue
            if fields[1].endswith(', First>'):
                fields[1] = fields[1].split(',')[0][1:]
                fields_end = lines[lineno+1].split(';')
                if (not fields_end[1].endswith(', Last>')
                    or len(fields_end) != 15):
                    sys.stderr.write(
                        'missing end range in file "%(f)s": %(l)s\n' %{
                        'f': filename, 'l': lines[lineno+1]})
                for code_point in range(
                        int(fields[0], 16),
                        int(fields_end[0], 16)+1):
                    fill_attribute(code_point, fields)
            fill_attribute(int(fields[0], 16), fields)

def fill_derived_core_property(code_point, property):
    if code_point in derived_core_properties:
        derived_core_properties[code_point].append(property)
    else:
        derived_core_properties[code_point] = [property]

def fill_derived_core_properties(filename):
    with open(filename, mode='r') as file:
        for line in file:
            match = re.match(
                r'^(?P<codepoint>[0-9A-F]{4,6})\s*;\s*(?P<property>[a-zA-Z_]+)',
                line)
            if match:
                fill_derived_core_property(
                    int(match.group('codepoint'), 16),
                    match.group('property'))
            match = re.match(
                r'^(?P<codepoint1>[0-9A-F]{4,6})\.\.(?P<codepoint2>[0-9A-F]{4,6})\s*;\s*(?P<property>[a-zA-Z_]+)',
                line)
            if match:
                for code_point in range(
                        int(match.group('codepoint1'), 16),
                        int(match.group('codepoint2'), 16)+1):
                    fill_derived_core_property(
                        code_point,
                        match.group('property'))

def to_upper(code_point):
    if (unicode_attributes[code_point]['name']
        and unicode_attributes[code_point]['upper']):
        return unicode_attributes[code_point]['upper']
    else:
        return code_point

def to_lower(code_point):
    if (unicode_attributes[code_point]['name']
        and unicode_attributes[code_point]['lower']):
        return unicode_attributes[code_point]['lower']
    else:
        return code_point

def to_title(code_point):
    if (unicode_attributes[code_point]['name']
        and unicode_attributes[code_point]['title']):
        return unicode_attributes[code_point]['title']
    else:
        return code_point

def is_upper(code_point):
    return (to_lower(code_point) != code_point
            or (code_point in derived_core_properties
                and 'Uppercase' in derived_core_properties[code_point]))

def is_lower(code_point):
    # Some characters are defined as “Lowercase” in Derived_Core_Properties.txt
    # but do not have a mapping to upper case. For example,
    # ꜰ U+A72F “LATIN LETTER SMALL CAPITAL F” is one of these.
    return (to_upper(code_point) != code_point
            # <U00DF> is lowercase, but without simple to_upper mapping.
            or code_point == 0x00DF
            or (code_point in derived_core_properties
                and 'Lowercase' in derived_core_properties[code_point]))

def is_alpha(code_point):
    return ((code_point in derived_core_properties
             and
             'Alphabetic' in derived_core_properties[code_point])
            or
            # Consider all the non-ASCII digits as alphabetic.
            # ISO C 99 forbids us to have them in category “digit”,
            # but we want iswalnum to return true on them.
            (unicode_attributes[code_point]['category'] == 'Nd'
             and not (code_point >= 0x0030 and code_point <= 0x0039)))

def is_digit(code_point):
    if 0:
        return (unicode_attributes[code_point]['name']
                and unicode_attributes[code_point]['category'] == 'Nd')
        # Note: U+0BE7..U+0BEF and U+1369..U+1371 are digit systems without
        # a zero.  Must add <0> in front of them by hand.
    else:
        # SUSV2 gives us some freedom for the "digit" category, but ISO C 99
        # takes it away:
        # 7.25.2.1.5:
        #    The iswdigit function tests for any wide character that corresponds
        #    to a decimal-digit character (as defined in 5.2.1).
        # 5.2.1:
        #    the 10 decimal digits 0 1 2 3 4 5 6 7 8 9
        return (code_point >= 0x0030 and code_point <= 0x0039)

def is_outdigit(code_point):
    return (code_point >= 0x0030 and code_point <= 0x0039)

def is_blank(code_point):
    return (code_point == 0x0009 # '\t'
            # Category Zs without mention of '<noBreak>'
            or (unicode_attributes[code_point]['name']
                and unicode_attributes[code_point]['category'] == 'Zs'
                and '<noBreak>' not in unicode_attributes[code_point]['decomposition']))

def is_space(code_point):
    # Don’t make U+00A0 a space. Non-breaking space means that all programs
    # should treat it like a punctuation character, not like a space.
    return (code_point == 0x0020 # ' '
            or code_point == 0x000C # '\f'
            or code_point == 0x000A # '\n'
            or code_point == 0x000D # '\r'
            or code_point == 0x0009 # '\t'
            or code_point == 0x000B # '\v'
            # Categories Zl, Zp, and Zs without mention of "<noBreak>"
            or (unicode_attributes[code_point]['name']
                and
                (unicode_attributes[code_point]['category'] in ['Zl', 'Zp']
                 or
                 (unicode_attributes[code_point]['category'] in ['Zs']
                  and
                  '<noBreak>' not in unicode_attributes[code_point]['decomposition']))))

def is_cntrl(code_point):
    return (unicode_attributes[code_point]['name']
            and (unicode_attributes[code_point]['name'] == '<control>'
                 or
                 unicode_attributes[code_point]['category'] in ['Zl', 'Zp']))

def is_xdigit(code_point):
    if 0:
        return (is_digit(code_point)
                or (code_point >= 0x0041 and code_point <= 0x0046)
                or (code_point >= 0x0061 and code_point <= 0x0066))
    else:
        # SUSV2 gives us some freedom for the "xdigit" category, but ISO C 99
        # takes it away:
        # 7.25.2.1.12:
        #    The iswxdigit function tests for any wide character that corresponds
        #    to a hexadecimal-digit character (as defined in 6.4.4.1).
        # 6.4.4.1:
        #    hexadecimal-digit: one of 0 1 2 3 4 5 6 7 8 9 a b c d e f A B C D E F
        return ((code_point >= 0x0030 and code_point  <= 0x0039)
                or (code_point >= 0x0041 and code_point <= 0x0046)
                or (code_point >= 0x0061 and code_point <= 0x0066))

def is_graph(code_point):
    return (unicode_attributes[code_point]['name']
            and unicode_attributes[code_point]['name'] != '<control>'
            and not is_space(code_point))

def is_print(code_point):
    return (unicode_attributes[code_point]['name']
            and unicode_attributes[code_point]['name'] != '<control>'
            and unicode_attributes[code_point]['category'] not in ['Zl', 'Zp'])

def is_punct(code_point):
    if 0:
        return (unicode_attributes[code_point]['name']
                and unicode_attributes[code_point]['category'].startswith('P'))
    else:
        # The traditional POSIX definition of punctuation is every graphic,
        # non-alphanumeric character.
        return (is_graph(code_point)
                and not is_alpha(code_point)
                and not is_digit(code_point))

def is_combining(code_point):
    # Up to Unicode 3.0.1 we took the Combining property from the PropList.txt
    # file. In 3.0.1 it was identical to the union of the general categories
    # "Mn", "Mc", "Me". In Unicode 3.1 this property has been dropped from the
    # PropList.txt file, so we take the latter definition.
    return (unicode_attributes[code_point]['name']
            and
            unicode_attributes[code_point]['category'] in ['Mn', 'Mc', 'Me'])

def is_combining_level3(code_point):
    return (is_combining(code_point)
            and
            int(unicode_attributes[code_point]['combining']) in range(0, 200))

def ucs_symbol(code_point):
    '''Return the UCS symbol string for a Unicode character.'''
    if code_point < 0x10000:
        return '<U{:04X}>'.format(code_point)
    else:
        return '<U{:08X}>'.format(code_point)

def ucs_symbol_range(code_point_low, code_point_high):
    return ucs_symbol(code_point_low) + '..' + ucs_symbol(code_point_high)

def output_charclass(file, class_name, is_class_function):
    code_point_ranges  = []
    for code_point in sorted(unicode_attributes):
        if is_class_function(code_point):
            if (code_point_ranges
                and code_point_ranges[-1][-1] == code_point - 1):
                code_point_ranges[-1].append(code_point)
            else:
                code_point_ranges.append([code_point])
    if code_point_ranges:
        file.write('%s /\n' %class_name)
        max_column = 75
        prefix = '   '
        line = prefix
        range_string = ''
        for code_point_range in code_point_ranges:
            if line.strip():
                line  += ';'
            if len(code_point_range) == 1:
                range_string = ucs_symbol(code_point_range[0])
            else:
                range_string = ucs_symbol_range(
                    code_point_range[0], code_point_range[-1])
            if len(line+range_string) > max_column:
                file.write(line+'/\n')
                line = prefix
            line += range_string
        if line.strip():
            file.write(line+'\n')

def output_charmap(file, map_name, map_function):
    max_column = 75
    prefix = '   '
    line = prefix
    map_string = ''
    file.write('%s /\n' %map_name)
    for code_point in sorted(unicode_attributes):
        if code_point != map_function(code_point):
            if line.strip():
                line += ';'
            map_string = '(' \
                         + ucs_symbol(code_point) \
                         + ',' \
                         + ucs_symbol(map_function(code_point)) \
                         + ')'
            if len(line+map_string) > max_column:
                file.write(line+'/\n')
                line = prefix
            line += map_string
    if line.strip():
        file.write(line+'\n')

def verifications():
    for code_point in sorted(unicode_attributes):
        # toupper restriction: "Only characters specified for the keywords
	# lower and upper shall be specified.
        if (to_upper(code_point) != code_point
            and not (is_lower(code_point) or is_upper(code_point))):
            sys.stderr.write(
                '%(sym)s is not upper|lower but toupper(0x%(c)04X) = 0x%(uc)04X\n' %{
                    'sym': ucs_symbol(code_point),
                    'c': code_point,
                    'uc': to_upper(code_point)})
        # tolower restriction: "Only characters specified for the keywords
        # lower and upper shall be specified.
        if (to_lower(code_point) != code_point
            and not (is_lower(code_point) or is_upper(code_point))):
            sys.stderr.write(
                '%(sym)s is not upper|lower but tolower(0x%(c)04X) = 0x%(uc)04X\n' %{
                    'sym': ucs_symbol(code_point),
                    'c': code_point,
                    'uc': to_lower(code_point)})
        # alpha restriction: "Characters classified as either upper or lower
	# shall automatically belong to this class.
        if ((is_lower(code_point) or is_upper(code_point))
             and not is_alpha(code_point)):
            sys.stderr.write('%(sym)s is upper|lower but not alpha\n' %{
                'sym': ucs_symbol(code_point)})
        # alpha restriction: “No character specified for the keywords cntrl,
	# digit, punct or space shall be specified.”
        if (is_alpha(code_point) and is_cntrl(code_point)):
            sys.stderr.write('%(sym)s is alpha and cntrl\n' %{
                'sym': ucs_symbol(code_point)})
        if (is_alpha(code_point) and is_digit(code_point)):
            sys.stderr.write('%(sym)s is alpha and digit\n' %{
                'sym': ucs_symbol(code_point)})
        if (is_alpha(code_point) and is_punct(code_point)):
            sys.stderr.write('%(sym)s is alpha and punct\n' %{
                'sym': ucs_symbol(code_point)})
        if (is_alpha(code_point) and is_space(code_point)):
            sys.stderr.write('%(sym)s is alpha and space\n' %{
                'sym': ucs_symbol(code_point)})
        # space restriction: “No character specified for the keywords upper,
	# lower, alpha, digit, graph or xdigit shall be specified.”
	# upper, lower, alpha already checked above.
        if (is_space(code_point) and is_digit(code_point)):
            sys.stderr.write('%(sym)s is space and digit\n' %{
                'sym': ucs_symbol(code_point)})
        if (is_space(code_point) and is_graph(code_point)):
            sys.stderr.write('%(sym)s is space and graph\n' %{
                'sym': ucs_symbol(code_point)})
        if (is_space(code_point) and is_xdigit(code_point)):
            sys.stderr.write('%(sym)s is space and xdigit\n' %{
                'sym': ucs_symbol(code_point)})
        # cntrl restriction: “No character specified for the keywords upper,
	# lower, alpha, digit, punct, graph, print or xdigit shall be
	# specified.”  upper, lower, alpha already checked above.
        if (is_cntrl(code_point) and is_digit(code_point)):
            sys.stderr.write('%(sym)s is cntrl and digit\n' %{
                'sym': ucs_symbol(code_point)})
        if (is_cntrl(code_point) and is_punct(code_point)):
            sys.stderr.write('%(sym)s is cntrl and punct\n' %{
                'sym': ucs_symbol(code_point)})
        if (is_cntrl(code_point) and is_graph(code_point)):
            sys.stderr.write('%(sym)s is cntrl and graph\n' %{
                'sym': ucs_symbol(code_point)})
        if (is_cntrl(code_point) and is_print(code_point)):
            sys.stderr.write('%(sym)s is cntrl and print\n' %{
                'sym': ucs_symbol(code_point)})
        if (is_cntrl(code_point) and is_xdigit(code_point)):
            sys.stderr.write('%(sym)s is cntrl and xdigit\n' %{
                'sym': ucs_symbol(code_point)})
        # punct restriction: “No character specified for the keywords upper,
	# lower, alpha, digit, cntrl, xdigit or as the <space> character shall
	# be specified.”  upper, lower, alpha, cntrl already checked above.
        if (is_punct(code_point) and is_digit(code_point)):
            sys.stderr.write('%(sym)s is punct and digit\n' %{
                'sym': ucs_symbol(code_point)})
        if (is_punct(code_point) and is_xdigit(code_point)):
            sys.stderr.write('%(sym)s is punct and xdigit\n' %{
                'sym': ucs_symbol(code_point)})
        if (is_punct(code_point) and code_point == 0x0020):
            sys.stderr.write('%(sym)s is punct\n' %{
                'sym': ucs_symbol(code_point)})
        # graph restriction: “No character specified for the keyword cntrl
	# shall be specified.”  Already checked above.

        # print restriction: “No character specified for the keyword cntrl
	# shall be specified.”  Already checked above.

        # graph - print relation: differ only in the <space> character.
	# How is this possible if there are more than one space character?!
	# I think susv2/xbd/locale.html should speak of “space characters”,
	# not “space character”.
        if (is_print(code_point)
            and not (is_graph(code_point) or is_space(code_point))):
            sys.stderr.write('%(sym)s is print but not graph|<space>\n' %{
                'sym': ucs_symbol(code_point)})
        if (not is_print(code_point)
            and (is_graph(code_point) or code_point == 0x0020)):
            sys.stderr.write('%(sym)s is graph|<space> but not print\n' %{
                'sym': ucs_symbol(code_point)})

def output_tables(filename, unicode_version):
    with open(filename, mode='w') as file:
        file.write('escape_char /\n')
        file.write('comment_char %\n')
        file.write('\n')
        file.write('% Generated automatically by gen-unicode-ctype.py for Unicode {:s}.\n'.format(unicode_version))
        file.write('\n')
        file.write('LC_IDENTIFICATION\n')
        file.write('title     "Unicode {:s} FDCC-set"\n'.format(unicode_version))
        file.write('source    "UnicodeData.txt, DerivedCoreProperties.txt"\n')
        file.write('address   ""\n')
        file.write('contact   ""\n')
        file.write('email     "bug-glibc-locales@gnu.org"\n')
        file.write('tel       ""\n')
        file.write('fax       ""\n')
        file.write('language  ""\n')
        file.write('territory "Earth"\n')
        file.write('revision  "{:s}"\n'.format(unicode_version))
        file.write('date      "{:s}"\n'.format(time.strftime('%Y-%m-%d')))
        file.write('category  "unicode:2014";LC_CTYPE\n')
        file.write('END LC_IDENTIFICATION\n')
        file.write('\n')
        file.write('LC_CTYPE\n')
        file.write('% The following is the 14652 i18n fdcc-set LC_CTYPE category.\n')
        file.write('% It covers Unicode version {:s}.\n'.format(unicode_version))
        file.write('% The character classes and mapping tables were automatically\n')
        file.write('% generated using the gen-unicode-ctype.py program.\n')

        file.write('\n')
        file.write('% The "upper" class reflects the uppercase characters of class "alpha"\n')
        output_charclass(file, 'upper', is_upper)

        file.write('\n')
        file.write('% The "lower" class reflects the lowercase characters of class "alpha"\n')
        output_charclass(file, 'lower', is_lower)

        file.write('\n')
        file.write('% The "alpha" class of the "i18n" FDCC-set is reflecting\n')
        file.write('% the recommendations in TR 10176 annex A\n')
        output_charclass(file, 'alpha', is_alpha)

        file.write('\n')
        file.write('% The "digit" class must only contain the BASIC LATIN digits, says ISO C 99\n')
        file.write('% (sections 7.25.2.1.5 and 5.2.1).\n')
        output_charclass(file, 'digit', is_digit)

        file.write('\n')
        file.write('% The "outdigit" information is by default "0" to "9".  We don\'t have to\n')
        file.write('% provide it here since localedef will fill in the bits and it would\n')
        file.write('% prevent locales copying this file define their own values.\n')
        file.write('% outdigit /\n')
        file.write('%    <U0030>..<U0039>\n')
        # output_charclass(file, 'outdigit', is_outdigit)

        file.write('\n')
        output_charclass(file, 'space', is_space)

        file.write('\n')
        output_charclass(file, 'cntrl', is_cntrl)

        file.write('\n')
        output_charclass(file, 'punct', is_punct)

        file.write('\n')
        output_charclass(file, 'graph', is_graph)

        file.write('\n')
        output_charclass(file, 'print', is_print)

        file.write('\n')
        file.write('% The "xdigit" class must only contain the BASIC LATIN digits and A-F, a-f,\n')
        file.write('% says ISO C 99 (sections 7.25.2.1.12 and 6.4.4.1).\n')
        output_charclass(file, 'xdigit', is_xdigit)

        file.write('\n')
        output_charclass(file, 'blank', is_blank)

        file.write('\n')
        output_charmap(file, 'toupper', to_upper)

        file.write('\n')
        output_charmap(file, 'tolower', to_lower)

        file.write('\n')
        output_charmap(file, 'map "totitle";', to_title)

        file.write('\n')
        file.write('% The "combining" class reflects ISO/IEC 10646-1 annex B.1\n')
        file.write('% That is, all combining characters (level 2+3).\n')
        output_charclass(file, 'class "combining";', is_combining)

        file.write('\n')
        file.write('% The "combining_level3" class reflects ISO/IEC 10646-1 annex B.2\n')
        file.write('% That is, combining characters of level 3.\n')
        output_charclass(file, 'class "combining_level3";', is_combining_level3)

        file.write('END LC_CTYPE\n')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Generate a Unicode conforming LC_CTYPE category from a UnicodeData file.')
    parser.add_argument('-u', '--unicode_data_file',
                        nargs='?',
                        type=str,
                        default='UnicodeData.txt',
                        help='The UnicodeData.txt file to read, default: %(default)s')
    parser.add_argument('-d', '--derived_core_properties_file',
                        nargs='?',
                        type=str,
                        default='DerivedCoreProperties.txt',
                        help='The DerivedCoreProperties.txt file to read, default: %(default)s')
    parser.add_argument('-o', '--output_file',
                        nargs='?',
                        type=str,
                        default='unicode',
                        help='The file which shall contain the generated LC_CTYPE category, default: %(default)s')
    parser.add_argument('--unicode_version',
                        nargs='?',
                        required=True,
                        type=str,
                        help='The Unicode version of the input files used.')
    args = parser.parse_args()

    fill_attributes(args.unicode_data_file)
    fill_derived_core_properties(args.derived_core_properties_file)
    verifications()
    output_tables(args.output_file, args.unicode_version)
