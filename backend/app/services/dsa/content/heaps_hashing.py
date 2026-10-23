"""Topic I (Heaps and Hashing)."""

from __future__ import annotations

from app.services.dsa import algos as A
from app.services.dsa.references import _s, _tbl

from .build import M, S, mk, mk_ref

H1 = [13, 31, 35, 36, 38, 26]  # insertion-built and bottom-up-built heaps differ for this input
H2 = [13, 31, 35, 36, 38, 26]
H3 = [10, 20, 15, 30, 40, 45]


def _heap_trace(items):
    h, steps = [], []
    for x in items:
        h = A.heap_insert(h, x)
        steps.append({"label": f"insert {x}", "state": _s(h)})
    return steps


def heap_ops():
    s = "heap-operations"
    heap = A.build_heap_by_insertion(H3)
    return [
        mk_ref(s, "trace", f"Values {H1} are inserted one at a time into an initially empty MAX-heap (sift-up after each insertion). What is the array?", "heap_by_insertion", {"items": H1},
               [_s(H1), _s(sorted(H1, reverse=True)), _s(A.build_heap_bottom_up(H1))], "Each new value swaps upward while it is larger than its parent.", d="medium", t=85, trace=_heap_trace(H1)),
        mk_ref(s, "trace", f"Values {H3} are inserted one at a time into an empty max-heap. What is the array afterwards?", "heap_by_insertion", {"items": H3},
               [_s(H3), _s(sorted(H3, reverse=True)), _s(A.build_heap_bottom_up(H3))], "Sift-up after each insertion; the largest value 25 ends at the root.", d="medium", t=90, trace=_heap_trace(H3)),
        mk_ref(s, "trace", f"The max-heap {_s(heap)} has its maximum deleted (last element moves to the root, then sifts down). What is the array afterwards?", "heap_after_delete", {"heap": heap},
               [_s(heap[1:]), _s(sorted(heap[1:], reverse=True)), _s(heap[:-1])], "The last element replaces the root and swaps downward with the larger child while smaller than it.", d="hard", t=100,
               trace=[{"label": "remove root", "state": f"max = {heap[0]}"}, {"label": "move last element to root", "state": _s([heap[-1]] + heap[1:-1])}, {"label": "sift down", "state": _s(A.heap_delete_max(heap)[1])}]),
        mk(s, "complexity", "What are the time complexities of inserting into and deleting the max from a binary heap of n elements?", "Both O(log n)", ["Both O(1)", "Insert O(1), delete O(n)", "Both O(n)"], "A heap has height ⌊log₂ n⌋ and each operation moves along one root-to-leaf path.", d="easy", t=35,
           complexity={"time": "O(log n)", "space": "O(1)"}, ver=M("Heap height is log n.")),
        mk(s, "complexity", "Building a heap from n unsorted elements with the bottom-up (heapify) method takes:", "O(n)", ["O(n log n)", "O(log n)", "O(n²)"], "Most nodes are near the bottom and sift down only a short distance; the sum converges to O(n).", d="hard", t=60,
           complexity={"time": "O(n) bottom-up, O(n log n) by repeated insertion", "space": "O(1)"}, ver=M("Classic result: heapify is O(n).")),
        mk(s, "conceptual", "Which property defines a max-heap?", "Every node's value is at least as large as its children's, and the tree is complete", ["Left child < parent < right child", "All leaves have equal values", "The array is sorted in ascending order"],
           "The heap property orders parent versus children only, not siblings.", d="easy", t=35, ver=M("Heap order plus shape property.")),
        mk_ref(s, "conceptual", "In a zero-based array max-heap, which array positions hold the children of index 5?", "heap_children", {"i": 5}, ["5 and 6", "10 and 11", "2 and 3"], "Children are at 2i + 1 and 2i + 2.", d="easy", t=35),
        mk(s, "scenario", "A task scheduler must always process the largest-priority job next while new jobs arrive constantly. Which structure gives O(log n) for both operations?", "A binary max-heap", ["A sorted array", "An unsorted linked list", "A stack"], "Both insertion and extract-max are O(log n) in a heap.", d="easy", t=40, ver=M("Heap-based priority queue.")),
    ]


