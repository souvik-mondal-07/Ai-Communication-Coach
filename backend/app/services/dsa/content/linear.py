"""Topics D (Linked Lists), E (Stacks) and F (Queues)."""

from __future__ import annotations

from .build import M, S, mk, mk_ref

_NODE = "class N:\n    def __init__(self, v, nxt=None):\n        self.v, self.nxt = v, nxt\n\n"
_WALK = "out, p = [], head\nwhile p:\n    out.append(p.v)\n    p = p.nxt\nprint(out)"


# --- D. Linked lists -------------------------------------------------------------------------------


def ll_intro():
    s = "ll-intro-memory"
    return [
        mk(s, "conceptual", "In the array representation of a linked list with parallel arrays INFO and LINK, what does a LINK value of 0 (NULL) in the last node mean?", "There is no next node; the list ends here",
           ["The node is free and available for reuse", "The node points back to the start of the list", "The node's INFO field is empty"], "NULL in the link field marks the end of the list.", d="easy", t=40, ver=M("Standard INFO/LINK representation: NULL terminates the list.")),
        mk(s, "conceptual", "What is the AVAIL list in the memory representation of linked lists?", "A list of free nodes from which new nodes are allocated",
           ["The list of nodes that were deleted from the user's data", "The header node of the main list", "An array that stores the sizes of all lists"], "Insertions take a node from AVAIL; deletions return a node to it.", d="easy", t=40, ver=M("AVAIL is the free-storage list in the dynamic-allocation model.")),
        mk(s, "scenario", "Why can a linked list grow without relocating existing data, unlike a fixed-size array?", "New nodes are allocated individually and linked in, so no contiguous block is needed",
           ["Linked lists use less memory per element than arrays", "Linked lists keep elements sorted automatically", "The operating system resizes them silently"], "Each node is allocated separately and reached through pointers.", d="easy", t=45, ver=M("Dynamic node allocation vs contiguous arrays.")),
        mk(s, "conceptual", "Trying to insert a node when the AVAIL list is empty is called:", "Overflow", ["Underflow", "Garbage collection", "Deadlock"], "No free node is available to allocate, so the insertion cannot proceed.", d="medium", t=35, ver=M("Overflow = no free node; underflow = delete from empty list.")),
        mk(s, "conceptual", "Compared with an array, what is a disadvantage of a singly linked list?", "Reaching the i-th element requires walking i links, O(i)",
           ["Insertion at the front takes O(n)", "It cannot store more than a fixed number of items", "Deletion always requires shifting elements"], "No direct addressing exists, and each node also stores a pointer.", d="medium", t=40, ver=M("Sequential access cost and pointer overhead.")),
    ]


def ll_traversal():
    s = "ll-traversal"
    return [
        mk(s, "output", "What does this code print?", "[1, 2, 3]", ["[3, 2, 1]", "[1, 2]", "[]"], "The loop follows nxt from the head, collecting values in list order.", d="easy", t=35,
           code=_NODE + "head = N(1, N(2, N(3)))\n" + _WALK, ver=S("[1, 2, 3]")),
        mk(s, "output", "What does this code print?", "3", ["2", "4", "None"], "count increments once for every node visited.", d="easy", t=35,
           code=_NODE + "head = N(7, N(8, N(9)))\ncount, p = 0, head\nwhile p:\n    count += 1\n    p = p.nxt\nprint(count)", ver=S("3")),
        mk(s, "complexity", "What is the time complexity of traversing a singly linked list of n nodes?", "O(n)", ["O(1)", "O(log n)", "O(n²)"], "Each node is visited exactly once.", d="easy", t=25,
           complexity={"time": "O(n)", "space": "O(1)"}, ver=M("Single pass over n nodes.")),
        mk(s, "conceptual", "In a singly linked list, how do you find the second-to-last node?", "Walk from the head until ptr.nxt.nxt is NULL",
           ["Follow the prev pointer of the last node", "Index it directly with n − 2", "Start at the tail and move one step back"], "A singly linked list has no backward pointers, so you must walk forward from the head.", d="medium", t=45, ver=M("Singly linked lists lack prev pointers.")),
        mk(s, "output", "What does this code print?", "9", ["7", "8", "None"], "The loop stops at the node whose nxt is None, i.e. the last one.", d="medium", t=40,
           code=_NODE + "head = N(7, N(8, N(9)))\np = head\nwhile p.nxt:\n    p = p.nxt\nprint(p.v)", ver=S("9")),
    ]


