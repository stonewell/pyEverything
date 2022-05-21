import pathlib
import globre


class VCSIgnore(object):
  IGNORE_PATTERN_FILES = [
      '.ignore',
      '.gitignore',
      '.git/info/exclude',
      '.hgignore',
  ]

  def __init__(self, path, parent=None):
    super().__init__()

    self.path_ = path
    self.parent_ = parent
    self.patterns_ = []

  def add_ignore_pattern(self, pattern):
    if pattern.startswith('#'):
      return

    while pattern.endswith('\n') or pattern.endswith('\r'):
      pattern = pattern[:-1]

    if not pattern.endswith('\\ '):
      pattern = pattern.rstrip()

    if len(pattern) == 0:
      return

    white_list = False
    if pattern.startswith('!'):
      pattern = pattern[1:]
      white_list = True

    extra_pattern = None
    if pattern.startswith('/'):
      pattern = pattern[1:]
    elif pattern.find('/') >= 0:
      extra_pattern = pattern
      pattern = '**/' + pattern

    if pattern.endswith('/'):
      pattern = pattern + '**'
      if extra_pattern:
        extra_pattern += '**'

    if extra_pattern is not None:
      self.patterns_.append((extra_pattern, white_list))

    self.patterns_.append((pattern, white_list))

  def load_ignore_patterns(self, path):
    if isinstance(path, str):
      path = pathlib.Path(path)

    if not (path.exists() and path.is_file()):
      return

    with path.open(encoding='utf-8') as f:
      for line in f:
        self.add_ignore_pattern(line)

  def load_ignore_patterns_in_path(self, path=None):
    if path is None:
      path = self.path_

    if isinstance(path, str):
      path = pathlib.Path(path)

    for f in VCSIgnore.IGNORE_PATTERN_FILES:
      p = path / f

      if p.exists() and p.is_file():
        self.load_ignore_patterns(p)

  def ignore_path(self, path):
    if isinstance(path, str):
      path = pathlib.Path(path)

    if len(self.patterns_) == 0:
      return False if self.parent_ is None else self.parent_.ignore_path(path)

    rel_path = path.relative_to(self.path_).as_posix()

    ignore = None

    for pattern, white_list in self.patterns_:
      match = globre.match(pattern, rel_path) is not None

      if match:
        ignore = not white_list

    if not (ignore is None):
      return ignore

    return False if self.parent_ is None else self.parent_.ignore_path(path)