def heapsort_q():
    s = "heapsort"
    built, states, final = A.heapsort_states(H2)
    return [
        mk_ref(s, "trace", f"HeapSort builds a max-heap from {H2} using bottom-up heapify. What is the array after building?", "heapsort_built", {"items": H2},
               [_s(H2), _s(A.build_heap_by_insertion(H2)), _s(sorted(H2))], "Sift down from the last parent: index 2 needs no change, index 1 (31) swaps with 38, then index 0 (13) sinks past 38 and 36.", d="medium", t=80,
               trace=[{"label": "heapify bottom-up", "state": _s(built)}]),
        mk_ref(s, "trace", f"HeapSort on {H2}: after building the max-heap, the first extraction pass swaps the root with the last element of the heap and sifts down. What is the array after that FIRST pass?", "heapsort_pass", {"items": H2, "k": 1},
               [_s(built), _s(states[1]), _s(final)], "The root 38 swaps with the last heap element (26) and is frozen at the end; 26 then sinks past 36 and 31.", d="hard", t=100,
               trace=[{"label": "built heap", "state": _s(built)}] + [{"label": f"after pass {i + 1}", "state": _s(x)} for i, x in enumerate(states)]),
        mk_ref(s, "trace", f"Continuing HeapSort on {H2}: what is the array after the SECOND extraction pass?", "heapsort_pass", {"items": H2, "k": 2},
               [_s(states[0]), _s(states[2]), _s(final)], "The two largest values (38, 36) are now fixed at the end of the array.", d="hard", t=100,
               trace=[{"label": f"after pass {i + 1}", "state": _s(x)} for i, x in enumerate(states)]),
        mk(s, "complexity", "What are HeapSort's time and extra-space complexities?", "O(n log n) time in every case; O(1) extra space", ["O(n²) worst time; O(1) extra space", "O(n log n) time; O(n) extra space", "O(n) time; O(1) extra space"],
           "Building is O(n) and n extractions cost O(log n) each, all in place.", d="medium", t=45, complexity={"time": "O(n log n)", "best": "O(n log n)", "worst": "O(n log n)", "space": "O(1)"}, ver=M("Standard HeapSort analysis.")),
        mk(s, "conceptual", "Is HeapSort stable?", "No — long-distance swaps can reorder equal keys", ["Yes, always", "Yes, if a min-heap is used", "Only for arrays with distinct keys"], "Moving the root to the end can jump an element past an equal one.", d="medium", t=45, ver=M("HeapSort is not stable.")),
        mk(s, "conceptual", "To sort an array into ASCENDING order in place with HeapSort, which kind of heap is built?", "A max-heap", ["A min-heap", "A binary search tree", "A complete graph"], "The maximum is repeatedly moved to the end of the array.", d="easy", t=35, ver=M("Ascending in-place HeapSort uses max-heap.")),
    ]


# --- hashing ----------------------------------------------------------------------------------------------


def hash_functions():
    s = "hash-functions"
    return [
        mk_ref(s, "conceptual", "A hash table has 10 slots and the division-method hash h(k) = k mod 10. In which slot does key 47 go?", "hash_index", {"key": 47, "m": 10}, ["4", "47", "3"], "47 mod 10 = 7.", d="easy", t=30),
        mk_ref(s, "conceptual", "A table of 13 slots holds 26 keys using chaining. What is the load factor?", "hash_load_factor", {"n": 26, "m": 13}, ["0.5", "13", "39"], "Load factor α = n / m = 26 / 13.", d="easy", t=35),
        mk(s, "conceptual", "Which is a desirable property of a good hash function?", "It spreads keys uniformly across the table and is cheap to compute", ["It maps every key to slot 0", "It never needs to be deterministic", "It produces a different table size per call"],
           "Uniform spreading minimises collisions; determinism is mandatory.", d="easy", t=40, ver=M("Standard hash-function criteria.")),
        mk(s, "conceptual", "Why is a prime table size often chosen with the division method?", "It reduces the chance that patterns in the keys cause many collisions", ["Primes make hashing O(1) without collisions", "Primes need no modulo operation", "It lets the table hold more keys than slots"],
           "A prime modulus avoids sharing factors with common key patterns.", d="medium", t=45, ver=M("Standard advice for division hashing.")),
        mk(s, "output", "What does this code print?", "True", ["False", "None", "Error"], "Both calls compute the same deterministic function of the key.", d="easy", t=30,
           code="def h(k, m=7):\n    return k % m\n\nprint(h(100) == h(100))", ver=S("True")),
        mk(s, "scenario", "Two different keys map to the same slot. What is this called?", "A collision", ["An overflow of the key", "Rehashing", "Underflow"], "Collisions must be resolved by chaining or probing.", d="easy", t=25, ver=M("Definition of collision.")),
        mk(s, "complexity", "What is the average-case time for search/insert/delete in a hash table with a good hash function and a bounded load factor?", "O(1)", ["O(log n)", "O(n)", "O(n log n)"], "Expected chain/probe lengths stay constant when the load factor is bounded.", d="medium", t=35, complexity={"time": "O(1) average, O(n) worst", "space": "O(n)"}, ver=M("Standard average-case hash-table analysis.")),
    ]


