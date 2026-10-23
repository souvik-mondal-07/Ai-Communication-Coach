"""Topic G (Trees) and the first two subtopics of Topic H (Recursion)."""

from __future__ import annotations

from app.services.dsa import algos as A
from app.services.dsa.references import _s

from .build import M, S, mk, mk_ref

K1 = [50, 30, 70, 20, 40, 60, 80]
K2 = [8, 3, 10, 1, 6, 14, 4, 7, 13]
K3 = [15, 10, 20, 8, 12, 17, 25]
K4 = [45, 15, 79, 90, 10, 55, 12, 20, 50]
K5 = [10, 20, 30, 40]
K6 = [40, 20, 60, 10, 30, 50, 70, 25, 35]


def _visit_trace(order, verb):
    """Progressive trace: after each step, what has been collected so far."""
    return [{"label": f"{verb} {k}", "state": _s(order[: i + 1])} for i, k in enumerate(order)]


def _bst_code(keys, tail):
    return ("class T:\n    def __init__(self, k):\n        self.k, self.l, self.r = k, None, None\n\n"
            "def ins(n, k):\n    if n is None:\n        return T(k)\n    if k < n.k:\n        n.l = ins(n.l, k)\n    else:\n        n.r = ins(n.r, k)\n    return n\n\n"
            f"root = None\nfor k in {keys}:\n    root = ins(root, k)\n" + tail)


def _delete_pred(keys, key):
    """Distractor: delete using the inorder PREDECESSOR instead of the successor."""
    root = A.build_bst(keys)

    def rec(n, k):
        if n is None:
            return None
        if k < n.key:
            n.left = rec(n.left, k)
        elif k > n.key:
            n.right = rec(n.right, k)
        else:
            if n.left is None:
                return n.right
            if n.right is None:
                return n.left
            p = n.left
            while p.right:
                p = p.right
            n.key = p.key
            n.left = rec(n.left, p.key)
        return n

    return rec(root, key)


def binary_trees():
    s = "binary-trees"
    return [
        mk(s, "conceptual", "In a binary tree, what is the maximum number of nodes at level L (root at level 0)?", "2^L", ["L²", "2L", "2^(L+1)"], "Each node has at most two children, so each level can at most double.", d="easy", t=35, ver=M("Level L holds at most 2^L nodes when the root is level 0.")),
        mk_ref(s, "conceptual", "What is the maximum total number of nodes in a binary tree of height 3 (a single node has height 0)?", "max_nodes_height", {"h": 3}, ["8", "16", "9"],
               "1 + 2 + 4 + 8 = 2^(3+1) − 1.", d="medium", t=45),
        mk(s, "conceptual", "In a non-empty binary tree, how many leaves does it have if it has 5 nodes with exactly two children?", "6", ["5", "4", "10"], "Leaves = (nodes with two children) + 1.", d="hard", t=60, ver=M("Identity n0 = n2 + 1 for binary trees.")),
        mk(s, "conceptual", "What is the term for a node with no children?", "Leaf (external node)", ["Root", "Sibling", "Ancestor"], "Leaves have degree zero.", d="easy", t=20, ver=M("Basic tree terminology from textbooks.")),
        mk(s, "scenario", "A tree where every node has only a right child behaves like which structure, and what is its height for n nodes?", "A linked list, with height n − 1", ["A balanced tree, with height log n", "A heap, with height n/2", "A hash table, with height 1"],
           "A skewed tree degenerates to a chain, which makes operations O(n).", d="medium", t=50, ver=M("Skewed binary tree has height n-1 with edge counting.")),
        mk_ref(s, "conceptual", "How many nodes can a binary tree have at level 5 at most (root at level 0)?", "max_nodes_level", {"level": 5}, ["10", "25", "64"], "2^5.", d="easy", t=30),
    ]


