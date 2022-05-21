import pathlib
from collections import deque
from vcs_ignore import VCSIgnore

BUILTIN_IGNORE = set(['.git', '.svn', 'CVS', '.hg', '.gitignore'])


def add_glboal_ignore(path_name):
  BUILTIN_IGNORE.add(path_name)


def walk_directory(path):
  children = deque([(path, VCSIgnore(path))])

  while len(children) > 0:
    cur_entry, vi = children.popleft()
    vi.load_ignore_patterns_in_path()

    for child in cur_entry.iterdir():
      if vi.ignore_path(child) or child.name in BUILTIN_IGNORE:
        continue

      if child.is_file():
        yield child
      elif child.is_dir():
        children.append((child, VCSIgnore(child, vi)))


if __name__ == '__main__':
  for p in walk_directory(pathlib.Path('.').cwd()):
    print(p.as_posix())
