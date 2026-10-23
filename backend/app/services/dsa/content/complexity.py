"""Topics A (Introduction and Complexity Analysis) and B (Arrays)."""

from __future__ import annotations

from .build import M, S, mk, mk_ref, ref


def basic_concepts():
    s = "basic-concepts"
    return [
        mk(s, "conceptual", "Which statement best defines an algorithm?", "A finite, unambiguous sequence of steps that solves a problem and terminates",
           ["Any program that compiles without errors", "A sequence of steps that may run forever as long as it is correct", "A data structure that stores items in order"],
           "An algorithm must be finite, well defined, take zero or more inputs, produce output and terminate.", d="easy", t=40, ver=M("Standard textbook definition of an algorithm.")),
        mk(s, "conceptual", "What does an Abstract Data Type (ADT) specify?", "The operations and their behaviour, without fixing the implementation",
           ["The exact memory layout used by the compiler", "Only the programming language to use", "The running time of every operation in nanoseconds"],
           "An ADT describes what operations do; concrete data structures (array, linked list) decide how.", d="easy", t=40, ver=M("An ADT is defined by its operations/behaviour; implementation is separate.")),
        mk(s, "conceptual", "Which of these is a NON-linear data structure?", "Tree",
           ["Array", "Stack", "Queue"], "Arrays, stacks and queues arrange elements in a sequence; a tree is hierarchical, so an element can have several successors.", d="easy", t=30,
           ver=M("Linear vs non-linear classification of basic structures.")),
        mk(s, "conceptual", "Which property is NOT required of a correct algorithm?", "It must use the least possible memory",
           ["It must terminate after finitely many steps", "Each step must be well defined", "It must produce the desired output for valid input"],
           "Termination, definiteness and correctness are required; minimal memory is a quality goal, not a requirement.", d="medium", t=40,
           ver=M("Required algorithm properties: finiteness, definiteness, input/output, effectiveness.")),
    ]


def time_space():
    s = "time-space-complexity"
    return [
        mk(s, "complexity", "What is the time complexity of this code?", "O(n)", ["O(1)", "O(n²)", "O(log n)"],
           "The loop body is O(1) and runs n times.", d="easy", t=30, code="total = 0\nfor i in range(n):\n    total += i",
           complexity={"time": "O(n)", "space": "O(1)"}, ver=M("Single loop of n constant-time iterations.")),
        mk(s, "complexity", "What is the time complexity of this code?", "O(n²)", ["O(n)", "O(n log n)", "O(2ⁿ)"],
           "The inner loop runs n times for each of the n outer iterations: n × n.", d="easy", t=40,
           code="count = 0\nfor i in range(n):\n    for j in range(n):\n        count += 1", complexity={"time": "O(n²)", "space": "O(1)"},
           ver=M("Two nested full-range loops give n*n constant-time operations.")),
        mk(s, "complexity", "What is the time complexity of this loop?", "O(log n)", ["O(n)", "O(√n)", "O(n log n)"],
           "i doubles each time, so the loop runs about log₂ n times.", d="medium", t=45, code="i = 1\nwhile i < n:\n    i *= 2",
           complexity={"time": "O(log n)", "space": "O(1)"}, ver=M("Multiplicative growth of the loop variable: floor(log2(n)) + 1 iterations at most.")),
        mk(s, "complexity", "What is the auxiliary space complexity of this recursive function?", "O(n)", ["O(1)", "O(log n)", "O(n²)"],
           "Each pending call keeps a stack frame, and the recursion depth reaches n.", d="medium", t=45,
           code="def total(n):\n    if n == 0:\n        return 0\n    return n + total(n - 1)", complexity={"time": "O(n)", "space": "O(n)"},
           ver=M("Recursion depth n gives n stack frames; no other storage.")),
        mk(s, "complexity", "What is the time complexity of this code?", "O(n log n)", ["O(n)", "O(n²)", "O(log² n)"],
           "The outer loop runs n times and the inner loop runs about log n times for each.", d="medium", t=50,
           code="for i in range(n):\n    j = 1\n    while j < n:\n        j *= 2", complexity={"time": "O(n log n)", "space": "O(1)"},
           ver=M("n iterations of a loop that doubles j, i.e. log n each.")),
        mk(s, "conceptual", "Which phrase correctly separates time complexity from space complexity?", "Time counts the basic operations performed; space counts the extra memory used as the input grows",
           ["Time counts the lines of code; space counts the number of variables declared", "Time is measured in seconds; space is measured in operations", "Time depends on hardware only; space depends on the compiler only"],
           "Both are functions of input size, independent of any particular machine.", d="easy", t=40, ver=M("Standard definitions of time and space complexity as functions of input size.")),
    ]


