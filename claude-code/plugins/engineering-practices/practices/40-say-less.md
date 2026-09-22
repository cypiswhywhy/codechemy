# Say less in the code

- A comment says *why*, never *what*. If it restates the line below, delete it; if the line needs
  explaining, rename or split the line instead.
- A docstring is one line stating the contract: what the caller gets, plus the surprise (raises,
  mutates an argument, blocks, unsafe to call twice). Not the parameters one by one.
- No docstring on a private helper whose name and signature say it, on a test whose name says
  it, or on an `__init__` that only assigns.
- Longer only for a reason outside the code (a protocol quirk, a workaround with a link, an
  ordering constraint), placed next to the code that depends on it.
- Never narrate the change or the review that shaped it (`# now handle ...`, `# was: ...`), leave
  `TODO`/`FIXME`, keep commented-out code, or open a module by listing its contents.
- Match the density of the file you are in. The Stop hook measures this per file and blocks once
  when a file's growth is mostly prose and well past its own density.
