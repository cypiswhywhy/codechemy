# Say less in the code

Comments are code that cannot be tested and that rots in silence. Write only the few that
carry something the code itself cannot.

- A comment says *why*, never *what*. If it restates the line below it, delete it. If a line
  needs explaining, fix the line instead - rename it, split it, name the constant - and the
  comment stops being needed.
- One line is the default docstring, and it states the contract rather than the body: what the
  caller gets, plus the surprise (raises, mutates an argument, blocks, is not safe to call
  twice). Restating the signature parameter by parameter is not documentation.
- No docstring at all on a private helper whose name and signature already say it, on a test
  whose name says it, or on an `__init__` that only assigns its arguments.
- Longer only when the reason is outside the code: a protocol quirk, a workaround with a link,
  an ordering constraint someone would otherwise tidy away. Then give the reason, next to the
  code that depends on it.
- Never narrate the change (`# now handle the empty case`, `# was: ...`), leave `TODO`/`FIXME`
  for someone else, keep commented-out code, or open a module with a docstring listing what the
  file visibly contains.
- Match the density of the file you are in. A change whose added lines are mostly prose is a
  change that was not read closely enough. The Stop hook measures this per file and blocks
  once when a file's growth is mostly prose and well past its own density.