def ll_insert_delete():
    s = "ll-insert-delete"
    return [
        mk(s, "output", "What does this code print?", "[5, 1, 2]", ["[1, 2, 5]", "[1, 5, 2]", "[5, 1]"], "Inserting at the head makes the new node point to the old head and become the head.", d="easy", t=40,
           code=_NODE + "head = N(1, N(2))\nhead = N(5, head)\n" + _WALK, ver=S("[5, 1, 2]")),
        mk(s, "output", "What does this code print?", "[1, 9, 2, 3]", ["[1, 2, 9, 3]", "[9, 1, 2, 3]", "[1, 2, 3, 9]"], "The new node is linked in after the node with value 1: new.nxt = a.nxt; a.nxt = new.", d="medium", t=60,
           code=_NODE + "head = N(1, N(2, N(3)))\nnew = N(9)\nnew.nxt = head.nxt\nhead.nxt = new\n" + _WALK, ver=S("[1, 9, 2, 3]")),
        mk(s, "output", "What does this code print?", "[1, 3]", ["[2]", "[1, 2]", "[2, 3]"], "Skipping a node by setting head.nxt = head.nxt.nxt removes the value 2 from the list.", d="medium", t=45,
           code=_NODE + "head = N(1, N(2, N(3)))\nhead.nxt = head.nxt.nxt\n" + _WALK, ver=S("[1, 3]")),
        mk(s, "complexity", "What is the time complexity of deleting the node AFTER a given node whose pointer you already hold, in a singly linked list?", "O(1)", ["O(n)", "O(log n)", "O(n²)"], "Only one pointer needs to be updated.", d="medium", t=40,
           complexity={"time": "O(1)", "space": "O(1)"}, ver=M("Re-linking needs a constant number of pointer assignments.")),
        mk(s, "conceptual", "To delete a node N from a singly linked list when you only have a pointer to the node BEFORE it (P), which assignment is correct?", "P.nxt = N.nxt",
           ["N.nxt = P.nxt", "P = N.nxt", "N = P.nxt"], "Bypass N by linking P directly to what follows N.", d="easy", t=35, ver=M("Standard deletion by re-linking.")),
        mk(s, "scenario", "A task needs repeated insertions at the front of a collection of unknown size. Which gives O(1) per insertion without resizing?", "A singly linked list",
           ["An array with shifting", "A sorted array", "A binary search over an array"], "A new head node is created and linked in constant time.", d="easy", t=40, ver=M("Head insertion is O(1) on linked lists.")),
    ]


def ll_header():
    s = "ll-header"
    return [
        mk(s, "conceptual", "What distinguishes a GROUNDED header linked list?", "The last node's link field is NULL, so the list ends at a grounded pointer",
           ["The last node points back to the header node", "It has no header node", "Every node has a back pointer"], "A grounded header list is a header node followed by nodes, ending in NULL.", d="easy", t=40, ver=M("Grounded header list: NULL terminated; circular header list: last node points to the header.")),
        mk(s, "conceptual", "In a CIRCULAR header linked list, what does the link of the last node contain?", "The address of the header node", ["NULL", "The address of the first data node", "The address of the AVAIL list"],
           "Circular header lists point the last node to the header, so the list can be traversed from any node back around to the header.", d="easy", t=40, ver=M("Circular header list definition.")),
        mk(s, "conceptual", "How do you detect the end of traversal in a circular header list that starts at the header node's link?", "Stop when the pointer returns to the header node", ["Stop when the pointer is NULL", "Stop after exactly n steps counted by the header", "Stop when INFO becomes 0"],
           "There is no NULL; the pointer comes back to the header.", d="medium", t=45, ver=M("Circular lists have no NULL; the sentinel is the header.")),
        mk(s, "conceptual", "What is the main benefit of a header node?", "Insertion and deletion at the front need no special case, because every data node has a predecessor",
           ["It makes searching O(1)", "It stores all data values", "It removes the need for pointers"], "The header is always present, so head-of-list operations look like any other.", d="medium", t=50, ver=M("Header (sentinel) simplifies boundary cases.")),
        mk(s, "output", "A circular header list has header H and data nodes 4 → 6 → 8 → back to H. This loop starts at H.nxt and stops on returning to H. What does it print?", "[4, 6, 8]", ["[4, 6, 8, 4]", "[6, 8]", "[H, 4, 6, 8]"],
           "Only data nodes are visited; the header is the stop marker.", d="medium", t=50,
           code=_NODE + "h = N(None)\nc = N(8, h)\nb = N(6, c)\na = N(4, b)\nh.nxt = a\nout, p = [], h.nxt\nwhile p is not h:\n    out.append(p.v)\n    p = p.nxt\nprint(out)", ver=S("[4, 6, 8]")),
        mk(s, "scenario", "A round-robin scheduler must keep cycling through processes without special end-of-list handling. Which structure suits it?", "A circular linked list", ["A grounded list", "A sorted array", "A binary search tree"],
           "After the last process the pointer naturally returns to the first.", d="medium", t=45, ver=M("Circular lists model cyclic scheduling.")),
    ]