def tradeoffs():
    s = "time-space-tradeoffs"
    return [
        mk(s, "scenario", "A web service computes the same expensive function for many repeated inputs. Which change trades memory for time?", "Cache (memoise) results in a hash table",
           ["Recompute the value every time to save memory", "Sort the inputs before each call", "Replace the function with a longer loop"],
           "Storing computed results uses extra space but avoids recomputation, reducing running time.", d="easy", t=40, ver=M("Memoisation is the canonical time-for-space trade.")),
        mk(s, "conceptual", "Which technique is a typical example of spending MORE time to save space?", "Compressing data and decompressing it when needed",
           ["Precomputing a lookup table", "Memoising a recursive function", "Storing an extra index for fast search"],
           "Compression shrinks storage but costs CPU time to compress and decompress.", d="medium", t=45, ver=M("Compression trades time for space; lookup tables and indexes do the reverse.")),
        mk(s, "scenario", "An embedded device has very little RAM but no strict deadline. Between a method needing O(n) extra memory with O(n) time and one needing O(1) extra memory with O(n²) time, which fits best?", "The O(1)-space, O(n²)-time method",
           ["The O(n)-space, O(n)-time method, because time always matters more", "Neither, because every algorithm needs O(n) space", "Whichever has the shorter code"],
           "When memory is the binding constraint and time is flexible, the low-space method is the better trade.", d="medium", t=60,
           ver=M("Judgement question: constraint (RAM) dominates; small n or relaxed deadline makes extra time acceptable.")),
        mk(s, "output", "What does this code print?", "True", ["False", "None", "Error"],
           "Memoising with a dict turns exponential recomputation into one computation per value; the results are equal.", d="medium", t=60,
           code="memo = {}\ndef fib(n):\n    if n < 2:\n        return n\n    if n not in memo:\n        memo[n] = fib(n - 1) + fib(n - 2)\n    return memo[n]\n\ndef slow(n):\n    return n if n < 2 else slow(n - 1) + slow(n - 2)\n\nprint(fib(15) == slow(15))",
           ver=S("True")),
    ]


def big_o():
    s = "big-o"
    return [
        mk(s, "conceptual", "Big O notation gives which kind of bound on a function's growth?", "An asymptotic upper bound",
           ["An exact running time in seconds", "An asymptotic lower bound", "The average-case time only"],
           "f(n) = O(g(n)) means f grows no faster than a constant multiple of g for large n.", d="easy", t=30, ver=M("Definition of Big O.")),
        mk(s, "complexity", "Which function has the SLOWEST growth for large n?", "n log n", ["n²", "2ⁿ", "n³"],
           "n log n grows more slowly than any polynomial of degree 2 or above, and far more slowly than 2ⁿ.", d="easy", t=30, complexity={"time": "O(n log n)"},
           ver=M("Standard growth ordering: log n < n < n log n < n² < n³ < 2ⁿ.")),
        mk(s, "conceptual", "Simplify f(n) = 5n² + 3n + 7 using Big O.", "O(n²)", ["O(n)", "O(5n²)", "O(n² + n)"],
           "Drop constant factors and lower-order terms.", d="easy", t=30, ver=M("Big O drops constants and lower-order terms.")),
        mk(s, "conceptual", "Which statement about Big O is TRUE?", "If f(n) = O(n) then f(n) is also O(n²)",
           ["O(n) and O(n²) can never describe the same function", "Big O must always be a tight bound", "O(log n) grows faster than O(n)"],
           "Big O is only an upper bound, so any slower-growing function is also in the larger class.", d="medium", t=45, ver=M("Big O is an upper bound, not necessarily tight.")),
        mk(s, "conceptual", "Which expression is NOT equal to O(n)?", "n log n", ["3n + 10", "n/2", "100n"],
           "n log n grows strictly faster than n, so it is not O(n); the others differ from n only by constants.", d="medium", t=40, ver=M("n log n is not bounded by c*n for any constant c.")),
    ]


