from whoosh.fields import Schema, TEXT, ID, DATETIME

FILE_INDEXING_SCHEMA = Schema(path=ID(stored=True),
                              content=TEXT,
                              create_time=DATETIME(stored=True),
                              modified_time=DATETIME(stored=True))