def ll_doubly():
    s = "ll-doubly"
    dnode = "class D:\n    def __init__(self, v):\n        self.v, self.prev, self.nxt = v, None, None\n\n"
    return [
        mk(s, "conceptual", "What does each node of a two-way (doubly) linked list contain?", "Data, a pointer to the previous node and a pointer to the next node", ["Data and a pointer to the next node only", "Data and the index of the node in an array", "Only two data fields"],
           "The extra back pointer allows traversal in both directions.", d="easy", t=30, ver=M("Doubly linked list node structure.")),
        mk(s, "conceptual", "What is the advantage of a doubly linked list over a singly linked list for deletion?", "A node can be deleted given only a pointer to it, in O(1)", ["Deletion needs no pointer updates", "It uses less memory per node", "It keeps the list sorted"],
           "The node knows its predecessor via prev, so no walk from the head is needed.", d="medium", t=50, ver=M("Doubly linked deletion of a known node is O(1).")),
        mk(s, "conceptual", "To insert a new node X immediately AFTER node A in a doubly linked list (B = A.next), which set of pointer updates is correct?", "X.prev = A; X.next = B; A.next = X; B.prev = X", ["A.next = X; B.prev = A", "X.next = A; A.prev = X", "X.prev = B; X.next = A"],
           "All four links around X must be set so both directions stay consistent.", d="medium", t=60, ver=M("Four-pointer update for doubly linked insertion.")),
        mk(s, "output", "What does this code print? (list is 1 ⇄ 2 ⇄ 3, traversed forward from head then backward from tail)", "[1, 2, 3] [3, 2, 1]", ["[1, 2, 3] [1, 2, 3]", "[3, 2, 1] [3, 2, 1]", "[1, 2, 3] [3, 2]"], "Forward uses next; backward uses prev.", d="medium", t=60,
           code=dnode + "a, b, c = D(1), D(2), D(3)\na.nxt, b.prev, b.nxt, c.prev = b, a, c, b\nf, p = [], a\nwhile p:\n    f.append(p.v)\n    p = p.nxt\nr, p = [], c\nwhile p:\n    r.append(p.v)\n    p = p.prev\nprint(f, r)", ver=S("[1, 2, 3] [3, 2, 1]")),
        mk(s, "complexity", "Compared with a singly linked list, the memory overhead of a doubly linked list per node is:", "One extra pointer", ["No extra memory", "n extra pointers", "A copy of the data"], "Each node adds a prev pointer.", d="easy", t=30, complexity={"time": "O(1) extra per node", "space": "one extra pointer per node, so O(n) extra overall"}, ver=M("Doubly linked node has two pointers instead of one.")),
        mk(s, "scenario", "An editor needs to move the cursor left and right through a line of characters and delete the character under the cursor. Which structure is the natural fit?", "A doubly linked list", ["A singly linked list", "A stack", "A min-heap"], "Moving both ways and deleting a known node are O(1) with prev/next pointers.", d="medium", t=50, ver=M("Bidirectional navigation with local edits.")),
    ]


# --- E. Stacks ---------------------------------------------------------------------------------------


def _ops_text(ops):
    return ", ".join(f"push({o[1]})" if o[0] == "push" else "pop()" for o in ops)


def stack_repr():
    s = "stack-representations"
    return [
        mk(s, "conceptual", "In an array-based stack with TOP initialised to -1, what is the condition for an empty stack?", "TOP == -1", ["TOP == 0", "TOP == MAXSIZE", "TOP == MAXSIZE − 1"], "TOP = -1 means no element has been pushed.", d="easy", t=30, ver=M("Convention: TOP=-1 initial; MAXSIZE-1 is full.")),
        mk(s, "conceptual", "In an array-based stack with TOP initialised to -1 and capacity MAXSIZE, the stack is full when:", "TOP == MAXSIZE − 1", ["TOP == MAXSIZE", "TOP == 0", "TOP == -1"], "The last valid index is MAXSIZE − 1.", d="easy", t=30, ver=M("Convention as above.")),
        mk(s, "conceptual", "Which end of a singly linked list is the best place to push and pop in a linked-list stack, and why?", "The head, because both operations are O(1) there",
           ["The tail, because insertion there is O(1)", "The middle, to balance the list", "Either end is O(n)"], "Head insertion and deletion need no traversal.", d="medium", t=50, ver=M("Singly linked list: head ops O(1); tail ops need traversal.")),
        mk(s, "scenario", "You need a stack whose maximum size is unknown and must never fail by running out of preallocated slots. Which implementation fits?", "A linked-list stack", ["A fixed-size array stack", "A sorted array", "A circular queue"], "A linked-list stack grows node by node (memory permitting).", d="easy", t=40, ver=M("Linked stacks have no preset capacity.")),
        mk(s, "conceptual", "Attempting to push onto a full array-based stack is called:", "Stack overflow", ["Stack underflow", "Stack traversal", "Stack inversion"], "Overflow = push on full; underflow = pop on empty.", d="easy", t=25, ver=M("Standard overflow/underflow terminology for bounded containers.")),
    ]