def omega():
    s = "omega"
    return [
        mk(s, "conceptual", "Omega (Ω) notation describes:", "An asymptotic lower bound", ["An asymptotic upper bound", "An exact bound only", "The worst case only"],
           "f(n) = Ω(g(n)) means f grows at least as fast as a constant multiple of g for large n.", d="easy", t=30, ver=M("Definition of Omega.")),
        mk(s, "conceptual", "Which statement is TRUE for f(n) = 3n + 2?", "f(n) = Ω(n)", ["f(n) = Ω(n²)", "f(n) = Ω(2ⁿ)", "f(n) = Ω(n³)"],
           "3n + 2 ≥ 3n for all n, so it is bounded below by a constant times n; it does not grow as fast as n².", d="easy", t=40, ver=M("3n+2 >= 3n; no quadratic lower bound holds.")),
        mk(s, "scenario", "An engineer proves that any comparison-based sorting algorithm needs Ω(n log n) comparisons. What does this mean?", "No comparison-based sort can beat roughly n log n comparisons in the worst case",
           ["Every comparison sort takes exactly n log n comparisons on every input", "Some comparison sorts run in O(n) in the worst case", "Sorting is impossible in less than n² time"],
           "A lower bound limits every algorithm of that class; merge sort and heap sort match it.", d="medium", t=60, ver=M("Decision-tree lower bound for comparison sorting.")),
        mk(s, "conceptual", "Which statement about Ω is correct?", "If f(n) = Ω(n²) then f(n) is also Ω(n)",
           ["If f(n) = Ω(n²) then f(n) must be O(n²)", "Ω can only be used for best-case analysis", "Ω(n) and Ω(n²) are the same class"],
           "Anything growing at least as fast as n² also grows at least as fast as n.", d="medium", t=45, ver=M("Omega classes are nested: Omega(n^2) is contained in Omega(n).")),
    ]


def theta():
    s = "theta"
    return [
        mk(s, "conceptual", "Θ (Theta) notation describes:", "A tight bound: both an upper and a lower bound", ["Only an upper bound", "Only a lower bound", "The best case only"],
           "f(n) = Θ(g(n)) means f is both O(g(n)) and Ω(g(n)).", d="easy", t=30, ver=M("Definition of Theta.")),
        mk(s, "conceptual", "What is the Θ bound of f(n) = 4n² + 10n + 2?", "Θ(n²)", ["Θ(n)", "Θ(n³)", "Θ(4n²)"],
           "The n² term dominates; constants are dropped.", d="easy", t=30, ver=M("Dominant term n^2 after dropping constants.")),
        mk(s, "conceptual", "For which function is f(n) = Θ(n) FALSE?", "f(n) = n log n", ["f(n) = 7n", "f(n) = n + 100", "f(n) = 2n - 5"],
           "n log n is Ω(n) but not O(n), so it has no Θ(n) bound.", d="medium", t=40, ver=M("n log n is not O(n).")),
        mk(s, "conceptual", "Insertion sort takes Θ(n) on already-sorted input but Θ(n²) on reverse-sorted input. Which statement is accurate?", "Its running time is O(n²) and Ω(n), but it has no single Θ bound over all inputs",
           ["It is Θ(n²) for every input", "It is Θ(n) for every input", "Theta cannot be applied to sorting algorithms"],
           "Different inputs give different tight bounds, so only O(n²) and Ω(n) hold over all inputs.", d="hard", t=75,
           ver=M("Overall bounds: best case n comparisons, worst case ~n^2/2; no one function bounds both sides.")),
    ]


def basic_ds():
    s = "basic-data-structures"
    return [
        mk(s, "scenario", "You need constant-time access to the i-th element by position. Which structure fits?", "Array", ["Singly linked list", "Queue implemented by a linked list", "Binary tree"],
           "Arrays store elements contiguously, so index arithmetic gives O(1) access.", d="easy", t=30, ver=M("Random access is O(1) for arrays.")),
        mk(s, "scenario", "A browser's back button must return pages in the reverse order they were visited. Which data structure models this?", "Stack", ["Queue", "Binary search tree", "Hash table"],
           "The most recently visited page is the first one to go back: last in, first out.", d="easy", t=30, ver=M("LIFO behaviour.")),
        mk(s, "scenario", "A printer receives jobs and must print them in arrival order. Which structure fits?", "Queue", ["Stack", "Heap", "Graph"],
           "First come, first served is FIFO.", d="easy", t=30, ver=M("FIFO behaviour.")),
        mk(s, "output", "What does this code print?", "[3, 2, 1]", ["[1, 2, 3]", "[1, 3, 2]", "[3, 1, 2]"],
           "A list used as a stack returns items in reverse order of pushing.", d="easy", t=35,
           code="stack = []\nfor x in (1, 2, 3):\n    stack.append(x)\nout = []\nwhile stack:\n    out.append(stack.pop())\nprint(out)", ver=S("[3, 2, 1]")),
        mk(s, "output", "What does this code print?", "[1, 2, 3]", ["[3, 2, 1]", "[1, 3, 2]", "[2, 1, 3]"],
           "collections.deque with popleft() is FIFO, so items come out in insertion order.", d="easy", t=35,
           code="from collections import deque\nq = deque()\nfor x in (1, 2, 3):\n    q.append(x)\nout = []\nwhile q:\n    out.append(q.popleft())\nprint(out)", ver=S("[1, 2, 3]")),
    ]