def complete_extended():
    s = "complete-extended-trees"
    return [
        mk(s, "conceptual", "Which description fits a COMPLETE binary tree?", "Every level except possibly the last is full, and the last level is filled from the left", ["Every node has exactly two children or none", "All leaves are at the same depth and no node has one child", "Each node's key is larger than its children's"],
           "That shape lets the tree be stored in an array with no gaps.", d="easy", t=40, ver=M("Definition of a complete binary tree.")),
        mk_ref(s, "conceptual", "An extended (2-tree) binary tree is formed by adding external nodes so every internal node has two children. If a binary tree has 6 internal nodes, how many external nodes does the extended tree have?", "extended_external", {"internal": 6},
               ["5", "6", "12"], "External nodes = internal nodes + 1.", d="medium", t=55),
        mk_ref(s, "conceptual", "An extended binary tree has 9 internal nodes. What is the total number of nodes (internal + external)?", "extended_total", {"internal": 9}, ["18", "20", "10"], "9 internal + 10 external.", d="medium", t=55),
        mk(s, "conceptual", "What is the height of a complete binary tree with 15 nodes? (single node = height 0)", "3", ["4", "2", "15"], "Levels hold 1, 2, 4, 8 nodes: 15 nodes fill levels 0–3.", d="medium", t=45, ver=M("floor(log2(15)) = 3.")),
        mk(s, "conceptual", "In an extended binary tree, what do the external nodes represent?", "Empty subtrees (null links) of the original tree", ["Duplicate keys", "The root of each subtree", "Nodes with two children"], "Each missing child of the original tree becomes an external node.", d="easy", t=40, ver=M("Standard definition of extended binary tree.")),
        mk(s, "conceptual", "Is a full binary tree (every node has 0 or 2 children) always complete?", "No — a full tree can have its last level not filled from the left", ["Yes, always", "Only when its height is odd", "Only when it has an even number of nodes"],
           "Full and complete are different properties; a full tree can place leaves at different depths.", d="hard", t=60, ver=M("Counter-example: full tree whose left subtree is a single leaf and right subtree has children.")),
    ]


def tree_repr():
    s = "tree-representations"
    return [
        mk_ref(s, "conceptual", "In a sequential (array) representation of a binary tree with the root at index 0, where are the children of the node at index 4?", "heap_children", {"i": 4},
               ["4 and 5", "5 and 6", "8 and 9"], "Left child 2i + 1, right child 2i + 2.", d="easy", t=40),
        mk_ref(s, "conceptual", "In a zero-based array representation of a binary tree, what is the index of the parent of the node at index 9?", "heap_parent", {"i": 9}, ["3", "5", "9"], "Parent = ⌊(i − 1) / 2⌋.", d="easy", t=40),
        mk(s, "conceptual", "With ONE-based indexing, the children of the node at index i are stored at:", "2i and 2i + 1", ["i + 1 and i + 2", "2i + 1 and 2i + 2", "i/2 and i/2 + 1"], "Left child 2i, right child 2i + 1; the parent is ⌊i/2⌋.", d="easy", t=35, ver=M("Standard one-based heap indexing.")),
        mk_ref(s, "conceptual", "What is the minimum array size needed to store ANY binary tree of height 4 sequentially (root at index 0)?", "complete_array_size", {"h": 4}, ["16", "15", "30"], "A tree of height h can use indices up to 2^(h+1) − 2 when it is a full tree, so 2^(h+1) − 1 slots.", d="medium", t=55),
        mk(s, "scenario", "A tree is very skewed (each node has only one child). Why is sequential array storage a poor choice?", "Most array slots stay empty, so memory use is exponential in the height", ["Array indexing becomes O(n)", "Nodes lose their data", "The tree cannot be traversed"],
           "Sparse trees waste many positions, which is why linked representation is preferred.", d="medium", t=55, ver=M("Sequential storage allocates 2^(h+1)-1 slots regardless of node count.")),
        mk(s, "conceptual", "In the linked representation of a binary tree, each node typically stores:", "Data, a left-child pointer and a right-child pointer", ["Data and the index of the parent", "Only data", "A sorted list of its descendants"], "Pointers let the tree take any shape without wasting space.", d="easy", t=30, ver=M("Linked binary tree node structure.")),
    ]


