# CRDT Counters: Distributed, Concurrent-Safe Increment API

## Overview
This feature adds distributed, concurrent-safe counters to the key-value store using a G-Counter (CRDT) approach. Counters are safe for concurrent increments and are merged across nodes.

## Endpoints

### Increment Counter
`POST /counter/incr/<key>`
- Increment the counter for `<key>` by a specified amount (default 1).
- Request body: `{ "amount": <int> }`
- Example:
  ```bash
  curl -X POST http://localhost:8080/counter/incr/mykey -H "Content-Type: application/json" -d '{"amount": 5}'
  ```
- Response: `{ "key": "mykey", "node_id": "node-1", "new_value": 5 }`

### Get Counter Value
`GET /counter/<key>`
- Returns the current value and per-node contributions.
- Example:
  ```bash
  curl http://localhost:8080/counter/mykey
  ```
- Response: `{ "key": "mykey", "value": 5, "nodes": { "node-1": 5 } }`

### Merge Counter State
`POST /counter/merge/<key>`
- Merge a remote counter state (for anti-entropy or manual sync).
- Request body: `{ "nodes": { "node-1": 5, "node-2": 3 } }`
- Response: `{ "key": "mykey", "value": 8, "nodes": { "node-1": 5, "node-2": 3 } }`

### Sync Counter State
`GET /counter/sync/<key>`
- Get the current per-node state for anti-entropy or peer sync.
- Response: `{ "key": "mykey", "nodes": { "node-1": 5 } }`

## Concurrency Guarantees
- Each increment is commutative and associative.
- Concurrent increments from different nodes are merged by summing per-node values.
- No lost updates: all increments are preserved.

## Example: Concurrent Increments
Suppose 5 threads increment a counter by [2, 100, 3, 7, 8] concurrently:
- Initial value: 0
- After all increments: 2 + 100 + 3 + 7 + 8 = **120**

## Persistence
- Counter state is saved to `data/counters.json` on every update.
- On node restart, counters are restored from disk.

## Test Results
- All counter API tests pass, including concurrent increments with different values.
- Example test:
  ```python
  increments = [2, 100, 3, 7, 8]
  # ... run 5 threads, each incrementing by one value ...
  # Final value should be sum(increments) == 120
  ```

## Usage Notes
- Use counters for metrics, likes, views, or any value that needs safe concurrent increments.
- Not suitable for decrements (use PN-Counter for that). 