"""Unit D: Relational database design. Dependency, normal-form, MVD and decomposition answers are computed by design_algos."""

from __future__ import annotations

from app.services.dbms_sql.content.build import mcq as M, short as S

CTB = ["C", "T", "B"]
FULL = [("DB", "Rao", "Korth"), ("DB", "Rao", "Date"), ("DB", "Sen", "Korth"), ("DB", "Sen", "Date")]


def questions() -> list[dict]:
    return [
        # data-integrity
        M("data-integrity", "easy", "Entity integrity requires that:", "Primary key values are unique and never NULL", ["Every foreign key is NULL", "Every column has a default", "Every table has an index"],
          "Entity integrity guarantees each row can be identified; it concerns primary keys."),
        M("data-integrity", "medium", "Which integrity type does a FOREIGN KEY enforce?", "Referential integrity", ["Entity integrity", "Domain integrity", "Isolation"],
          "Referential integrity keeps relationships valid: every reference must point to an existing parent row."),
        M("data-integrity", "medium", "A rule such as 'an order total must equal the sum of its line items' is best described as:", "A user-defined (business-rule) integrity constraint",
          ["Entity integrity", "Referential integrity", "A physical storage rule"], "It is a semantic rule specific to the application, enforced with checks, triggers or application logic."),
        # functional-dependencies
        M("functional-dependencies", "easy", "Given A->B and B->C, what is the attribute closure of {A}?", "{A, B, C}", ["{A}", "{A, B}", "{B, C}"],
          "Start with A, add B (A->B), then C (B->C).", fmt="design", ref=("closure", {"fds": "A->B, B->C", "x": "A"})),
        S("functional-dependencies", "medium", "With the dependencies A->C, BC->D and D->E, compute the closure of {A, B}.", "attrs", ["A", "B", "C", "D", "E"],
          "Type the attributes of the closure as letters, e.g. ABC.", "A gives C; with B we have BC, so D; D gives E. The closure is {A, B, C, D, E}.",
          ("closure", {"fds": "A->C, BC->D, D->E", "x": "AB"}), hints=("Repeat until no dependency adds a new attribute.",)),
        M("functional-dependencies", "easy", "Which dependency is trivial?", "AB -> A", ["A -> AB", "A -> B", "B -> AC"], "X -> Y is trivial when Y is a subset of X.", fmt="design"),
        M("functional-dependencies", "medium", "Armstrong's transitivity axiom states:", "If X -> Y and Y -> Z then X -> Z", ["If X -> Y then Y -> X", "If X -> Y then X -> YZ for any Z", "If X -> Z then X -> Y for any Y"],
          "Transitivity lets dependencies chain; it is one of the sound and complete Armstrong axioms (with reflexivity and augmentation)."),
        # normalization-purpose
        M("normalization-purpose", "easy", "The main purpose of normalization is to:", "Reduce redundancy and avoid insert, update and delete anomalies", ["Make queries always faster", "Encrypt the data", "Remove the need for keys"],
          "Normalization organises attributes so each fact is stored once, preventing anomalies."),
        M("normalization-purpose", "medium", "A common cost of highly normalized designs is:", "More joins are needed to reassemble related data", ["Larger duplicate storage", "No primary keys", "Inability to use indexes"],
          "Splitting facts across tables improves integrity but queries must join them; some systems denormalize selectively for read speed."),
        M("normalization-purpose", "hard", "Denormalization is usually justified when:", "Read performance for known queries outweighs the risk and cost of keeping duplicates consistent", ["The schema has no foreign keys", "Anomalies are desired", "Tables are empty"],
          "It is a deliberate trade-off, not a default; duplicates must then be maintained consistently."),
        # 1nf
        M("1nf", "easy", "A table stores phone_numbers as '555-1, 555-2' in one cell. Which normal form is violated?", "First normal form (atomic values)", ["Second normal form", "Third normal form", "BCNF"],
          "1NF requires every attribute value to be atomic; a list in one cell is not."),
        M("1nf", "medium", "Which change brings the phone_numbers column into 1NF?", "Store one phone number per row, in a separate table keyed by employee", ["Make the column wider", "Add an index on the column", "Rename the column"],
          "Move the repeating values into rows (employee_phone(emp_id, phone))."),
        M("1nf", "easy", "Which is NOT required of a relation in 1NF?", "That every attribute depends on the whole primary key", ["Atomic attribute values", "No repeating groups", "A way to identify each row"],
          "Dependence on the whole key is the 2NF requirement."),
        # 2nf
        M("2nf", "medium", "R(A,B,C,D) has AB->C and B->D. What is the highest normal form of R?", "1NF", ["2NF", "3NF", "BCNF"],
          "The key is {A, B}. D depends on B alone, a partial dependency, so R is not in 2NF.", fmt="design", ref=("highest_nf", {"attrs": "ABCD", "fds": "AB->C, B->D"}), hints=("Find the candidate key first, then look for partial dependencies.",)),
        M("2nf", "easy", "Is R(A,B,C) with A->B and B->C in 2NF?", "Yes", ["No", "Only if C is the key", "It depends on the data"],
          "The only candidate key is {A}, a single attribute, so a partial dependency is impossible.", fmt="design", ref=("is_2nf", {"attrs": "ABC", "fds": "A->B, B->C"})),
        M("2nf", "easy", "A relation is in 2NF if it is in 1NF and:", "No non-prime attribute depends on part of a candidate key", ["Every attribute is prime", "No attribute is NULL", "It has exactly two columns"],
          "2NF removes partial dependencies of non-prime attributes on a proper subset of a candidate key."),
        # 3nf
        M("3nf", "medium", "R(A,B,C) has A->B and B->C. What is its highest normal form?", "2NF", ["1NF", "3NF", "BCNF"],
          "The key is {A}. A->B->C is a transitive dependency of non-prime C on the key, so R is in 2NF but not 3NF.", fmt="design", ref=("highest_nf", {"attrs": "ABC", "fds": "A->B, B->C"})),
        M("3nf", "medium", "R(A,B,C) has AB->C and C->B. What is its highest normal form?", "3NF", ["2NF", "BCNF", "1NF"],
          "Keys are {A,B} and {A,C}, so B is prime. C->B has a non-superkey left side but a prime right side, which 3NF allows; BCNF does not.", fmt="design", ref=("highest_nf", {"attrs": "ABC", "fds": "AB->C, C->B"})),
        M("3nf", "easy", "A relation is in 3NF if for every nontrivial X->A either X is a superkey or:", "A is a prime attribute", ["A is NULL", "X is a single attribute", "A is a foreign key"],
          "That is the 3NF condition: determinants are superkeys, or the dependent attribute is part of some candidate key."),
        # bcnf
        M("bcnf", "medium", "Is R(A,B,C) with AB->C and C->B in BCNF?", "No", ["Yes", "Only if A is NULL", "Cannot be determined"],
          "C is a determinant but not a superkey ({C} does not determine A), so BCNF is violated.", fmt="design", ref=("is_bcnf", {"attrs": "ABC", "fds": "AB->C, C->B"})),
        M("bcnf", "easy", "Is R(A,B,C) with A->B and A->C in BCNF?", "Yes", ["No", "Only with a third dependency", "Only if B and C are keys"],
          "A determines every attribute, so it is a key and the only determinant.", fmt="design", ref=("is_bcnf", {"attrs": "ABC", "fds": "A->B, A->C"})),
        M("bcnf", "hard", "A relation can be in 3NF but not BCNF only when:", "A determinant that is not a superkey determines a prime attribute", ["It has no candidate key", "It has a NULL key", "It is not in 1NF"],
          "3NF tolerates non-superkey determinants whose dependents are prime; BCNF does not."),
        # multivalued-dependencies
        M("multivalued-dependencies", "medium", "In this instance of R(C, T, B) the rows are (DB,Rao,Korth), (DB,Rao,Date), (DB,Sen,Korth), (DB,Sen,Date). Does C ->> T hold?", "Holds", ["Does not hold", "Only if T is a key", "It is trivial"],
          "For course DB every teacher is paired with every book, so swapping teachers between tuples yields tuples that already exist.", fmt="design",
          ref=("mvd_holds", {"columns": CTB, "rows": [list(r) for r in FULL], "x": "C", "y": "T"})),
        M("multivalued-dependencies", "hard", "The row (DB,Sen,Date) is deleted from that instance, leaving (DB,Rao,Korth), (DB,Rao,Date), (DB,Sen,Korth). Does C ->> T now hold?", "Does not hold", ["Holds", "It becomes trivial", "Only if C is a key"],
          "Swapping T between (DB,Rao,Date) and (DB,Sen,Korth) requires the missing tuple (DB,Sen,Date), so the MVD fails.", fmt="design",
          ref=("mvd_holds", {"columns": CTB, "rows": [list(r) for r in FULL[:3]], "x": "C", "y": "T"})),
        M("multivalued-dependencies", "easy", "X ->> Y (a multivalued dependency) means that for a given X value:", "The set of Y values is independent of the other attributes", ["Y is a function of X", "Y is always NULL", "X is the primary key"],
          "An MVD says the Y values associated with X are independent of the remaining attributes, so all combinations appear."),
        # 4nf
        M("4nf", "medium", "R(C,T,B) has no functional dependencies but has C ->> T. Is it in 4NF?", "Not in 4NF", ["In 4NF", "In 4NF only if C is NULL", "It is in 4NF because it is in BCNF"],
          "C ->> T is nontrivial (T and C do not cover all attributes) and C is not a superkey, so 4NF is violated even though the relation is trivially in BCNF.", fmt="design",
          ref=("in_4nf", {"attrs": "CTB", "mvds": "C->>T"})),
        M("4nf", "medium", "R(A,B,C) has A->BC (so A is a key) and the multivalued dependency A ->> B. Is it in 4NF?", "In 4NF", ["Not in 4NF", "Not in 4NF because MVDs are forbidden", "Not in 1NF"],
          "The left side A is a superkey, so the MVD does not violate 4NF.", fmt="design", ref=("in_4nf", {"attrs": "ABC", "fds": "A->BC", "mvds": "A->>B"})),
        M("4nf", "easy", "To bring R(Course, Teacher, Book) with Course ->> Teacher into 4NF you decompose it into:", "(Course, Teacher) and (Course, Book)", ["(Teacher, Book) only", "(Course, Teacher, Book) unchanged", "Three one-column tables"],
          "4NF decomposition splits on the violating MVD, giving one relation per independent multivalued fact."),
        # anomalies
        M("anomalies", "easy", "In Employee(emp, dept, dept_head), deleting the only employee of a department also deletes the department head's information. This is a:", "Deletion anomaly", ["Insertion anomaly", "Update anomaly", "Phantom read"],
          "Facts about the department are lost as a side effect of deleting an employee."),
        M("anomalies", "easy", "In Employee(emp, dept, dept_head) a new department cannot be recorded until it has an employee. This is a:", "Insertion anomaly", ["Deletion anomaly", "Update anomaly", "Dirty read"],
          "The department fact depends on a row for some employee existing."),
        M("anomalies", "medium", "dept_head is stored in every employee row. Changing a head requires editing many rows, and missing one leaves conflicting data. This is a:", "Update anomaly", ["Insertion anomaly", "Deletion anomaly", "Lost update"],
          "Redundant copies of one fact must all change together; otherwise the data becomes inconsistent."),
        # decomposition-lossless
        M("decomposition-lossless", "medium", "R(A,B,C) has A->B. Is the decomposition {A,B} and {A,C} lossless?", "Lossless", ["Lossy", "Only if C is a key", "Not decidable"],
          "The common attribute A determines B, so A is a key of {A,B}; the natural join reconstructs R exactly.", fmt="design",
          ref=("lossless", {"attrs": "ABC", "fds": "A->B", "decomp": ["AB", "AC"]}), hints=("Does the shared attribute determine one of the two parts?",)),
        M("decomposition-lossless", "medium", "R(A,B,C) has A->B. Is the decomposition {A,B} and {B,C} lossless?", "Lossy", ["Lossless", "Always lossless", "Lossless only for empty tables"],
          "The shared attribute B determines neither {A,B} nor {B,C}, so the join can create spurious tuples.", fmt="design",
          ref=("lossless", {"attrs": "ABC", "fds": "A->B", "decomp": ["AB", "BC"]})),
        M("decomposition-lossless", "hard", "R(A,B,C) has A->B and B->C. Decompose into {A,B} and {A,C}. Is every dependency preserved?", "Not preserved", ["Preserved", "Preserved only for A->B", "Preserved only for B->C"],
          "The decomposition is lossless, but B->C cannot be checked inside either relation, because B and C never appear together.", fmt="design",
          ref=("dep_preserving", {"attrs": "ABC", "fds": "A->B, B->C", "decomp": ["AB", "AC"]})),
    ]
