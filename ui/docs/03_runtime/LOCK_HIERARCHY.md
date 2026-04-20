# Lock Hierarchy

1. `state_mutex_` owns execution-state mutation and freeze-gate checks.
2. RT execution lane must not wait on query/projection work while holding RT-sensitive state.
3. Query/projection code may snapshot under `state_mutex_`, then publish outside the critical section.
4. Session freeze verification and reply projection must not recursively reacquire control-authority transitions.