def stack_ops():
    s = "stack-operations"
    o1 = [["push", 1], ["push", 2], ["push", 3], ["pop"], ["push", 4], ["pop"], ["pop"]]
    o2 = [["push", 5], ["push", 6], ["pop"], ["push", 7], ["push", 8]]
    o3 = [["push", 2], ["pop"], ["pop"], ["push", 9]]
    return [
        mk_ref(s, "trace", f"A stack starts empty. Operations: {_ops_text(o1)}. What is the final content, bottom to top?", "stack_final", {"ops": o1}, ["[1, 2]", "[1, 2, 4]", "[1, 2, 3]"],
               "Pops remove 3, then 4, then 2, leaving only 1.", d="medium", t=70, trace=[{"label": "push(1), push(2), push(3)", "state": "[1, 2, 3]"}, {"label": "pop() → 3", "state": "[1, 2]"}, {"label": "push(4)", "state": "[1, 2, 4]"}, {"label": "pop() → 4", "state": "[1, 2]"}, {"label": "pop() → 2", "state": "[1]"}]),
        mk_ref(s, "trace", f"A stack starts empty. Operations: {_ops_text(o2)}. What is the final content, bottom to top?", "stack_final", {"ops": o2}, ["[5, 6, 7, 8]", "[5, 7, 8, 6]", "[6, 7, 8]"],
               "pop() removes 6; the remaining pushes add 7 and 8 on top of 5.", d="easy", t=55, trace=[{"label": "push(5), push(6)", "state": "[5, 6]"}, {"label": "pop() → 6", "state": "[5]"}, {"label": "push(7), push(8)", "state": "[5, 7, 8]"}]),
        mk_ref(s, "trace", f"A stack starts empty. Operations: {_ops_text(o3)}. What are the values returned by the pops, in order? (a pop on an empty stack reports 'underflow')", "stack_popped", {"ops": o3},
               ["[2]", "[2, 9]", "['underflow', 2]"], "The first pop returns 2; the second pop finds the stack empty.", d="medium", t=60,
               trace=[{"label": "push(2)", "state": "[2]"}, {"label": "pop() → 2", "state": "[]"}, {"label": "pop() → underflow", "state": "[]"}, {"label": "push(9)", "state": "[9]"}]),
        mk(s, "output", "What does this code print?", "olleh", ["hello", "hlloe", "ohell"], "Pushing characters then popping them reverses the string.", d="easy", t=35,
           code="st = []\nfor ch in 'hello':\n    st.append(ch)\nprint(''.join(st.pop() for _ in range(len(st))))", ver=S("olleh")),
        mk_ref(s, "scenario", "A compiler checks the bracket string '([)]'. Which verdict is correct using a stack?", "balanced", {"s": "([)]"}, ["Balanced", "Balanced but incorrectly ordered", "Unbalanced only because of the missing curly brace"],
               "When ')' arrives the top of the stack is '[', so the match fails.", d="medium", t=50),
        mk(s, "complexity", "What is the time complexity of push and pop on an array-based stack (ignoring resizing)?", "O(1) each", ["O(n) each", "O(log n) each", "O(n) for push, O(1) for pop"], "Both operate only at the top index.", d="easy", t=25,
           complexity={"time": "O(1)", "space": "O(1)"}, ver=M("Top-only operations.")),
    ]


def polish():
    s = "polish-notation"
    return [
        mk_ref(s, "conceptual", "Convert the infix expression  A + B * C  to postfix (reverse Polish) notation.", "postfix", {"expr": "A + B * C"}, ["A B + C *", "+ A * B C", "A B C + *"],
               "* has higher precedence, so B * C is grouped first: A (B C *) +.", d="easy", t=50),
        mk_ref(s, "conceptual", "Convert the infix expression  ( A + B ) * C  to prefix (Polish) notation.", "prefix", {"expr": "( A + B ) * C"}, ["+ A * B C", "A B + C *", "* A + B C"],
               "The parentheses force A + B first, then multiply by C: * (+ A B) C.", d="medium", t=55),
        mk(s, "conceptual", "What is a key advantage of Polish (prefix) and reverse Polish (postfix) notation?", "No parentheses or precedence rules are needed to evaluate them", ["They use fewer operators than infix", "They only work for addition", "They always produce shorter expressions"],
           "The position of each operator fixes the evaluation order.", d="easy", t=40, ver=M("Property of prefix/postfix notation.")),
        mk_ref(s, "conceptual", "Convert the infix expression  A - B - C  to postfix notation.", "postfix", {"expr": "A - B - C"}, ["A B C - -", "- - A B C", "A - B C -"],
               "Subtraction is left-associative: (A − B) − C becomes A B − C −.", d="medium", t=50),
        mk_ref(s, "conceptual", "Convert  A * ( B + C ) / D  to postfix notation.", "postfix", {"expr": "A * ( B + C ) / D"}, ["A B C * + D /", "A B + C * D /", "A B C + D / *"],
               "Evaluate B + C first, multiply by A, then divide by D (left to right for * and /).", d="hard", t=75),
        mk(s, "conceptual", "In which notation does the operator appear BEFORE its operands?", "Prefix (Polish)", ["Postfix (reverse Polish)", "Infix", "Both prefix and postfix"], "Prefix = operator first; postfix = operator last.", d="easy", t=25, ver=M("Definition of the term as used in standard data-structure texts.")),
    ]


