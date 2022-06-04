# pyEverything
Everything file indexing server in python

# Install
```
pip install git+https://github.com/stonewell/pyEverything
```

# TODO
- [ ] scheduled indexing update
- [X] ignore vcs file, and files vcs ignore
- [X] list indexed path
- [X] refresh index (delete non existing, update changed, add new)
- [X] support raw query string
- [X] get the hit line and column
- [X] generate textmate compatible output
- [X] update will remove the indexed file which ignore now
- [X] use 1 to 3 gram index, and full support regex
- [ ] handle [a]?.* regex
- [X] add run_with_args function to frontend.cmd
- [X] add refresh index function to frontend.cmd

# Reference
- [https://swtch.com/~rsc/regexp/regexp4.html](https://swtch.com/~rsc/regexp/regexp4.html)
- [http://www.dalkescientific.com/Python/sre_dump.html](http://www.dalkescientific.com/Python/sre_dump.html)
- [https://github.com/google/sre_yield](https://github.com/google/sre_yield)
