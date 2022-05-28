from collections import deque
import logging
import pathlib
import re

import sre_parse
from sre_constants import LITERAL, NOT_LITERAL, MAX_REPEAT
from sre_constants import IN, BRANCH, MIN_REPEAT, SUBPATTERN, MAXREPEAT
from sre_constants import ASSERT, ASSERT_NOT, ANY, GROUPREF, AT

from .utils import generate_match_info


def __sre_tree_to_query(pattern, minisize=2):
  words = []

  def emit(s):
    if s != ' ':
      words.append(s)

  def emit_with_op(s, op, check_minsize=True):
    if s == ' ':
      return
    if len(s) >= minisize or (not check_minsize and len(s) > 0):
      if len(words) > 0:
        emit(f' {op} ')

      if is_raw_literal(s):
        emit(f'({s})')
      else:
        emit(f'{s}')

  def emit_literal(s, op):
    if len(s.strip()) == 0:
      return

    if len(words) > 0:
      emit(f' {op} ')

    v = s.split()

    if len(v) == 1:
      emit(v[0])
    else:
      emit(f'({" AND ".join(v)})')

  def is_raw_literal(s):
    return s.find('(') == -1

  last_op = None
  literal = ''

  for term in pattern:
    op, av = term

    if last_op != op:
      emit_literal(literal, 'AND')
      literal = ''

    if op in [LITERAL, NOT_LITERAL]:
      c = chr(av)

      if c not in ['(', ')', '"']:
        literal += chr(av)
      else:
        literal += ' '

    elif op == IN:
      pass
    elif op in (MAX_REPEAT, MIN_REPEAT):
      i, j, subtree = av
      s = __sre_tree_to_query(subtree)

      if j == MAXREPEAT:
        if i == 0:
          emit_with_op(s, 'OR')
        elif i == 1:
          emit_with_op(s, 'AND')
        else:
          emit_with_op(s * i if is_raw_literal(s) else s, 'AND')
      else:
        if i == 0 and j == 1:
          emit_with_op(s, 'OR')
        elif i == j:
          emit_with_op(s * i if is_raw_literal(s) else s, 'AND')
        else:
          ss = ''

          for count in range(max(1, i), j + 1):
            if len(ss) > 0:
              ss += ' OR '
            ss += f'{(s * count)}'

          emit_with_op(ss if is_raw_literal(s) else s, 'AND')
    elif op == SUBPATTERN:
      _, _, _, subtree = av
      s = __sre_tree_to_query(subtree)

      emit_with_op(s, 'AND')
    elif op == ASSERT:
      _, subtree = av
      s = __sre_tree_to_query(subtree, minisize)

      emit_with_op(s, 'AND')
    elif op == ASSERT_NOT:
      _, subtree = av
      s = __sre_tree_to_query(subtree, minisize)

      emit_with_op(s, 'AND')

    elif op == BRANCH:
      # av[0] is always None
      ss = ''
      for x in av[1][:-1]:
        s = __sre_tree_to_query(x, minisize)

        if len(s) >= minisize:
          if len(ss) > 0:
            ss += ' OR '

          if is_raw_literal(s):
            ss += f'({s})'
          else:
            ss += s

      s = __sre_tree_to_query(av[1][-1], minisize)

      if len(s) >= minisize:
        if len(ss) > 0:
          ss += ' OR '

        if is_raw_literal(s):
          ss += f'({s})'
        else:
          ss += s

      emit_with_op(ss, 'AND')

    elif op == ANY:
      pass
    elif op == AT:
      pass
    elif op == GROUPREF:
      pass
    else:
      raise NotImplementedError(op)

    # These are added in creation order, inner before outer.
    last_op = op

  emit_literal(literal, 'AND')

  return "".join(words)


def __add_brackets(s):
  s = s.strip()

  if len(s) == 0:
    return s

  if s[0] != '(' or s[-1] != ')':
    return f'({s})'

  v = deque()

  for i, c in enumerate(s):
    if c == '(':
      v.append((i, c))
    elif c == ')':
      ii, cc = v.popleft()

      if ii == 0 and i != len(s) - 1:
        return f'({s})'

  return s


def regexp_to_query(regex_str, minisize=2):
  return __add_brackets(
      __sre_tree_to_query(sre_parse.parse(regex_str), minisize))


def regexp_match_info(hit, pattern, ignore_case):
  text = pathlib.Path(hit['path']).read_text()

  logging.debug(f'matching file:{hit["path"]} using:{pattern}, ignore_case:{ignore_case}')

  token_iter = re.finditer(f'(?m){"(?i)" if ignore_case else ""}{pattern}',
                           text)

  return generate_match_info(text, token_iter, lambda t: t.start(),
                             lambda t: t.end())