def expr_eval():
    s = "expression-evaluation"
    return [
        mk_ref(s, "trace", "Evaluate the postfix expression  5 6 2 + * 12 4 / -", "eval_postfix", {"expr": "5 6 2 + * 12 4 / -"}, ["20", "40", "43"],
               "6 + 2 = 8; 5 × 8 = 40; 12 ÷ 4 = 3; 40 − 3 = 37.", d="medium", t=80,
               trace=[{"label": "push 5, 6, 2", "state": "[5, 6, 2]"}, {"label": "+", "state": "[5, 8]"}, {"label": "*", "state": "[40]"}, {"label": "push 12, 4", "state": "[40, 12, 4]"}, {"label": "/", "state": "[40, 3]"}, {"label": "-", "state": "[37]"}]),
        mk_ref(s, "trace", "Evaluate the postfix expression  2 3 1 * + 9 -", "eval_postfix", {"expr": "2 3 1 * + 9 -"}, ["-1", "0", "5"], "3 × 1 = 3; 2 + 3 = 5; 5 − 9 = −4.", d="easy", t=60,
               trace=[{"label": "push 2, 3, 1", "state": "[2, 3, 1]"}, {"label": "*", "state": "[2, 3]"}, {"label": "+", "state": "[5]"}, {"label": "push 9", "state": "[5, 9]"}, {"label": "-", "state": "[-4]"}]),
        mk_ref(s, "conceptual", "Evaluate the prefix expression  - * 2 3 4", "eval_prefix", {"expr": "- * 2 3 4"}, ["-2", "10", "6"], "2 × 3 = 6, then 6 − 4 = 2.", d="medium", t=70),
        mk_ref(s, "complexity", "What is the maximum stack depth reached while evaluating the postfix expression  4 5 6 * + 7 8 + *  ?", "postfix_max_depth", {"expr": "4 5 6 * + 7 8 + *"}, ["2", "4", "7"],
               "Pushing 4, 5, 6 gives depth 3; after * and + the stack holds one value, and pushing 7 and 8 reaches depth 3 again, so the peak is 3.", d="hard", t=90, complexity={"time": "O(n)", "space": "O(n) worst case; peak depth 3 here"}),
        mk(s, "scenario", "Why do calculators and compilers often convert infix to postfix before evaluating?", "Postfix can be evaluated in one left-to-right pass with a stack and no precedence rules",
           ["Postfix expressions are always shorter", "Infix cannot represent subtraction", "Postfix removes the need for operands"], "Precedence and parentheses are resolved during conversion.", d="medium", t=50, ver=M("Standard motivation.")),
    ]


def expr_conv():
    s = "expression-conversion"
    return [
        mk_ref(s, "trace", "Convert  ( A + B ) * ( C - D )  to postfix notation.", "postfix", {"expr": "( A + B ) * ( C - D )"}, ["A B C D - + *", "A B * C D - +", "A + B C - D *"],
               "Each parenthesised group becomes its own postfix subexpression; * comes last.", d="medium", t=75,
               trace=[{"label": "( A + B )", "state": "A B +"}, {"label": "( C - D )", "state": "C D -"}, {"label": "* joins both groups", "state": "A B + C D - *"}]),
        mk_ref(s, "trace", "Convert  A + B * C - D  to postfix notation.", "postfix", {"expr": "A + B * C - D"}, ["A B + C * D -", "A B C + * D -", "A B C * D - +"],
               "B * C is done first, then A + (B C *), then the subtraction: A B C * + D −.", d="medium", t=75,
               trace=[{"label": "A", "state": "output: A | stack: —"}, {"label": "+", "state": "output: A | stack: +"}, {"label": "B", "state": "output: A B | stack: +"}, {"label": "*", "state": "output: A B | stack: + *"}, {"label": "C", "state": "output: A B C | stack: + *"}, {"label": "- (pops * and +)", "state": "output: A B C * + | stack: -"}, {"label": "D", "state": "output: A B C * + D | stack: -"}, {"label": "end", "state": "output: A B C * + D -"}]),
        mk_ref(s, "conceptual", "Convert  A + B * C  to prefix notation.", "prefix", {"expr": "A + B * C"}, ["* + A B C", "A B C * +", "+ * A B C"], "B * C becomes * B C, then + A (* B C).", d="medium", t=60),
        mk(s, "conceptual", "In infix-to-postfix conversion using a stack, what happens when a closing parenthesis ')' is read?", "Operators are popped to the output until the matching '(' is found, which is discarded",
           ["Every operator on the stack is pushed again", "The conversion stops", "The '(' is written to the output"], "This completes the parenthesised subexpression.", d="easy", t=50, ver=M("Shunting-yard rule for ')'.")),
        mk(s, "conceptual", "In infix-to-postfix conversion, an incoming * meets + on top of the stack. What happens?", "* is pushed, because it has higher precedence than +", ["+ is popped to the output first", "Both are output at once", "Conversion fails"],
           "An operator only pops operators of equal or higher precedence.", d="easy", t=40, ver=M("Precedence rule.")),
        mk(s, "conceptual", "Which postfix expression is equivalent to the infix expression  A - ( B + C ) * D ?", "A B C + D * -", ["A B C D + * -", "A B - C + D *", "A B C + - D *"],
           "B + C first, times D, then subtract from A.", d="hard", t=70, ver=M("Hand derivation: A - ((B+C)*D) -> A [B C +] D * -.")),
    ]


