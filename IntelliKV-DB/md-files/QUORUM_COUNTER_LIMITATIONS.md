# Quorum Counters: Limitations and Pitfalls

## Overview
This document explains the limitations of using quorum read/write with Last-Write-Wins (LWW) for distributed counters, and why CRDTs or atomic counters are required for correct behavior.

## Why Quorum + LWW Fails for Counters
- **Lost Updates:**
  - Two nodes read the same value (e.g., 5), both increment (to 6 and 7), both write back.
  - The value with the latest timestamp wins, so one increment is lost.
- **Value Can Decrease:**
  - If a node with a stale value but a newer timestamp writes back, the counter can decrease.
- **Network Partitions:**
  - During partitions, nodes may diverge. When healed, the "winning" value may not reflect all increments.
- **Anti-entropy/Read Repair:**
  - These can propagate a lower value if it has a newer timestamp, causing the counter to decrease.

## Example Scenario
1. Counter is 5.
2. Node A and Node B both read 5.
3. Node A increments to 6, Node B increments to 7.
4. Both write back. Whichever write has the latest timestamp wins (say, 6).
5. The increment to 7 is lost.

## Summary Table
| Consistency Model | Safe for Counters? | Can Lose Increments? | Can Value Decrease? |
|-------------------|--------------------|----------------------|---------------------|
| Quorum + LWW      | ❌ No              | ✅ Yes               | ✅ Yes              |
| CRDT Counter      | ✅ Yes             | ❌ No                | ❌ No               |

## Quorum Not Reached Errors
- If you see persistent 'quorum not reached' errors:
  - Some nodes are unreachable or unhealthy.
  - Peer lists or hash ring are inconsistent.
  - Writes/reads are not propagating to enough nodes.

## Practical Advice
- **Do NOT use quorum+LWW for distributed counters if you need correct totals.**
- For correct, monotonic counters, use a CRDT (G-Counter, PN-Counter) or an atomic counter implementation.
- Accept that with quorum+LWW, counters may lose increments and even decrease after failures or partitions.

## References
- [Why CRDTs are needed for distributed counters](https://riak.com/assets/bitcask-intro.pdf)
- [Cassandra Counter Documentation](https://cassandra.apache.org/doc/latest/cassandra/counters.html) 