def bst_search():
    s = "bst-search"
    return [
        mk(s, "conceptual", "Which property defines a binary search tree?", "For every node, keys in the left subtree are smaller and keys in the right subtree are larger", ["Every node is larger than both children", "The tree is complete", "All leaves have the same depth"],
           "This ordering lets a search discard one subtree at each step.", d="easy", t=35, ver=M("BST ordering property.")),
        mk_ref(s, "trace", f"Keys are inserted into an empty BST in this order: {K1}. Which nodes are visited, in order, when searching for 60?", "bst_search_path", {"keys": K1, "key": 60},
               ["50, 30, 60", "50, 60", "50, 70, 80, 60"], "At 50 go right (60 > 50), at 70 go left (60 < 70), then find 60.", d="easy", t=55,
               trace=[{"label": "compare with 50", "state": "60 > 50 → go right"}, {"label": "compare with 70", "state": "60 < 70 → go left"}, {"label": "compare with 60", "state": "found"}]),
        mk_ref(s, "trace", f"Keys are inserted into an empty BST in this order: {K2}. Which nodes are visited when searching for 7?", "bst_search_path", {"keys": K2, "key": 7},
               ["8, 3, 6, 4, 7", "8, 10, 14, 7", "8, 3, 7"], "7 < 8 → left; 7 > 3 → right to 6; 7 > 6 → right to 7.", d="medium", t=65,
               trace=[{"label": "compare with 8", "state": "7 < 8 → go left"}, {"label": "compare with 3", "state": "7 > 3 → go right"}, {"label": "compare with 6", "state": "7 > 6 → go right"}, {"label": "compare with 7", "state": "found"}]),
        mk(s, "conceptual", "Where is the minimum key in a BST?", "At the leftmost node", ["At the root", "At the rightmost node", "At the deepest leaf"], "Keep following left links until none remain.", d="easy", t=30, ver=M("BST minimum is the leftmost node.")),
        mk(s, "complexity", "What is the worst-case time complexity of searching a BST with n nodes (no balancing)?", "O(n)", ["O(log n)", "O(1)", "O(n log n)"], "Inserting sorted keys produces a chain, so a search may visit every node.", d="medium", t=40,
           complexity={"time": "O(n) worst case, O(log n) when balanced", "best": "O(1)", "average": "O(log n) for random insertions", "worst": "O(n)", "space": "O(1) iterative"}, ver=M("Unbalanced BST degenerates to a list.")),
        mk_ref(s, "complexity", f"Keys {K5} are inserted in this order into an empty BST. What is the height of the tree (single node = 0)?", "bst_height", {"keys": K5}, ["1", "2", "4"],
               "Each key is larger than the previous, so each goes to the right of the last: a chain of height 3.", d="medium", t=50, complexity={"time": "O(n) search", "space": "O(n)"}),
        mk(s, "conceptual", "Which traversal of a BST visits the keys in sorted ascending order?", "Inorder", ["Preorder", "Postorder", "Level order"], "Left, node, right yields ascending keys.", d="easy", t=25, ver=M("Inorder traversal of a BST is sorted.")),
    ]


