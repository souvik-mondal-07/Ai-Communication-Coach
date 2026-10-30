"""
The Python Interview Practice syllabus (Phase 26): 9 units (A-I) and 144 topics.

Every bullet of the supplied syllabus maps to a topic (a few near-duplicate bullets share one: e.g. "Identity versus equality" and
"is versus ==", or "Context managers" and "the with statement"; the coverage report lists the bullets each topic stands for). Bullets
that the brief repeats in Unit F (copying, iterators/generators, decorators, context managers, closures) get their own advanced-level
topics there. This file is static reference data: completion is always computed from questions that actually exist.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Topic:
    id: str
    title: str
    covers: str = ""  # syllabus bullet(s) this topic stands for, when they differ from the title


@dataclass(frozen=True)
class Unit:
    id: str
    code: str
    title: str
    summary: str
    topics: tuple[Topic, ...]


def _u(code: str, title: str, summary: str, rows: list[tuple]) -> Unit:
    return Unit(f"unit-{code.lower()}", code, title, summary, tuple(Topic(*r) for r in rows))


UNITS: tuple[Unit, ...] = (
    _u("A", "Python fundamentals", "The language, its execution model, types, operators and control flow.", [
        ("features-use-cases", "Python features and use cases"), ("interpreter-execution", "Interpreter and execution model"),
        ("variables-naming", "Variables, identifiers and naming rules"), ("builtin-types", "Built-in data types"),
        ("mutability", "Mutable versus immutable objects"), ("type-conversion", "Type conversion and type checking"),
        ("operators-precedence", "Operators and operator precedence"), ("input-output", "Input and output"),
        ("conditionals", "Conditional statements"), ("loops", "for and while loops"), ("break-continue-pass", "break, continue and pass"),
        ("comprehensions-basic", "Comprehensions"), ("range-enumerate-zip", "range(), enumerate() and zip()"),
        ("truthiness", "Truthiness and Boolean logic"), ("identity-equality", "Identity versus equality", "Identity versus equality; is versus =="),
    ]),
    _u("B", "Strings and collections", "Sequences, sets, dictionaries, copying, sorting and everyday collection problems.", [
        ("string-slicing", "String indexing and slicing"), ("string-methods", "String methods"), ("string-formatting", "String formatting and f-strings"),
        ("lists", "Lists and list operations"), ("tuples", "Tuples and tuple unpacking"), ("sets", "Sets and set operations"),
        ("dicts", "Dictionaries and dictionary methods"), ("nested-collections", "Nested collections"), ("copy-shallow-deep", "Shallow copy versus deep copy"),
        ("references-mutation", "References and object mutation"), ("sorting-key", "Sorting with key; sorted() versus .sort()", "Sorting with key; sorted() versus .sort()"),
        ("collection-problems", "Common collection problems"), ("frequency-counting", "Frequency counting"), ("duplicate-detection", "Duplicate detection"),
    ]),
    _u("C", "Functions and functional programming", "Defining, calling and composing functions; closures, generators and decorators.", [
        ("function-basics", "Function definitions and return values"), ("argument-passing", "Positional and keyword arguments"),
        ("default-arguments", "Default arguments"), ("args-kwargs", "*args and **kwargs"), ("scope-namespaces", "Scope and namespaces; local and global variables", "Scope and namespaces; local and global variables"),
        ("closures", "Closures"), ("lambda", "Lambda functions"), ("recursion", "Recursion"), ("higher-order", "Higher-order functions"),
        ("map-filter-reduce", "map(), filter() and reduce()"), ("iterators", "Iterables and iterators"), ("generators", "Generators and yield"),
        ("decorators", "Decorators"), ("type-hints", "Type hints"), ("docstrings", "Docstrings and function design"), ("global-nonlocal", "global and nonlocal"),
    ]),
    _u("D", "Object-oriented programming", "Classes, inheritance, polymorphism, properties, dunder methods and dataclasses.", [
        ("classes-objects", "Classes and objects"), ("init-constructors", "Constructors and __init__"), ("method-kinds", "Instance, class and static methods"),
        ("attributes", "Instance and class attributes"), ("encapsulation", "Encapsulation"), ("inheritance", "Inheritance"),
        ("multiple-inheritance", "Multiple inheritance"), ("polymorphism", "Polymorphism"), ("overriding", "Method overriding"),
        ("composition", "Composition versus inheritance"), ("abc-interfaces", "Abstract base classes and interfaces"), ("properties-descriptors", "Properties and descriptors"),
        ("mro", "Method Resolution Order (MRO)"), ("dunder-methods", "Dunder methods"), ("super", "super()"), ("dataclasses", "Dataclasses"),
        ("lifecycle-gc", "Object lifecycle and garbage collection basics"),
    ]),
    _u("E", "Exceptions, files and modules", "Error handling, resources, files, formats, packaging, logging and configuration.", [
        ("exception-hierarchy", "Exception hierarchy"), ("try-except", "try, except, else and finally"), ("raising", "Raising exceptions"),
        ("custom-exceptions", "Custom exceptions"), ("context-managers", "Context managers and the with statement", "Context managers; with statement"),
        ("file-io", "File reading and writing"), ("text-binary", "Text versus binary files"), ("paths", "Paths and directories"),
        ("json-handling", "JSON handling"), ("csv-handling", "CSV handling"), ("modules-packages", "Modules and packages"), ("import-resolution", "Imports and import resolution"),
        ("virtualenvs", "Virtual environments"), ("dependencies", "Dependency management"), ("logging", "Logging"), ("config-env", "Configuration and environment variables"),
        ("safe-errors", "Safe error handling"),
    ]),
    _u("F", "Advanced Python", "The standard-library toolkit, concurrency, memory and performance.", [
        ("genexp", "Comprehensions and generator expressions"), ("regex", "Regular expressions (re)"), ("collections-module", "The collections module"),
        ("counter-defaultdict-deque", "Counter, defaultdict and deque"), ("itertools", "itertools"), ("functools", "functools"), ("pathlib-adv", "pathlib"),
        ("datetime", "datetime"), ("json-module", "json module"), ("custom-sort-keys", "Sorting and custom comparison keys"), ("concurrency", "Concurrency concepts"),
        ("threads-processes", "Threads versus processes"), ("async-await", "async and await"), ("event-loop", "Coroutines and event loops"), ("gil", "GIL and version-sensitive behaviour"),
        ("memory-management", "Memory management"), ("profiling", "Profiling and performance basics"), ("adv-copying", "Shallow versus deep copying (advanced)"),
        ("adv-iterators-generators", "Iterators and generators (advanced)"), ("adv-decorators-closures", "Decorators and closures (advanced)"),
        ("adv-context-managers", "Context managers (advanced)"),
    ]),
    _u("G", "Algorithms and coding interviews", "Interview problem patterns, data-structure choice and complexity analysis.", [
        ("array-problems", "Array/list problems"), ("string-manipulation", "String manipulation"), ("hash-maps", "Hash maps and sets"), ("two-pointers", "Two-pointer problems"),
        ("sliding-window", "Sliding-window problems"), ("stack-queue", "Stack and queue problems"), ("searching-sorting", "Searching and sorting"), ("binary-search", "Binary search"),
        ("backtracking", "Recursion and backtracking basics"), ("linked-lists", "Linked-list concepts and implementation"), ("trees-graphs", "Tree and graph traversal concepts"),
        ("dynamic-programming", "Basic dynamic programming"), ("time-complexity", "Time complexity"), ("space-complexity", "Space complexity"), ("big-o", "Big O notation"),
        ("data-structure-choice", "Choosing appropriate data structures"), ("edge-cases", "Edge cases and test-driven problem solving"),
    ]),
    _u("H", "Python for cybersecurity and automation", "Defensive, offline automation: logs, validation, hashing, reports and safe handling of untrusted input.", [
        ("log-parsing", "Log-file parsing"), ("ip-validation", "IP-address validation (ipaddress)"), ("url-parsing", "URL parsing and validation"),
        ("file-hashing", "File hashing and integrity verification"), ("json-logs", "JSON log processing"), ("csv-reports", "CSV report generation"),
        ("regex-extraction", "Regex-based log extraction"), ("event-analysis", "Basic defensive event analysis"), ("file-automation", "File and directory automation"),
        ("http-analysis", "HTTP response analysis (controlled examples)"), ("secure-subprocess", "Secure subprocess usage"), ("input-validation", "Input validation"),
        ("automation-exceptions", "Exception handling in automation scripts"), ("secret-management", "Secret-management principles"), ("untrusted-input", "Safe handling of untrusted input"),
    ]),
    _u("I", "Python interview scenarios", "Reasoning aloud: surprising behaviour, debugging, trade-offs and design.", [
        ("unexpected-results", "Why a program produces an unexpected result"), ("choosing-collections", "Choosing between lists, tuples, sets and dictionaries"),
        ("debugging-function", "Debugging a failing function"), ("improving-code", "Improving inefficient code"), ("malformed-input", "Handling malformed input"),
        ("reusable-modules", "Designing reusable modules"), ("testable-code", "Writing testable code"), ("large-files", "Handling large files"),
        ("resource-leaks", "Preventing resource leaks"), ("concurrency-limits", "Understanding concurrency limitations"), ("explaining-code", "Explaining code to an interviewer"),
        ("tradeoffs", "Discussing trade-offs between alternative solutions"),
    ]),
)

UNIT_BY_ID = {u.id: u for u in UNITS}
TOPIC_BY_ID = {t.id: t for u in UNITS for t in u.topics}
TOPIC_TO_UNIT = {t.id: u.id for u in UNITS for t in u.topics}
MIN_QUESTIONS_PER_TOPIC = 2


def topic_title(topic_id: str) -> str:
    t = TOPIC_BY_ID.get(topic_id)
    return t.title if t else topic_id