# --- B. Arrays ----------------------------------------------------------------------------------


def array_memory():
    s = "array-memory"
    out = [
        mk_ref(s, "conceptual", "An integer array starts at address 1000 and each element takes 4 bytes. Using zero-based indexing, what is the address of element A[6]?", "array_address",
               {"base": 1000, "i": 6, "w": 4}, ["1006", "1020", "1028"], "Address = base + i × width = 1000 + 6 × 4.", d="easy", t=40),
        mk_ref(s, "conceptual", "An array declared with indices 1..10 (one-based) starts at address 200 and each element is 2 bytes. What is the address of element 5?", "array_address",
               {"base": 200, "i": 4, "w": 2}, ["210", "205", "202"], "Offset is (5 − 1) = 4 elements: 200 + 4 × 2.", d="medium", t=60),
        mk_ref(s, "conceptual", "An array has lower bound 5 and upper bound 20. How many elements does it hold?", "array_len", {"lb": 5, "ub": 20}, ["15", "17", "20"],
               "Length = UB − LB + 1.", d="easy", t=30),
        mk(s, "conceptual", "Why is index access O(1) in an array?", "Elements are contiguous, so the address is computed directly from the base address and index",
           ["The array keeps a sorted index of all elements", "Each element stores a pointer to the next", "The compiler searches for the element at compile time"],
           "Base + index × element size is a single arithmetic operation.", d="easy", t=40, ver=M("Contiguous memory layout gives direct address computation.")),
    ]
    return out


def array_traversal():
    s = "array-traversal"
    return [
        mk(s, "output", "What does this code print?", "10", ["15", "4", "6"], "The loop adds every element: 1 + 2 + 3 + 4.", d="easy", t=30,
           code="a = [1, 2, 3, 4]\ns = 0\nfor x in a:\n    s += x\nprint(s)", ver=S("10")),
        mk(s, "output", "What does this code print?", "[4, 3, 2, 1]", ["[1, 2, 3, 4]", "[4, 3, 2]", "[3, 2, 1, 4]"], "Traversing indices from the last to the first builds the reverse.", d="easy", t=35,
           code="a = [1, 2, 3, 4]\nr = []\nfor i in range(len(a) - 1, -1, -1):\n    r.append(a[i])\nprint(r)", ver=S("[4, 3, 2, 1]")),
        mk(s, "complexity", "What is the time complexity of finding the maximum of an unsorted array of n numbers by traversal?", "O(n)", ["O(1)", "O(log n)", "O(n log n)"],
           "Every element must be inspected once.", d="easy", t=30, complexity={"time": "O(n)", "space": "O(1)"}, ver=M("Single full traversal.")),
        mk(s, "output", "What does this code print? (watch the slice)", "[2, 3]", ["[1, 2]", "[2, 3, 4]", "[1, 2, 3]"], "a[1:3] takes indices 1 and 2; the end index is excluded.", d="medium", t=35,
           code="a = [1, 2, 3, 4]\nprint(a[1:3])", ver=S("[2, 3]")),
    ]


def array_insert_delete():
    s = "array-insert-delete"
    return [
        mk_ref(s, "conceptual", "In the array [10, 20, 30, 40, 50] (size 5, spare capacity), 25 is inserted at index 2 by shifting. What is the array afterwards?", "array_insert_result",
               {"arr": [10, 20, 30, 40, 50], "pos": 2, "x": 25}, ["[10, 20, 25, 40, 50]", "[10, 25, 20, 30, 40, 50]", "[25, 10, 20, 30, 40, 50]"],
               "Elements from index 2 onward shift right by one, then 25 is placed at index 2.", d="easy", t=40),
        mk_ref(s, "conceptual", "How many elements must be shifted to insert a new element at index 1 of an array holding 8 elements?", "array_shift_insert",
               {"arr": [1, 2, 3, 4, 5, 6, 7, 8], "pos": 1}, ["8", "1", "6"], "Elements at indices 1..7 (that is 8 − 1 = 7) each move one place right.", d="medium", t=45),
        mk_ref(s, "conceptual", "How many elements must be shifted left when deleting the element at index 2 of an array holding 9 elements?", "array_shift_delete",
               {"arr": list(range(9)), "pos": 2}, ["9", "7", "2"], "Elements at indices 3..8 each move one place left: 9 − 2 − 1 elements.", d="medium", t=45),
        mk_ref(s, "conceptual", "What is the array after deleting the element at index 3 from [4, 8, 15, 16, 23, 42] by shifting left?", "array_delete_result",
               {"arr": [4, 8, 15, 16, 23, 42], "pos": 3}, ["[4, 8, 15, 23, 42, 42]", "[4, 8, 16, 23, 42]", "[8, 15, 16, 23, 42]"], "Removing index 3 (value 16) leaves the other elements in order.", d="easy", t=40),
        mk(s, "conceptual", "Which operation is O(1) on a plain array that is not full?", "Appending at the end",
           ["Inserting at the front", "Deleting from the front", "Inserting in the middle"], "Only appending at the next free slot needs no shifting.", d="easy", t=30, ver=M("Front/middle insert and delete shift O(n) elements.")),
    ]


