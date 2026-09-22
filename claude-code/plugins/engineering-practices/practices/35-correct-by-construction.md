# Correct by construction

Whenever you add or change code that runs:

- Validate where data crosses into your code (request body, CLI argument, environment, file,
  third-party response, a row written by an older version). Convert it once, at that edge, into
  a shape the interior can assume without guards.
- Handle an error or propagate it with what the caller needs. Never swallow one: no empty
  `except`, no logged-and-continued failure, no zero return indistinguishable from success.
- Before putting state outside a function, name who else reads it and from where.
- Anything reachable twice must be safe twice: idempotent, or keyed so the second call is a
  no-op. "It only runs once" is an assumption.
- Release what you acquire on every path, with the language's construct (`with`, `defer`,
  `using`, RAII), not a close at the end.
- Untrusted input never reaches an interpreter as text: use the parameterised or escaping API
  for SQL, shell, HTML and paths. Credentials stay out of source, logs and error messages. A new
  endpoint, query or file read is an authorization question: say who may call it.
- Name in the summary the trust boundary you validated at and any failure mode you chose not to
  handle, with why. "Nothing crosses a boundary here" is a complete answer.
