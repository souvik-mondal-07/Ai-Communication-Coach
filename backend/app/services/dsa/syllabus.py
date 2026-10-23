"""
The complete DSA syllabus (Phase 24): 10 topics (A-J) and their subtopics.

Every bullet of the supplied syllabus is a `SyllabusItem` that lists the subtopic ids covering it,
so any syllabus line can be traced to subtopics and then to real questions. This file is static
reference data: it never claims a topic is "done" -- completion is computed from questions that exist.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Subtopic:
    id: str
    title: str


@dataclass(frozen=True)
class SyllabusItem:
    text: str
    subtopic_ids: tuple[str, ...]


@dataclass(frozen=True)
class Topic:
    id: str
    code: str
    title: str
    summary: str
    subtopics: tuple[Subtopic, ...]
    items: tuple[SyllabusItem, ...]


def _t(code, tid, title, summary, subs, items) -> Topic:
    return Topic(tid, code, title, summary, tuple(Subtopic(i, n) for i, n in subs),
                 tuple(SyllabusItem(text, tuple(ids)) for text, ids in items))


TOPICS: tuple[Topic, ...] = (
    _t("A", "complexity", "Introduction and Complexity Analysis", "Notations, time/space complexity, asymptotic bounds.",
       [("basic-concepts", "Basic concepts and notations"), ("time-space-complexity", "Time complexity and space complexity"),
        ("time-space-tradeoffs", "Time-space trade-offs"), ("big-o", "Big O notation"), ("omega", "Omega notation"),
        ("theta", "Theta notation"), ("basic-data-structures", "Basic data structures")],
       [("Basic concepts and notations.", ["basic-concepts"]), ("Time complexity and space complexity.", ["time-space-complexity"]),
        ("Time-space trade-offs.", ["time-space-tradeoffs"]), ("Big O notation.", ["big-o"]), ("Omega notation.", ["omega"]),
        ("Theta notation.", ["theta"]), ("Basic data structures.", ["basic-data-structures"])]),
    _t("B", "arrays", "Arrays", "Linear arrays, memory layout and core array operations.",
       [("array-memory", "Linear arrays and memory representation"), ("array-traversal", "Traversal"),
        ("array-insert-delete", "Insertion and deletion"), ("array-sort-search-merge", "Sorting, searching and merging"),
        ("array-complexity", "Complexity of array operations")],
       [("Linear arrays and memory representation.", ["array-memory"]),
        ("Traversal, insertion, deletion, sorting, searching, and merging.", ["array-traversal", "array-insert-delete", "array-sort-search-merge"]),
        ("Complexity analysis of array operations.", ["array-complexity"])]),
    _t("C", "sorting-searching", "Sorting and Searching", "Elementary sorts and linear/binary search.",
       [("bubble-sort", "Bubble Sort"), ("insertion-sort", "Insertion Sort"), ("selection-sort", "Selection Sort"),
        ("linear-search", "Linear Search"), ("binary-search", "Binary Search")],
       [("Bubble Sort.", ["bubble-sort"]), ("Insertion Sort.", ["insertion-sort"]), ("Selection Sort.", ["selection-sort"]),
        ("Linear Search.", ["linear-search"]), ("Binary Search.", ["binary-search"])]),
    _t("D", "linked-lists", "Linked Lists", "Singly, header, circular and doubly linked lists.",
       [("ll-intro-memory", "Introduction, memory representation and allocation"), ("ll-traversal", "Traversal"),
        ("ll-insert-delete", "Insertion and deletion"), ("ll-header", "Header linked lists: grounded and circular"),
        ("ll-doubly", "Two-way (doubly) linked lists and their operations")],
       [("Introduction, memory representation, and allocation.", ["ll-intro-memory"]),
        ("Traversal, insertion, and deletion.", ["ll-traversal", "ll-insert-delete"]),
        ("Header linked lists: grounded and circular.", ["ll-header"]),
        ("Two-way/doubly linked lists and their operations.", ["ll-doubly"])]),
    _t("E", "stacks", "Stacks", "LIFO structures, Polish notation and expression handling.",
       [("stack-representations", "Array and linked-list representations"), ("stack-operations", "Traversal, push and pop"),
        ("polish-notation", "Polish notation"), ("expression-evaluation", "Arithmetic expression evaluation"),
        ("expression-conversion", "Expression conversion and transformation")],
       [("Array and linked-list representations.", ["stack-representations"]), ("Traversal, push, and pop.", ["stack-operations"]),
        ("Polish notation.", ["polish-notation"]), ("Arithmetic expression evaluation.", ["expression-evaluation"]),
        ("Expression conversion and transformation.", ["expression-conversion"])]),
    _t("F", "queues", "Queues", "FIFO structures, priority queues and deques.",
       [("queue-representations", "Array and linked-list representations"), ("queue-operations", "Traversal, insertion and deletion"),
        ("priority-queues", "Priority queues"), ("deques", "Deques")],
       [("Array and linked-list representations.", ["queue-representations"]),
        ("Traversal, insertion, and deletion.", ["queue-operations"]), ("Priority queues.", ["priority-queues"]), ("Deques.", ["deques"])]),
    _t("G", "trees", "Trees", "Binary trees, BSTs and recursive traversals.",
       [("binary-trees", "Binary trees"), ("complete-extended-trees", "Complete and extended binary trees"),
        ("tree-representations", "Linked and sequential memory representations"), ("bst-search", "Binary Search Trees and searching"),
        ("bst-insert-delete", "BST insertion and deletion"), ("tree-traversals", "Recursive inorder, preorder and postorder traversals")],
       [("Binary trees.", ["binary-trees"]), ("Complete and extended binary trees.", ["complete-extended-trees"]),
        ("Linked and sequential memory representations.", ["tree-representations"]),
        ("Binary Search Trees; BST searching.", ["bst-search"]), ("BST insertion and deletion.", ["bst-insert-delete"]),
        ("Recursive inorder, preorder, and postorder traversals.", ["tree-traversals"])]),
    _t("H", "recursion", "Recursion", "Recursive thinking, Hanoi and divide-and-conquer sorts.",
       [("recursion-intro", "Introduction to recursion"), ("tower-of-hanoi", "Tower of Hanoi"),
        ("recursive-merge-sort", "Recursive Merge Sort"), ("recursive-quick-sort", "Recursive Quick Sort")],
       [("Introduction to recursion.", ["recursion-intro"]), ("Tower of Hanoi.", ["tower-of-hanoi"]),
        ("Recursive Merge Sort.", ["recursive-merge-sort"]), ("Recursive Quick Sort.", ["recursive-quick-sort"])]),
    _t("I", "heaps-hashing", "Heaps and Hashing", "Heaps, HeapSort and hash tables with all collision strategies.",
       [("heap-operations", "Heaps, insertion and deletion"), ("heapsort", "HeapSort"), ("hash-functions", "Hash functions and hash tables"),
        ("separate-chaining", "Open hashing: separate chaining"), ("open-addressing", "Closed hashing / open addressing"),
        ("linear-probing", "Linear probing"), ("quadratic-probing", "Quadratic probing"), ("double-hashing", "Double hashing")],
       [("Heaps, insertion, and deletion.", ["heap-operations"]), ("HeapSort.", ["heapsort"]),
        ("Hash functions and hash tables.", ["hash-functions"]), ("Open hashing using separate chaining.", ["separate-chaining"]),
        ("Closed hashing/open addressing.", ["open-addressing"]), ("Linear probing.", ["linear-probing"]),
        ("Quadratic probing.", ["quadratic-probing"]), ("Double hashing.", ["double-hashing"])]),
    _t("J", "graphs", "Graphs", "Traversals and shortest-path algorithms.",
       [("bfs", "Breadth-First Search (BFS)"), ("dfs", "Depth-First Search (DFS)"), ("dijkstra", "Dijkstra's shortest-path algorithm"),
        ("bellman-ford", "Bellman–Ford algorithm"), ("floyd-warshall", "Floyd–Warshall algorithm")],
       [("Breadth-First Search (BFS).", ["bfs"]), ("Depth-First Search (DFS).", ["dfs"]), ("Dijkstra's shortest-path algorithm.", ["dijkstra"]),
        ("Bellman–Ford algorithm.", ["bellman-ford"]), ("Floyd–Warshall algorithm.", ["floyd-warshall"])]),
)

TOPIC_BY_ID: dict[str, Topic] = {t.id: t for t in TOPICS}
SUBTOPIC_TO_TOPIC: dict[str, str] = {s.id: t.id for t in TOPICS for s in t.subtopics}
SUBTOPIC_TITLES: dict[str, str] = {s.id: s.title for t in TOPICS for s in t.subtopics}

MIN_QUESTIONS_PER_SUBTOPIC = 4


def topic_title(topic_id: str) -> str:
    t = TOPIC_BY_ID.get(topic_id)
    return t.title if t else topic_id