def array_ssm():
    s = "array-sort-search-merge"
    return [
        mk_ref(s, "conceptual", "Merge the sorted arrays [2, 5, 9] and [1, 5, 8, 12] using the standard two-pointer merge. What is the result?", "array_merge_sorted",
               {"left": [2, 5, 9], "right": [1, 5, 8, 12]}, ["[1, 2, 5, 8, 9, 12]", "[1, 2, 5, 5, 9, 8, 12]", "[2, 5, 9, 1, 5, 8, 12]"], "Repeatedly take the smaller front element; equal elements are both kept.", d="easy", t=50),
        mk_ref(s, "complexity", "How many element comparisons does the two-pointer merge of [1, 3, 5, 7] and [2, 4, 6, 8] make?", "merge_comps",
               {"left": [1, 3, 5, 7], "right": [2, 4, 6, 8]}, ["8", "4", "6"], "Comparisons continue until one array is exhausted: here 7 (the leftover 8 is copied without a comparison).", d="medium", t=60,
               complexity={"time": "O(m + n)", "space": "O(m + n)"}),
        mk(s, "scenario", "You must find a value in a sorted array of one million numbers many times. Which approach is best?", "Binary search",
           ["Linear search each time", "Sort the array again before every search", "Bubble sort then linear search"], "Binary search needs only about 20 comparisons on a sorted array.", d="easy", t=40, ver=M("Sorted input enables O(log n) search.")),
        mk(s, "conceptual", "What is the main extra cost of merging two sorted arrays into a new array?", "O(m + n) auxiliary space",
           ["O(1) auxiliary space", "O(log n) auxiliary space", "O(m × n) auxiliary space"], "The output array holds all m + n elements.", d="medium", t=40, ver=M("Standard merge needs an output buffer of size m+n.")),
    ]


def array_complexity():
    s = "array-complexity"
    return [
        mk(s, "complexity", "Match the worst-case time: inserting at the FRONT of an array holding n elements (by shifting).", "O(n)", ["O(1)", "O(log n)", "O(n²)"], "All n existing elements shift one place.", d="easy", t=30,
           complexity={"time": "O(n)", "space": "O(1)"}, ver=M("Front insert shifts n elements.")),
        mk(s, "complexity", "What is the time complexity of reading A[i] in an array?", "O(1)", ["O(n)", "O(log n)", "O(i)"], "The address is computed directly.", d="easy", t=25, complexity={"time": "O(1)", "space": "O(1)"}, ver=M("Direct addressing.")),
        mk(s, "complexity", "What is the worst-case time of linear search in an unsorted array of n elements?", "O(n)", ["O(1)", "O(log n)", "O(n log n)"], "The target may be last or absent, so all n elements are checked.", d="easy", t=30,
           complexity={"time": "O(n)", "best": "O(1)", "average": "O(n)", "worst": "O(n)", "space": "O(1)"}, ver=M("Linear search worst case n comparisons.")),
        mk(s, "complexity", "Appending to a dynamic array (doubling when full) has which amortised cost per append?", "O(1)", ["O(n)", "O(log n)", "O(n²)"],
           "Occasional O(n) resizes are spread across many cheap appends, giving O(1) amortised.", d="hard", t=60, complexity={"time": "O(1) amortised", "worst": "O(n) for a single resize", "space": "O(n)"},
           ver=M("Geometric doubling gives total copy cost < 2n across n appends.")),
    ]


def all_questions():
    out = []
    for f in (basic_concepts, time_space, tradeoffs, big_o, omega, theta, basic_ds, array_memory, array_traversal, array_insert_delete, array_ssm, array_complexity):
        out.extend(f())
    return out