def bst_insert_delete():
    s = "bst-insert-delete"
    return [
        mk_ref(s, "trace", f"Keys are inserted into an empty BST in this order: {K1}. What is the PREORDER traversal?", "bst_preorder", {"keys": K1},
               [_s(A.inorder(A.build_bst(K1))), _s(A.postorder(A.build_bst(K1))), _s(K1[::-1])], "The first key is the root; 30 and 70 become its children, with 20/40 under 30 and 60/80 under 70.", d="easy", t=60,
               trace=_visit_trace(A.preorder(A.build_bst(K1)), "visit")),
        mk_ref(s, "trace", f"Keys are inserted into an empty BST in this order: {K4}. What is the height of the tree (single node = 0)?", "bst_height", {"keys": K4}, ["2", "4", "5"],
               "One longest path is 45 → 15 → 10 → 12, with three edges.", d="hard", t=85,
               trace=_visit_trace([45, 15, 10, 12], "descend")),
        mk_ref(s, "trace", f"The BST built from {K2} (in that insertion order) has the node 3 deleted. 3 has two children, so it is replaced by its inorder SUCCESSOR. What is the PREORDER traversal afterwards?", "bst_delete_preorder", {"keys": K2, "key": 3},
               [_s(A.preorder(_delete_pred(K2, 3))), _s(A.preorder(A.build_bst(K2))), _s([8, 6, 1, 4, 7, 10, 14, 13])], "The successor of 3 is 4 (leftmost node of its right subtree); 4 replaces 3 and is removed from its old place.", d="hard", t=100,
               trace=[{"label": "locate 3", "state": "two children: 1 and 6"}, {"label": "find successor", "state": "right subtree 6 → leftmost is 4"}, {"label": "replace 3 with 4, delete old 4", "state": "preorder shown in the answer"}]),
        mk_ref(s, "trace", f"In the BST built from {K1} (insertion order), the root 50 is deleted using the inorder successor. Which key becomes the new root?", "bst_root_after_delete", {"keys": K1, "key": 50}, ["40", "70", "30"],
               "The successor is the smallest key in the right subtree: 60.", d="medium", t=65,
               trace=[{"label": "find successor", "state": "go right to 70, then left to 60"}, {"label": "copy 60 into the root", "state": "root = 60"}, {"label": "remove old 60 node (leaf)", "state": "right subtree: 70 with children (none, 80)"}]),
        mk_ref(s, "trace", f"Delete the leaf 80 from the BST built from {K1}. What is its INORDER traversal afterwards?", "bst_delete_inorder", {"keys": K1, "key": 80},
               [_s(A.inorder(A.build_bst(K1))), _s([20, 30, 40, 60, 70]), _s([20, 30, 40, 50, 60, 80])], "Deleting a leaf only removes it; the remaining keys stay sorted.", d="easy", t=50,
               trace=[{"label": "locate 80", "state": "50 → 70 → 80 (a leaf)"}, {"label": "unlink the leaf", "state": "70 now has only a left child"}]),
        mk(s, "conceptual", "A node to be deleted from a BST has exactly ONE child. What is the correct action?", "Replace the node with its single child", ["Replace it with its inorder predecessor and delete that", "Delete the whole subtree", "Rebuild the tree from scratch"], "The child subtree takes the deleted node's place; ordering is preserved.", d="easy", t=40, ver=M("Standard BST deletion case 2.")),
        mk(s, "complexity", "What is the average-case time to insert into a BST built from randomly ordered keys?", "O(log n)", ["O(1)", "O(n)", "O(n log n)"], "Random insertion produces a tree of expected height O(log n).", d="medium", t=40,
           complexity={"time": "O(log n) average, O(n) worst case", "space": "O(1) iterative"}, ver=M("Expected height of a random BST is O(log n).")),
    ]