def chaining():
    s = "separate-chaining"
    keys = [15, 53, 50, 56, 27, 58, 74, 39]
    keys2 = [12, 19, 26, 5, 6, 13]
    return [
        mk_ref(s, "trace", f"Keys {keys} are inserted (in this order) into a table of 7 buckets using h(k) = k mod 7 and separate chaining (new keys appended at the END of a chain). Which listing of buckets is correct?", "hash_chain", {"keys": keys, "m": 7},
               [_chain_alt(keys, 7, front=True), _chain_alt(keys, 5), _chain_alt(keys, 8)], "Group keys by k mod 7; within a bucket keep insertion order.", d="medium", t=90,
               trace=[{"label": f"insert {k}", "state": f"bucket {k % 7}"} for k in keys]),
        mk_ref(s, "complexity", f"Keys {keys2} are hashed with h(k) = k mod 7 into a table using chaining. What is the length of the LONGEST chain?", "hash_chain_longest", {"keys": keys2, "m": 7}, ["1", "2", "3"],
               "12, 19, 26 and 5 all hash to bucket 5, while 6 and 13 share bucket 6.", d="medium", t=70, complexity={"time": "O(chain length) per lookup", "space": "O(n + m)"}),
        mk(s, "conceptual", "In separate chaining, what is stored in each table slot?", "The head of a linked list of all keys that hash to that slot", ["Exactly one key; others are discarded", "A pointer to the next empty slot", "A sorted copy of the whole table"], "Colliding keys share the slot's chain.", d="easy", t=35, ver=M("Definition of separate chaining.")),
        mk(s, "complexity", "What is the worst-case time to search a separate-chaining table of n keys if every key hashes to the same slot?", "O(n)", ["O(1)", "O(log n)", "O(n²)"], "All keys end up in one chain.", d="medium", t=40, complexity={"time": "O(n) worst, O(1 + α) average", "space": "O(n + m)"}, ver=M("Degenerate chain.")),
        mk(s, "conceptual", "With separate chaining, can the load factor exceed 1?", "Yes, because chains can hold any number of keys", ["No, the table would crash", "Only if the table is rehashed first", "Only for string keys"], "Chains are unbounded, unlike open addressing.", d="medium", t=40, ver=M("Chaining allows alpha > 1.")),
        mk(s, "scenario", "A hash table must tolerate many more keys than slots and support easy deletion without markers. Which collision strategy fits?", "Separate chaining", ["Linear probing", "Double hashing", "Quadratic probing"], "Deleting from a chain is just removing a list node.", d="medium", t=45, ver=M("Chaining deletion is simple.")),
    ]


def _chain_alt(keys, m, front=False):
    t = A.hash_chaining(keys, m)
    if front:
        t = [b[::-1] for b in t]
    return " | ".join(f"{i}: {'→'.join(map(str, b)) if b else '—'}" for i, b in enumerate(t))


def open_addr():
    s = "open-addressing"
    return [
        mk(s, "conceptual", "In open addressing (closed hashing), where is a colliding key stored?", "In another slot of the same table, found by a probe sequence", ["In a linked list outside the table", "In a separate overflow file", "It is discarded"], "All keys live inside the table array.", d="easy", t=35, ver=M("Definition of open addressing.")),
        mk(s, "conceptual", "What is the maximum load factor possible in an open-addressing table?", "1", ["Unlimited", "0.5", "2"], "Each slot holds at most one key, so n ≤ m.", d="easy", t=30, ver=M("n <= m for open addressing.")),
        mk(s, "conceptual", "Why can't a deleted slot simply be set back to 'empty' in open addressing?", "It could break the probe sequence of other keys, so a 'deleted' marker (tombstone) is used", ["It would corrupt the hash function", "Empty slots cannot be reused", "The table size must change"], "A search stops at an empty slot, so removing a key that others probed past could hide them.", d="hard", t=60, ver=M("Tombstone rationale.")),
        mk(s, "conceptual", "What is primary clustering?", "Long runs of occupied adjacent slots that make further collisions more likely", ["A hash function that maps keys evenly", "Storing keys in sorted order", "Splitting the table in two"], "It is characteristic of linear probing.", d="medium", t=40, ver=M("Clustering definition.")),
        mk(s, "scenario", "Memory is tight and keys are small, with a load factor kept below about 0.7. Which collision strategy avoids per-key pointer overhead?", "Open addressing", ["Separate chaining", "Linked-list buckets", "A binary tree per slot"], "No pointers are stored per key.", d="medium", t=45, ver=M("Open addressing stores keys in the array.")),
    ]