# --- F. Queues ---------------------------------------------------------------------------------------


def _qops_text(ops):
    return ", ".join(f"enqueue({o[1]})" if o[0] == "enq" else "dequeue()" for o in ops)


def queue_repr():
    s = "queue-representations"
    return [
        mk(s, "conceptual", "What problem does a simple linear array queue suffer from after many enqueue and dequeue operations?", "Free slots at the front cannot be reused, so it appears full while space remains",
           ["It loses the order of elements", "It can only hold two elements", "Dequeue becomes impossible"], "REAR reaches the end even though earlier slots were freed; a circular queue fixes this.", d="medium", t=50, ver=M("Linear queue 'false full' problem.")),
        mk(s, "conceptual", "Which solution reuses the freed slots of an array queue?", "A circular queue where indices wrap around using modulo", ["Sorting the array after each dequeue", "Doubling the array every enqueue", "Using a stack instead"], "(rear + 1) % capacity wraps to the beginning.", d="easy", t=40, ver=M("Circular queue definition.")),
        mk(s, "conceptual", "In a linked-list queue, where are insertions and deletions performed for O(1) time with front and rear pointers?", "Insert at the rear, delete at the front", ["Insert at the front, delete at the rear", "Insert and delete at the front", "Insert and delete at the middle"], "A singly linked list can remove at the head and add at the tail in O(1) with a tail pointer.", d="medium", t=45, ver=M("Standard linked queue.")),
        mk(s, "scenario", "A producer thread adds tasks and a consumer thread removes them in the same order; the buffer has a fixed size. Which structure fits?", "A circular (ring) buffer queue", ["A stack", "A binary search tree", "A hash table"], "FIFO order with bounded memory and reuse of slots.", d="medium", t=50, ver=M("Ring buffer = circular queue.")),
        mk(s, "conceptual", "Attempting to dequeue from an empty queue is called:", "Queue underflow", ["Queue overflow", "Queue rotation", "Queue traversal"], "Underflow = remove from empty; overflow = insert into full.", d="easy", t=25, ver=M("Standard overflow/underflow terminology for bounded containers.")),
    ]