def traversals():
    s = "tree-traversals"
    t1 = A.build_bst(K1)
    return [
        mk_ref(s, "trace", f"The BST built from {K3} (insertion order) is traversed. What is the INORDER sequence?", "bst_inorder", {"keys": K3}, [_s(K3), _s(A.postorder(A.build_bst(K3))), _s(A.preorder(A.build_bst(K3)))],
               "Left–node–right visits keys in ascending order for any BST.", d="easy", t=45, trace=_visit_trace(sorted(K3), "visit")),
        mk_ref(s, "trace", f"The BST built from {K3} (insertion order) is traversed. What is the POSTORDER sequence?", "bst_postorder", {"keys": K3}, [_s(sorted(K3)), _s(A.preorder(A.build_bst(K3))), _s(A.preorder(A.build_bst(K3))[::-1])],
               "Left, right, then the node: leaves come out first, the root last.", d="medium", t=60, trace=_visit_trace(A.postorder(A.build_bst(K3)), "visit")),
        mk_ref(s, "trace", f"The BST built from {K6} (insertion order) is traversed. What is the PREORDER sequence?", "bst_preorder", {"keys": K6}, [_s(sorted(K6)), _s(A.postorder(A.build_bst(K6))), _s(K6[::-1])],
               "Node, left, right: the root comes first, then the entire left subtree, then the right subtree.", d="medium", t=70, trace=_visit_trace(A.preorder(A.build_bst(K6)), "visit")),
        mk_ref(s, "trace", f"The BST built from {K1} (insertion order) is traversed LEVEL BY LEVEL. What is the sequence?", "bst_levelorder", {"keys": K1}, [_s(sorted(K1)), _s(A.preorder(t1)), _s(A.postorder(t1))],
               "Level order uses a queue: 50; 30, 70; 20, 40, 60, 80.", d="easy", t=45, trace=_visit_trace(A.level_order(t1), "visit")),
        mk_ref(s, "trace", "A binary tree has INORDER sequence [4, 2, 5, 1, 3] and PREORDER sequence [1, 2, 4, 5, 3]. What is its POSTORDER sequence?", "postorder_from_in_pre", {"inorder": [4, 2, 5, 1, 3], "preorder": [1, 2, 4, 5, 3]},
               ["[4, 2, 5, 3, 1]", "[5, 4, 2, 3, 1]", "[1, 2, 4, 5, 3]"], "Root 1 splits inorder into [4,2,5] | [3]; recursively 2 is the root of the left part with children 4 and 5.", d="hard", t=110,
               trace=[{"label": "preorder root = 1", "state": "left inorder [4, 2, 5], right inorder [3]"}, {"label": "left subtree root = 2", "state": "children 4 (left), 5 (right)"}, {"label": "right subtree", "state": "single node 3"}, {"label": "postorder = left, right, root", "state": "[4, 5, 2, 3, 1]"}]),
        mk(s, "output", "What does this recursive traversal print?", "4 2 5 1 3", ["1 2 4 5 3", "4 5 2 3 1", "1 2 3 4 5"], "print occurs between the two recursive calls, so it is an inorder traversal.", d="medium", t=60,
           code="class T:\n    def __init__(self, v, l=None, r=None):\n        self.v, self.l, self.r = v, l, r\n\ndef f(n):\n    if n:\n        f(n.l)\n        print(n.v, end=' ')\n        f(n.r)\n\nf(T(1, T(2, T(4), T(5)), T(3)))", ver=S("4 2 5 1 3 ")),
        mk(s, "output", "What does this recursive traversal print?", "4 5 2 3 1", ["1 2 4 5 3", "4 2 5 1 3", "2 4 5 3 1"], "print occurs after both recursive calls: postorder.", d="medium", t=60,
           code="class T:\n    def __init__(self, v, l=None, r=None):\n        self.v, self.l, self.r = v, l, r\n\ndef f(n):\n    if n:\n        f(n.l)\n        f(n.r)\n        print(n.v, end=' ')\n\nf(T(1, T(2, T(4), T(5)), T(3)))", ver=S("4 5 2 3 1 ")),
        mk(s, "complexity", "What are the time and auxiliary space complexities of a recursive inorder traversal of a binary tree with n nodes and height h?", "Time O(n); space O(h) for the recursion stack", ["Time O(log n); space O(1)", "Time O(n²); space O(n)", "Time O(n); space O(1) always"],
           "Every node is visited once; the call stack grows to the tree's height.", d="medium", t=55, complexity={"time": "O(n)", "space": "O(h): O(log n) balanced, O(n) skewed"}, ver=M("Recursive DFS traversal cost.")),
    ]


# --- H. recursion (intro + Tower of Hanoi) ----------------------------------------------------------------


def recursion_intro():
    s = "recursion-intro"
    return [
        mk(s, "conceptual", "Which two parts must every correct recursive function have?", "A base case and a recursive case that moves toward the base case", ["A loop and a counter", "A global variable and a return value", "Two parameters and two return statements"],
           "Without a base case the recursion never ends; without progress it never reaches it.", d="easy", t=35, ver=M("Fundamental recursion requirements.")),
        mk(s, "output", "What does this code print?", "120", ["24", "720", "5"], "fact(5) = 5 × 4 × 3 × 2 × 1.", d="easy", t=35,
           code="def fact(n):\n    return 1 if n <= 1 else n * fact(n - 1)\n\nprint(fact(5))", ver=S("120")),
        mk(s, "output", "What does this code print?", "[3, 2, 1]", ["[1, 2, 3]", "[3, 2, 1, 0]", "[1, 2, 3, 0]"], "The append happens BEFORE the recursive call, so the values are appended in the order 3, 2, 1.", d="hard", t=70,
           code="def f(n, out):\n    if n == 0:\n        return out\n    out.append(n)\n    return f(n - 1, out)\n\nprint(f(3, []))", ver=S("[3, 2, 1]")),
        mk(s, "output", "What does this code print?", "[1, 2, 3]", ["[3, 2, 1]", "[0, 1, 2, 3]", "[1, 2, 3, 0]"], "Appending AFTER the recursive call returns means the smallest n is appended first.", d="hard", t=75,
           code="def f(n, out):\n    if n == 0:\n        return out\n    f(n - 1, out)\n    out.append(n)\n    return out\n\nprint(f(3, []))", ver=S("[1, 2, 3]")),
        mk(s, "conceptual", "What happens if a recursive function has no reachable base case?", "The call stack keeps growing until a stack overflow (RecursionError in Python)", ["It returns 0 automatically", "It runs once and stops", "The compiler rewrites it as a loop"], "Each call adds a stack frame that is never released.", d="easy", t=35, ver=M("Unbounded recursion exhausts the call stack.")),
        mk_ref(s, "complexity", "The naive recursive Fibonacci (fib(n) = fib(n−1) + fib(n−2), fib(0)=0, fib(1)=1) is called as fib(5). How many function calls are made in total, counting the first?", "fib_calls", {"n": 5}, ["5", "9", "25"],
               "Calls(n) = 1 + Calls(n−1) + Calls(n−2): 1, 1, 3, 5, 9, 15.", d="hard", t=90, complexity={"time": "O(2ⁿ)", "space": "O(n) recursion depth"}),
        mk(s, "complexity", "What is the auxiliary space of a recursive function that makes one recursive call per level and recurses n deep?", "O(n)", ["O(1)", "O(log n)", "O(n²)"], "Each pending call keeps a stack frame.", d="medium", t=40, complexity={"time": "depends on work per call", "space": "O(n) stack"}, ver=M("Call stack depth n.")),
    ]


