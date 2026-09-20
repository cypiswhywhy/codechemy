# Correct by construction

The review loop and the audit catch these after the code is written, at the cost of a cycle
each. They are cheaper not to write. This applies whenever you add or change code that runs.

- Validate where data crosses into your code - a request body, CLI argument, environment
  variable, file, third-party response, or a stored row written by an older version of this
  code. Check it once at that edge and convert it into a type or shape the rest of the code can
  assume, so the interior needs no guards. Everything already inside that edge is trusted.
- Handle an error or propagate it with what the caller needs to act on. Never swallow one: an
  empty `except`, a logged-and-continued failure, or a returned zero value that the caller
  cannot tell from success is a defect that surfaces somewhere else, much later.
- Before putting state outside a function - module level, a cached client, a field mutated from
  a handler - name who else reads it and from where. Unnamed shared state is where both data
  races and order-dependent tests come from.
- Anything reachable twice must be safe twice. A retry, an at-least-once queue, a resubmitted
  form: make the operation idempotent or give it a key that makes the second call a no-op.
  "It only runs once" is an assumption, not a property of the code.
- Release what you acquire on every path, including the error path, using the construct the
  language already has (`with`, `defer`, `using`, RAII) rather than a close at the end.
- Untrusted input never reaches an interpreter as text. Use the parameterised or escaping API
  the library already provides for SQL, shell, HTML and file paths. Keep credentials out of
  source, logs and error messages. A new endpoint, query or file read is also an authorization
  question - say who may call it.
- Name in the summary the trust boundary you validated at, and any failure mode you decided not
  to handle, with why. "Nothing crosses a boundary here" is a complete answer.