def queue_ops():
    s = "queue-operations"
    o1 = [["enq", 10], ["enq", 20], ["enq", 30], ["deq"], ["enq", 40], ["deq"]]
    o2 = [["enq", 1], ["enq", 2], ["enq", 3], ["enq", 4], ["enq", 5], ["deq"]]
    o3 = [["deq"], ["enq", 7], ["deq"], ["deq"]]
    o4 = [["enq", "A"], ["enq", "B"], ["enq", "C"], ["deq"], ["deq"], ["enq", "D"], ["enq", "E"]]
    return [
        mk_ref(s, "trace", f"An empty queue has operations: {_qops_text(o1)}. What is the queue, front to rear?", "cq_final", {"cap": 8, "ops": o1}, ["[10, 20, 30, 40]", "[40]", "[20, 30]"],
               "Dequeues remove 10 then 20, leaving 30 and the later 40.", d="easy", t=60, trace=[{"label": "enqueue 10, 20, 30", "state": "[10, 20, 30]"}, {"label": "dequeue → 10", "state": "[20, 30]"}, {"label": "enqueue 40", "state": "[20, 30, 40]"}, {"label": "dequeue → 20", "state": "[30, 40]"}]),
        mk_ref(s, "trace", f"A circular queue of capacity 4 starts empty. Operations: {_qops_text(o2)}. Enqueue on a full queue reports 'overflow'. What are the outputs of all operations that produce one?", "cq_outputs", {"cap": 4, "ops": o2},
               ["['overflow']", "[2]", "[1, 'overflow']"], "The 5th enqueue fails (queue holds 4); dequeue then returns 1.", d="medium", t=75,
               trace=[{"label": "enqueue 1..4", "state": "[1, 2, 3, 4] (full)"}, {"label": "enqueue 5", "state": "overflow"}, {"label": "dequeue", "state": "returns 1 → [2, 3, 4]"}]),
        mk_ref(s, "trace", f"An empty queue has operations: {_qops_text(o3)}. What are the outputs of the dequeues? (empty dequeue reports 'underflow')", "cq_outputs", {"cap": 4, "ops": o3},
               ["[7, 7, 'underflow']", "[7, 'underflow']", "['underflow', 7]"], "The first dequeue sees an empty queue; after enqueue(7) one dequeue returns 7 and the next underflows.", d="medium", t=65,
               trace=[{"label": "dequeue", "state": "underflow"}, {"label": "enqueue 7", "state": "[7]"}, {"label": "dequeue", "state": "returns 7 → []"}, {"label": "dequeue", "state": "underflow"}]),
        mk_ref(s, "trace", f"A circular queue of capacity 4 starts empty (slots 0–3). Operations: {_qops_text(o4)}. What do the slots hold, listed by slot index 0..3 ('-' = empty)?", "cq_slots", {"cap": 4, "ops": o4},
               ["[A, B, C, D]", "[-, -, C, D]", "[D, E, C, -]"], "A, B go to slots 0,1 and C to slot 2; two dequeues free 0,1; D goes to slot 3 and E wraps to slot 0.", d="hard", t=100,
               trace=[{"label": "enqueue A, B, C", "state": "[A, B, C, -]"}, {"label": "dequeue ×2", "state": "[-, -, C, -]"}, {"label": "enqueue D", "state": "[-, -, C, D]"}, {"label": "enqueue E (wraps)", "state": "[E, -, C, D]"}]),
        mk(s, "complexity", "What is the time complexity of enqueue and dequeue on a circular array queue?", "O(1) each", ["O(n) each", "O(log n) each", "O(n) for dequeue only"], "Only index arithmetic is needed.", d="easy", t=25, complexity={"time": "O(1)", "space": "O(1)"}, ver=M("Index updates are constant-time.")),
        mk(s, "output", "What does this code print?", "[3, 4]", ["[1, 2]", "[1, 2, 3, 4]", "[2, 3, 4]"], "Two items are dequeued from the front; 3 and 4 remain.", d="easy", t=40,
           code="from collections import deque\nq = deque([1, 2, 3, 4])\nq.popleft()\nq.popleft()\nprint(list(q))", ver=S("[3, 4]")),
    ]


def priority():
    s = "priority-queues"
    items = [[3, "print"], [1, "alarm"], [2, "email"], [1, "backup"]]
    items2 = [[5, "t1"], [2, "t2"], [9, "t3"], [2, "t4"], [1, "t5"]]
    return [
        mk_ref(s, "trace", "A priority queue serves the LOWEST number first (ties served in arrival order). Jobs arrive as (priority, name): (3, print), (1, alarm), (2, email), (1, backup). In what order are they served?", "pq_order", {"items": items},
               ["['print', 'alarm', 'email', 'backup']", "['alarm', 'email', 'backup', 'print']", "['backup', 'alarm', 'email', 'print']"], "Both priority-1 jobs go first (alarm arrived before backup), then email, then print.", d="medium", t=70,
               trace=[{"label": "priority 1 (arrival order)", "state": "alarm, backup"}, {"label": "priority 2", "state": "email"}, {"label": "priority 3", "state": "print"}]),
        mk_ref(s, "trace", "A priority queue serves the lowest number first (ties in arrival order). Jobs: (5, t1), (2, t2), (9, t3), (2, t4), (1, t5). What is the service order?", "pq_order", {"items": items2},
               ["['t5', 't4', 't2', 't1', 't3']", "['t1', 't2', 't3', 't4', 't5']", "['t5', 't2', 't1', 't4', 't3']"], "Sorted by priority, ties by arrival: t5, t2, t4, t1, t3.", d="medium", t=75,
               trace=[{"label": "priority 1", "state": "t5"}, {"label": "priority 2 (arrival order)", "state": "t2, t4"}, {"label": "priority 5", "state": "t1"}, {"label": "priority 9", "state": "t3"}]),
        mk(s, "conceptual", "Which data structure is the most efficient common implementation of a priority queue?", "A binary heap", ["An unsorted array", "A sorted linked list", "A stack"], "A heap gives O(log n) insertion and removal of the highest-priority element.", d="easy", t=35, ver=M("Binary heap implements PQ in O(log n).")),
        mk(s, "complexity", "In a priority queue backed by an UNSORTED array, what is the cost of removing the highest-priority element?", "O(n)", ["O(1)", "O(log n)", "O(n log n)"], "The whole array must be scanned to find the best element.", d="medium", t=45, complexity={"time": "O(n) delete-min; O(1) insert", "space": "O(n)"}, ver=M("Unsorted array: scan for min.")),
        mk(s, "scenario", "An operating system must always run the most urgent ready task next, with tasks arriving continuously. Which abstract structure matches this?", "Priority queue", ["Plain FIFO queue", "Stack", "Deque"], "Selection depends on urgency, not arrival order.", d="easy", t=40, ver=M("Scheduling by priority.")),
        mk(s, "scenario", "A low-priority job keeps being overtaken by newly arriving high-priority jobs and never runs. What is this problem called, and a common remedy?", "Starvation; gradually raise the priority of waiting jobs (aging)", ["Overflow; double the queue capacity", "Underflow; add dummy jobs", "Thrashing; sort by name"], "Aging prevents indefinite postponement.", d="hard", t=60, ver=M("OS scheduling concept: starvation and aging.")),
    ]


