# Type-Driven Design & Validation Implementation

Planned data structures (flow step 2) are implemented following strict **"Parse,
don't validate"** discipline. These principles apply regardless of language:

- **Parse at boundaries** — all external input (wire formats, config files, CLI
  args) is parsed into domain types at the subsystem entry point. After parsing,
  the rest of the system uses only those types — never raw strings, untyped
  dictionaries/maps, or loose primitives.
- **Make invalid states unrepresentable** — any value carrying an invariant
  (non-empty string, valid email, bounded number, well-formed URL) must be
  wrapped in a dedicated type whose constructor enforces the invariant at
  creation time. Holding an instance of the type _guarantees_ the invariant; no
  downstream validation needed.
- **Newtype / wrapper pattern** — single-field types that wrap a primitive and
  expose only valid constructions (fallible factory function, builder, private
  constructor). Equivalent patterns exist in every language: data classes with
  private constructors, tagged types, opaque types, smart constructors, or
  newtype structs with a `TryFrom` impl.
- **Type-first implementation** — design types from the planned data structures
  _before_ writing functions. Each structure becomes a record or enum variant.
  Functions operate on those types; the compiler/type-checker enforces
  correctness at every call site.
- **Shared types** — a data structure consumed by multiple modules or flows is
  defined once in a canonical location. Both producer and consumer modules
  import it, making type mismatches a **compile-time (or static-analysis)
  error** — no runtime check or test suite needed.
- **Fallible construction** — all constructors that can reject invalid input
  return a typed error (result type, checked exception, optional chaining with
  diagnostics) naming the data structure and the offending field. Errors are
  self-documenting.
- **No bare panics/asserts in production** — use structured errors or checked
  exceptions. Unrecoverable programmer bugs (invariant violations indicating a
  logic error) are the only acceptable use of panics/asserts.
