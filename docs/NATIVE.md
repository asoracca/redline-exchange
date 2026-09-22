# Python / C++ boundary

The existing Python `LimitOrderBook` remains the default for CSV replay, CLI,
market-making simulations, and research. `NativeLimitOrderBook` is an optional
backend with the same public order/trade value objects and matching semantics.

```text
Python research / replay / prepared event stream
              |
       submit / cancel / replace
              |
   +----------+------------------+
   |                             |
Python LimitOrderBook     NativeLimitOrderBook adapter
   |                             | pybind11 (GIL held)
heapq + dict               C++17 redline::Book
   |                       priority_queue + unordered_map
   +-----------+-----------------+
               |
      Python Order / Trade / BookLevel
```

## Build

Python 3.11+, a C++17 compiler, and matching Python development headers are
required for the native backend. The Python engine needs no compiler.

```bash
python -m pip install -e '.[dev,native,research]'
python scripts/build_native.py             # GCC or Clang via c++
python -c 'from orderbook import _native; print(_native.compiler)'
python -m pytest -q
```

On macOS, install Apple's Command Line Tools or use the optional portable
compiler below. On Linux install the distribution's C++ compiler and Python
headers if missing. Windows users can use WSL; MSVC is not supported by this
small build helper.

The measured macOS run used this isolated alternative:

```bash
python -m pip install ziglang==0.13.0
python scripts/build_native.py --cxx 'python -m ziglang c++'
```

The helper builds with `-O3 -DNDEBUG -std=c++17`, saves compiler/source metadata
in `native-build.json`, and writes an ignored extension into `src/orderbook`.
Rebuild after changing Python versions or C++ sources. Use an editable install;
this project does not yet distribute native wheels.

```python
from orderbook import Side
from orderbook.native import NativeLimitOrderBook

book = NativeLimitOrderBook("DEMO")
book.submit_limit("maker", Side.SELL, 100, 10100)
print(book.submit_market("taker", Side.BUY, 40))
book.assert_invariants()
```

## Contract

- Better price, then earlier sequence; execution at the maker price.
- Positive integer quantities and ticks; booleans/floats are rejected.
- New IDs are single-use for the life of a book, including canceled/filled IDs.
- Unfilled market quantity is discarded. Unfilled limit quantity rests.
- Replacement quantity means **new remaining quantity**. Reduction at the same
  price keeps priority; increase/reprice loses it. Equal quantity retains it.
- Missing active IDs raise `KeyError`; invalid values raise `ValueError` or
  `TypeError`. Invalid-input tests check that rejection leaves state unchanged.
- Returned values are detached snapshots. Mutating one cannot alter the book.
- History retention can be disabled on both backends; returned trades still exist.

C++ accepts prices and order quantities in `[1, 2**53 - 1]`, including cumulative
filled-plus-remaining quantity on replacement. Python integers remain unbounded.
Parity is promised for the shared valid range. Depth aggregates use signed
64-bit integers with checked overflow. Aggregate-depth overflow raises an error;
there is no wraparound. Sequence counters use signed 64-bit storage: this is an
educational finite-run engine, not an indefinitely running service.

Both engines retain seen IDs and maximum-quantity accounting for invariants.
Canceled/replaced heap entries are cleaned lazily. Consequently memory is not
bounded by current active order count, even with trade history disabled.

## Design and complexity

C++ intentionally follows the Python heap design, reducing the number of
algorithmic changes hidden inside the language comparison. The C++ core has no
Python dependency; `bindings.cpp` is the only file including pybind11.

For `H` heap entries (including stale entries) and `A` active orders:

| Operation | Expected cost / qualification |
|---|---|
| Rest | O(log H) |
| Cancel / ID lookup | Expected O(1), hash-map worst case O(A) |
| Quantity reduction | Expected O(1) |
| Reprice / increase | Matching cost plus O(log H) if it rests |
| Match | O((fills + stale entries removed) log H) upper bound |
| Active snapshots | O(A log A) to sort by arrival |
| Depth | Python O(A + L log L); C++ O(A log L), L occupied levels |
| Invariant checks | Expensive diagnostics, excluded from timed benchmarks |

This is not a lock-free, concurrent, persistent, networked exchange. No SIMD,
custom allocator, cache-line layout, or CPU-affinity claim is made. The GIL is
held during calls. The benchmark measures a usable Python-facing API, including
cross-language calls and materializing Python trade objects; it does not measure
standalone C++ peak throughput. Allocation failures are not transactional.

## Verification

The native suite reuses the original deterministic book/replace regressions,
compares randomized operations and every resulting state, checks identical full
trades and final snapshots on four workloads, and tests numeric-boundary rejection.
The comparison script refuses to report results when behavioral parity fails.

```bash
c++ -std=c++17 -O1 -g -fsanitize=address,undefined \
  -fno-omit-frame-pointer cpp/test_core.cpp -o /tmp/redline-core-test
/tmp/redline-core-test
```

Linux CI is configured to run those sanitizer checks and native parity on
Python 3.11–3.13. A configured workflow is not evidence of a completed hosted run;
see the audit for what was actually run locally.

## Rebuild safeguards

The build helper compiles into a temporary directory under ignored `build/`.
Compiler failures leave the existing extension and metadata intact. After a
successful build, it replaces the extension and metadata; a process interruption
between those replacements is detected by the checksum validation on the next
benchmark. Source changes during compilation also fail the build.

Before native timing, the comparison validates the current sources, loaded
binary checksum/path, Python ABI/cache tag and metadata schema. Keep the binary
and `native-build.json` together when moving a checkout, or rebuild. The regular
Python reference engine has no dependency on either artifact.

## Verified arm64 macOS shipping command

The 2026-09-21 run used an explicit deployment target with the portable compiler:

```bash
python scripts/build_native.py --cxx 'python -m ziglang c++ -target aarch64-macos.14.0'
python -m ziglang c++ -target aarch64-macos.14.0 -std=c++17 -O2 \
  cpp/test_core.cpp -o build/redline-core-test
build/redline-core-test
```

This resolved missing system symbols when linking the standalone test with Zig's
implicit target on the measured Mac. See [shipping validation](SHIPPING.md).