def hanoi():
    s = "tower-of-hanoi"
    return [
        mk_ref(s, "conceptual", "What is the minimum number of moves needed to solve the Tower of Hanoi with 4 disks?", "hanoi_count", {"n": 4}, ["8", "16", "31"], "The recurrence T(n) = 2T(n−1) + 1 gives 2ⁿ − 1.", d="easy", t=40),
        mk_ref(s, "conceptual", "How many moves are needed for 6 disks?", "hanoi_count", {"n": 6}, ["36", "64", "127"], "2⁶ − 1.", d="easy", t=35),
        mk_ref(s, "trace", "Disks 1 (smallest), 2, 3 start on peg A and must reach peg C using B. What is the SECOND move?", "hanoi_move", {"n": 3, "k": 2}, ["disk 1 from A to C", "disk 3 from A to C", "disk 2 from B to C"],
               "The sequence begins: disk 1 A→C, disk 2 A→B, disk 1 C→B, then disk 3 A→C.", d="medium", t=65,
               trace=[{"label": f"move {i + 1}", "state": f"disk {d} from {a} to {c}"} for i, (d, a, c) in enumerate(A.hanoi_moves(3))]),
        mk_ref(s, "trace", "Two disks must move from A to C using B. Which sequence of (from→to) moves is correct?", "hanoi_sequence", {"n": 2}, ["A→C, A→B, B→C", "A→C, B→C, A→B", "A→B, B→C, A→C"],
               "Park the small disk on B, move the big disk to C, then bring the small disk onto it.", d="easy", t=55,
               trace=[{"label": f"move {i + 1}", "state": f"disk {d} from {a} to {c}"} for i, (d, a, c) in enumerate(A.hanoi_moves(2))]),
        mk(s, "complexity", "What is the time complexity of the standard recursive Tower of Hanoi solution for n disks?", "O(2ⁿ)", ["O(n)", "O(n²)", "O(n log n)"], "The number of moves is 2ⁿ − 1.", d="medium", t=35, complexity={"time": "O(2ⁿ)", "space": "O(n) recursion depth"}, ver=M("Move count 2^n - 1.")),
        mk(s, "output", "What does this code print?", "7", ["6", "8", "3"], "The function counts moves: m(n) = 2·m(n−1) + 1, so m(3) = 7.", d="medium", t=55,
           code="def moves(n):\n    if n == 0:\n        return 0\n    return 2 * moves(n - 1) + 1\n\nprint(moves(3))", ver=S("7")),
        mk(s, "conceptual", "In the recursive Tower of Hanoi, which recursive step comes immediately BEFORE moving the largest disk?", "Move the top n−1 disks from the source to the spare peg", ["Move the top n−1 disks to the destination peg", "Move the largest disk to the spare peg", "Move disk 1 to the destination"],
           "The n−1 disks must be out of the way before the largest disk can move.", d="medium", t=45, ver=M("Standard recursive definition of Hanoi.")),
    ]


def all_questions():
    out = []
    for f in (binary_trees, complete_extended, tree_repr, bst_search, bst_insert_delete, traversals, recursion_intro, hanoi):
        out.extend(f())
    return out
