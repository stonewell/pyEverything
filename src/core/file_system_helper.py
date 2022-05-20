import pathlib
from collections import deque


def walk_directory(path):
  children = deque([path])

  while len(children) > 0:
    cur_entry = children.popleft()

    for child in cur_entry.iterdir():
      if child.is_file():
        yield child
      elif child.is_dir():
        children.append(child)
