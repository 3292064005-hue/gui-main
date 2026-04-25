# Historical tests

Versioned and migration-era test modules live here. The stable target surface in tests/ root re-exports the relevant cases so CI can stay on durable names while preserving history.

Archived tests preserve migration context only. They do not define active mainline behavior, runtime command surface, or release evidence requirements. Root-level tests are the stable CI contract.
