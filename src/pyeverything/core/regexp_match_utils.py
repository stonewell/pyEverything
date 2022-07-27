import logging
import pathlib
import re

from io import StringIO


def regexp_match_info(path, pattern, ignore_case=False):
  text = pathlib.Path(path).read_text(encoding='utf-8', errors='ignore')

  logging.debug(
      f'matching file:{path} using:{pattern}, ignore_case:{ignore_case}')

  if isinstance(pattern, str):
    token_iter = re.finditer(f'(?m){"(?i)" if ignore_case else ""}{pattern}',
                             text)
  else:
    token_iter = pattern.finditer(text)

  return generate_match_info(text, token_iter, lambda t: t.start(),
                             lambda t: t.end())


def generate_match_info(text, token_iter, start_char, end_char):
  try:
    t = next(token_iter)
  except (StopIteration):
    return

  line_start = 0
  line_count = 0

  for line in StringIO(text):
    line_end = line_start + len(line)

    _s_char = start_char(t)
    _e_char = end_char(t)

    while _s_char >= line_start and _e_char < line_end:
      yield (line_count, _s_char - line_start, _e_char - _s_char,
             line.replace('\n', '').replace('\r', ''))

      try:
        t = next(token_iter)
      except (StopIteration):
        return

      _s_char = start_char(t)
      _e_char = end_char(t)

    line_count += 1
    line_start = line_end
