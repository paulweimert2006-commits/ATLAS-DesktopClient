## 2026-02-25 - [Session Reuse in Parallel Workers]
**Learning:** In multi-threaded network applications using `requests`, creating a new `Session` per request is a significant performance bottleneck due to redundant TCP/TLS handshakes. However, sharing a single session across threads requires careful locking.
**Action:** Use "one Session per thread" in worker loops to maximize performance (connection pooling) while maintaining thread-safety without lock contention.

## 2026-02-25 - [Regex Pre-compilation Overhead]
**Learning:** Frequent XML and MTOM parsing in batch operations can become CPU-bound if regex patterns are compiled on-the-fly inside loops or frequently called functions.
**Action:** Identify and pre-compile common regex patterns as module-level constants to save CPU cycles during large-scale data retrieval.