def linear_probe():
    s = "linear-probing"
    k1 = [34, 46, 32, 44, 47, 36]
    k2 = [10, 20, 30, 15]
    return [
        mk_ref(s, "trace", f"Keys {k1} are inserted in order into a table of size 10 with h(k) = k mod 10 and linear probing (h + i). What is the final table (slots 0–9, '-' empty)?", "hash_linear", {"keys": k1, "m": 10},
               [_tbl(A.hash_open(k1, 10, "quadratic")[0]), _tbl(A.hash_open(k1, 10, "double", lambda k: 7 - k % 7)[0]), _tbl(A.hash_open(k1[::-1], 10)[0])],
               "34→4, 46→6, 32→2, 44→4 taken→5, 47→7, 36→6 taken→7 taken→8.", d="hard", t=120,
               trace=[{"label": f"insert {k}", "state": _tbl(A.hash_open(k1[: i + 1], 10)[0])} for i, k in enumerate(k1)]),
        mk_ref(s, "trace", f"Keys {k2} are inserted in order into a table of size 5 with h(k) = k mod 5 and linear probing. What is the final table?", "hash_linear", {"keys": k2, "m": 5},
               [_tbl(A.hash_open(k2, 5, "quadratic")[0]), _tbl(A.hash_open(k2[::-1], 5)[0]), _tbl(A.hash_open([15, 10, 20, 30], 5)[0])],
               "10→0, 20→0 taken→1, 30→0, 1 taken→2, 15→0, 1, 2 taken→3.", d="medium", t=90,
               trace=[{"label": f"insert {k}", "state": _tbl(A.hash_open(k2[: i + 1], 5)[0])} for i, k in enumerate(k2)]),
        mk_ref(s, "complexity", f"Using the table from keys {k1} (size 10, linear probing, same insertion order), how many probes (slots examined) did inserting key 36 need?", "hash_linear_probes", {"keys": k1, "m": 10, "key": 36}, ["1", "2", "4"],
               "36 mod 10 = 6 (taken by 46), 7 (taken by 47), 8 is free: three probes.", d="medium", t=75, complexity={"time": "O(probe length)", "space": "O(1)"}),
        mk(s, "conceptual", "Linear probing is MOST associated with which problem?", "Primary clustering", ["Secondary clustering only", "Chain overflow", "Table size must be a power of two"], "Occupied runs grow and attract further keys.", d="easy", t=35, ver=M("Linear probing yields primary clustering.")),
        mk(s, "conceptual", "In linear probing, if the probe sequence is h(k), h(k)+1, h(k)+2, ... (mod m), what is the step between probes?", "A constant step of 1", ["An increasing square", "A second hash value", "A random number"], "That is the definition of linear probing.", d="easy", t=25, ver=M("Definition of linear probing.")),
        mk(s, "output", "What does this code print?", "[None, 5, 14, 7]", ["[7, 14, 5, None]", "[None, 7, 14, 5]", "[14, 7, 5, None]"], "7 → slot 3; 14 → slot 2; 5 → slot 1; slot 0 stays empty.", d="hard", t=90,
           code="m = 4\nt = [None] * m\nfor k in (7, 14, 5):\n    i = k % m\n    while t[i] is not None:\n        i = (i + 1) % m\n    t[i] = k\nprint(t)", ver=S("[None, 5, 14, 7]")),
    ]