def deque_q():
    s = "deques"
    o1 = [["pb", 1], ["pb", 2], ["pf", 0], ["eb"], ["ef"]]
    o2 = [["pf", "x"], ["pf", "y"], ["pb", "z"], ["ef"], ["eb"]]
    o3 = [["pb", 4], ["ef"], ["ef"], ["pf", 8]]

    def txt(ops):
        names = {"pf": "push_front", "pb": "push_back", "ef": "pop_front", "eb": "pop_back"}
        return ", ".join(f"{names[o[0]]}({o[1]})" if len(o) > 1 else f"{names[o[0]]}()" for o in ops)

    return [
        mk_ref(s, "trace", f"A deque starts empty. Operations: {txt(o1)}. What does the deque hold, front to back?", "deque_final", {"ops": o1}, ["[0, 1]", "[2]", "[0, 1, 2]"],
               "After the three pushes it is [0, 1, 2]; pop_back removes 2 and pop_front removes 0, leaving [1].", d="medium", t=65,
               trace=[{"label": "push_back(1), push_back(2)", "state": "[1, 2]"}, {"label": "push_front(0)", "state": "[0, 1, 2]"}, {"label": "pop_back() → 2", "state": "[0, 1]"}, {"label": "pop_front() → 0", "state": "[1]"}]),
        mk_ref(s, "trace", f"A deque starts empty. Operations: {txt(o2)}. What values do the two pops return, in order?", "deque_popped", {"ops": o2}, ["['x', 'z']", "['z', 'x']", "['x', 'y']"],
               "After the pushes the deque is [y, x, z]; pop_front returns y, pop_back returns z.", d="medium", t=65,
               trace=[{"label": "push_front(x), push_front(y)", "state": "[y, x]"}, {"label": "push_back(z)", "state": "[y, x, z]"}, {"label": "pop_front() → y", "state": "[x, z]"}, {"label": "pop_back() → z", "state": "[x]"}]),
        mk_ref(s, "trace", f"A deque starts empty. Operations: {txt(o3)}. What are the results of the pops? (empty pop reports 'empty')", "deque_popped", {"ops": o3}, ["[4]", "['empty', 4]", "[4, 4]"],
               "The first pop_front returns 4; the second finds the deque empty.", d="easy", t=55,
               trace=[{"label": "push_back(4)", "state": "[4]"}, {"label": "pop_front() → 4", "state": "[]"}, {"label": "pop_front() → empty", "state": "[]"}, {"label": "push_front(8)", "state": "[8]"}]),
        mk(s, "conceptual", "Which statement describes a deque?", "A double-ended queue that allows insertion and deletion at both ends", ["A queue that is always sorted", "A queue limited to deletion at the front only", "A stack with a size limit"],
           "A deque generalises both stack and queue.", d="easy", t=30, ver=M("Definition of the deque abstract data type.")),
        mk(s, "scenario", "A sliding-window maximum algorithm needs to add and remove candidates at both ends in O(1). Which structure does it use?", "A deque", ["A binary heap", "A stack", "A singly linked list"], "Old indices are removed from the front and dominated values from the back.", d="hard", t=60, ver=M("Classic monotonic-deque technique.")),
        mk(s, "conceptual", "An input-restricted deque allows insertion at ONE end only. Deletion is allowed:", "At both ends", ["At one end only", "Nowhere", "Only in the middle"], "Input-restricted limits insertions; output-restricted limits deletions.", d="medium", t=40, ver=M("Standard textbook deque variants.")),
    ]


def all_questions():
    out = []
    for f in (ll_intro, ll_traversal, ll_insert_delete, ll_header, ll_doubly, stack_repr, stack_ops, polish, expr_eval, expr_conv, queue_repr, queue_ops, priority, deque_q):
        out.extend(f())
    return out