def quad_probe():
    s = "quadratic-probing"
    k1 = [87, 95, 99, 30, 51, 79]
    return [
        mk_ref(s, "trace", f"Keys {k1} are inserted in order into a table of size 11 with h(k) = k mod 11 and quadratic probing (h + i²). What is the final table (slots 0–10)?", "hash_quadratic", {"keys": k1, "m": 11},
               [_tbl(A.hash_open(k1, 11, "linear")[0]), _tbl(A.hash_open(k1[::-1], 11, "quadratic")[0]), _tbl(A.hash_open(sorted(k1), 11, "quadratic")[0])],
               "Colliding keys try offsets 1, 4, 9, ... from their home slot.", d="hard", t=120,
               trace=[{"label": f"insert {k}", "state": _tbl(A.hash_open(k1[: i + 1], 11, "quadratic")[0])} for i, k in enumerate(k1)]),
        mk_ref(s, "complexity", f"For the same insertions {k1} (size 11, quadratic probing), how many probes did the key 51 need?", "hash_quadratic_probes", {"keys": k1, "m": 11, "key": 51}, ["1", "2", "3"],
               "51 mod 11 = 7; offsets +0, +1, +4 hit occupied slots 7, 8 and 0 before the free slot at +9.", d="medium", t=80, complexity={"time": "O(probe length)", "space": "O(1)"}),
        mk(s, "conceptual", "What problem does quadratic probing reduce compared with linear probing?", "Primary clustering", ["Secondary clustering", "Collisions between different hash values", "Table resizing"], "Steps grow as 1, 4, 9, ... so runs don't keep extending adjacent slots (secondary clustering remains).", d="medium", t=45, ver=M("Quadratic probing eliminates primary but not secondary clustering.")),
        mk(s, "conceptual", "Keys with the SAME home slot follow the same probe sequence in quadratic probing. This weakness is called:", "Secondary clustering", ["Primary clustering", "Overflow", "Rehash collapse"], "Double hashing addresses it.", d="medium", t=40, ver=M("Secondary clustering definition.")),
        mk(s, "conceptual", "For quadratic probing to be guaranteed to find a free slot, which condition is commonly required?", "The table size is prime and the table is at most half full", ["The table size is even and fully loaded", "The keys are sorted", "The load factor equals 1"], "That guarantees the first ⌈m/2⌉ probe positions are distinct.", d="hard", t=60, ver=M("Classic theorem for h+i^2 with prime m.")),
    ]


def double_hash():
    s = "double-hashing"
    k1 = [34, 46, 32, 44, 47, 36]
    h2 = lambda k: 7 - k % 7
    return [
        mk_ref(s, "trace", f"Double hashing uses h1(k) = k mod 10 and h2(k) = 7 − (k mod 7), probing (h1 + i·h2) mod 10. Keys {k1} are inserted in order into a table of size 10. What is the final table?", "hash_double", {"keys": k1, "m": 10, "q": 7},
               [_tbl(A.hash_open(k1, 10, "linear")[0]), _tbl(A.hash_open(k1, 10, "quadratic")[0]), _tbl(A.hash_open(k1[::-1], 10, "double", h2)[0])],
               "A colliding key jumps by its own step h2(k) instead of 1 or i².", d="hard", t=130,
               trace=[{"label": f"insert {k}", "state": _tbl(A.hash_open(k1[: i + 1], 10, "double", h2)[0])} for i, k in enumerate(k1)]),
        mk_ref(s, "complexity", f"With the same function pair and keys {k1} (table size 10), how many probes did key 44 need?", "hash_double_probes", {"keys": k1, "m": 10, "q": 7, "key": 44}, ["1", "3", "4"],
               "44 mod 10 = 4, which 34 occupies, so it jumps by h2(44) = 7 − 2 = 5 to slot 9: two probes.", d="hard", t=90, complexity={"time": "O(probe length)", "space": "O(1)"}),
        mk(s, "conceptual", "What is the main advantage of double hashing over linear and quadratic probing?", "Different keys with the same home slot follow different probe sequences, reducing clustering", ["It never collides", "It needs no second function", "It allows load factors above 1"], "The step size depends on the key.", d="medium", t=45, ver=M("Double hashing mitigates both clustering types.")),
        mk(s, "conceptual", "Why must h2(k) never be 0 in double hashing?", "A step of 0 would probe the same slot forever", ["It would make the table smaller", "It would make keys negative", "Zero is not a valid integer hash"], "The probe sequence must advance to visit other slots.", d="medium", t=40, ver=M("Step 0 yields an infinite loop on the home slot.")),
        mk(s, "conceptual", "For double hashing to be able to probe every slot, the step h2(k) should be:", "Relatively prime to the table size", ["Always even", "Equal to the table size", "Larger than the key"], "Coprime step and size yield a full cycle through all slots.", d="hard", t=60, ver=M("Number-theoretic condition for full-cycle probing.")),
    ]


def all_questions():
    out = []
    for f in (heap_ops, heapsort_q, hash_functions, chaining, open_addr, linear_probe, quad_probe, double_hash):
        out.extend(f())
    return out
