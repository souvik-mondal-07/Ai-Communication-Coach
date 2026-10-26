"""Unit F: Transactions and concurrency. Schedule analysis answers are computed by txn_algos (never hand-asserted)."""

from __future__ import annotations

from app.services.dbms_sql.content.build import mcq as M

REC = ["Not recoverable", "Recoverable but not cascadeless", "Cascadeless but not strict", "Strict"]


def _rec(topic, diff, sched, hint=None):
    from app.services.dbms_sql import txn_algos
    answer = txn_algos.recoverability_class(txn_algos.parse(sched))
    return M(topic, diff, "Classify this schedule (T1, T2 on item A; C = commit).", answer, [o for o in REC if o != answer],
             {"Not recoverable": "T2 read T1's uncommitted write and committed first; if T1 then aborted, T2's commit could not be undone.",
              "Recoverable but not cascadeless": "Every reader commits after the writer, so it is recoverable, but T2 read uncommitted data, so an abort of T1 would cascade.",
              "Cascadeless but not strict": "No transaction reads uncommitted data, but a write overwrites an uncommitted write, so it is not strict.",
              "Strict": "No item written by an uncommitted transaction is read or overwritten until that transaction ends."}[answer],
             fmt="transaction", code=sched, ref=("recoverability", {"schedule": sched}), hints=(hint,) if hint else (), est=75)


def questions() -> list[dict]:
    return [
        # transaction-concepts
        M("transaction-concepts", "easy", "A bank transfer debits one account and credits another. Why must both updates form one transaction?", "Either both take effect or neither does", ["Because two statements cannot run separately", "To make the transfer faster", "Because accounts have no keys"],
          "A transaction is a logical unit of work that must not be left half-done."),
        M("transaction-concepts", "easy", "Which statement ends a transaction and makes its changes permanent?", "COMMIT", ["ROLLBACK", "SAVEPOINT", "SELECT"], "COMMIT makes the transaction's changes durable and visible to others."),
        M("transaction-concepts", "medium", "Changes made by a transaction that then issues ROLLBACK are:", "Undone, as if the transaction had never run", ["Kept but hidden", "Applied to half of the rows", "Written to a backup only"], "ROLLBACK restores the state before the transaction began."),
        # acid
        M("acid", "easy", "In ACID the letter A stands for:", "Atomicity: all of a transaction's changes happen or none do", ["Availability of the server", "Authorization of users", "Archiving of old data"], "Atomicity gives the all-or-nothing guarantee."),
        M("acid", "medium", "A power cut happens right after COMMIT returned. The data must still be there afterwards. Which property is this?", "Durability", ["Atomicity", "Isolation", "Consistency"], "Durability means committed work survives crashes, typically via a write-ahead log."),
        M("acid", "medium", "Which property means a transaction takes the database from one valid state to another, respecting all constraints?", "Consistency", ["Isolation", "Durability", "Availability"], "Consistency preserves the integrity rules; the application and constraints cooperate to ensure it."),
        M("acid", "hard", "Which ACID property is mainly implemented by the concurrency control manager (locks or multiversioning)?", "Isolation", ["Atomicity", "Durability", "Consistency"],
          "Atomicity and durability come mainly from logging and recovery; isolation comes from concurrency control."),
        # transaction-states
        M("transaction-states", "easy", "Which sequence of states does a successfully completed transaction pass through?", "Active, partially committed, committed", ["Active, committed, partially committed", "Partially committed, active, committed", "Active, failed, committed"],
          "After its last statement a transaction is partially committed; it commits once its changes are safely recorded."),
        M("transaction-states", "medium", "A transaction enters the failed state when:", "Normal execution can no longer proceed, for example after an error or an abort decision", ["It reads its first row", "It acquires a shared lock", "Another transaction commits"],
          "From failed it moves to aborted after rollback."),
        M("transaction-states", "medium", "Once a transaction is in the aborted state, the system may:", "Restart it (for a hardware or software error) or kill it", ["Commit it later", "Move it back to partially committed", "Ignore its undo log"], "An aborted transaction has been rolled back; restart is possible if the failure was not a logical error."),
        # schedules
        M("schedules", "easy", "How many different serial schedules exist for 3 transactions?", "6", ["3", "9", "12"], "Each ordering of the transactions is a serial schedule: 3! = 6.", fmt="transaction", ref=("serial_count", {"n": 3})),
        M("schedules", "medium", "T1 has 2 operations and T2 has 3. How many interleavings preserve each transaction's own operation order?", "10", ["5", "6", "20"], "Choose which 2 of the 5 positions belong to T1: C(5,2) = 10.", fmt="transaction", ref=("interleavings", {"lengths": [2, 3]})),
        M("schedules", "easy", "Which description defines a schedule in transaction processing?", "An ordering of the operations of several transactions that keeps each transaction's own order", ["A list of table names", "A backup timetable", "The set of indexes used"], "Schedules describe how operations of concurrent transactions are interleaved."),
        # serial-concurrent
        M("serial-concurrent", "easy", "Why run transactions concurrently instead of strictly one after another?", "To raise throughput and cut waiting by overlapping I/O and CPU work", ["Because serial execution is incorrect", "To avoid using locks", "To make rollback impossible"], "Serial execution is correct but slow; concurrency improves utilisation."),
        M("serial-concurrent", "medium", "A serial schedule is always:", "Correct, because each transaction runs alone on a consistent database", ["Non-recoverable", "Faster than any concurrent schedule", "Deadlock-prone"], "If each transaction preserves consistency, running them one at a time does too."),
        M("serial-concurrent", "medium", "Uncontrolled concurrent execution can cause:", "Lost updates and inconsistent reads", ["Faster commits only", "Smaller logs", "Duplicate indexes"], "Without concurrency control interleavings can break isolation."),
        # serializability
        M("serializability", "medium", "Is the schedule conflict serializable?", "No", ["Yes", "Only if T2 commits first", "It is serial"],
          "R1(A) before W2(A) gives T1 -> T2, and W2(A) before W1(A) gives T2 -> T1. The precedence graph has a cycle.", fmt="transaction", code="R1(A) W2(A) W1(A) C1 C2",
          ref=("conflict_serializable", {"schedule": "R1(A) W2(A) W1(A) C1 C2"}), hints=("Draw an edge Ti -> Tj for each conflicting pair where Ti's operation comes first.",)),
        M("serializability", "medium", "Give an equivalent serial order for the conflict-serializable schedule.", "T1 → T2", ["T2 → T1", "Not serializable", "T1 → T1"],
          "Every conflict is T1 before T2, so the precedence graph has the single edge T1 -> T2.", fmt="transaction", code="R1(A) W1(A) R2(A) W2(A) R1(B) W1(B) R2(B) W2(B) C1 C2",
          ref=("serial_order", {"schedule": "R1(A) W1(A) R2(A) W2(A) R1(B) W1(B) R2(B) W2(B) C1 C2"})),
        M("serializability", "hard", "This schedule has blind writes. Is it view serializable?", "Yes", ["No", "Only if T3 commits first", "View serializability needs no checking"],
          "It is not conflict serializable (T1 and T2 form a cycle) but it is view equivalent to T1, T2, T3: T1 reads the initial A and T3 performs the final write.", fmt="transaction",
          code="R1(A) W2(A) W1(A) W3(A) C1 C2 C3", ref=("view_serializable", {"schedule": "R1(A) W2(A) W1(A) W3(A) C1 C2 C3"})),
        M("serializability", "hard", "How are conflict and view serializability related?", "Every conflict-serializable schedule is view serializable, but not conversely", ["They are the same set of schedules", "Every view-serializable schedule is conflict serializable", "They are unrelated"],
          "Conflict serializability is strictly stronger; view serializability additionally admits some schedules with blind writes, and testing it is NP-complete."),
        M("serializability", "easy", "A cycle in the precedence (serialization) graph means the schedule is:", "Not conflict serializable", ["Conflict serializable", "Always serial", "Always recoverable"], "An acyclic graph is required for conflict serializability."),
        # concurrency-control
        M("concurrency-control", "easy", "Which approach assumes conflicts are rare and validates transactions at commit time?", "Optimistic concurrency control", ["Two-phase locking", "Strict serial execution", "Write-ahead logging"], "Optimistic methods let transactions run without locks and check for conflicts before committing."),
        M("concurrency-control", "medium", "Under timestamp ordering, T (timestamp 5) tries to write item X whose read timestamp is 9. What happens?", "The write is rejected and T is rolled back and restarted with a new timestamp", ["The write succeeds", "T waits for a lock", "X's read timestamp is lowered to 5"],
          "A younger transaction (9) has already read X, so an older write (5) would invalidate that read."),
        M("concurrency-control", "medium", "What does multiversion concurrency control (MVCC) let readers do?", "Read a consistent snapshot without blocking writers", ["Block all writers", "Skip transactions", "Avoid commit"], "Readers see an older committed version while writers create new ones."),
        # locking
        M("locking", "easy", "Which pair of lock requests on the same item is compatible?", "Shared with shared", ["Shared with exclusive", "Exclusive with exclusive", "None are compatible"], "Many readers may share an item; a writer needs exclusive access."),
        M("locking", "medium", "In two-phase locking a transaction:", "Cannot acquire any new lock after it has released one", ["Must release all locks before it starts", "May only hold shared locks", "Releases each lock right after use"], "The growing phase acquires locks; the shrinking phase releases them."),
        M("locking", "medium", "Does this lock sequence follow two-phase locking?", "No", ["Yes", "Only for T1's reads", "It depends on commit order"], "T1 requests X1(C) after it already released a lock (U1(A)), violating the two-phase rule.",
          fmt="transaction", code="X1(A) S1(B) U1(A) X1(C) U1(B) U1(C)", ref=("two_phase", {"schedule": "X1(A) S1(B) U1(A) X1(C) U1(B) U1(C)"})),
        M("locking", "hard", "Strict two-phase locking holds all of a transaction's exclusive locks until:", "The transaction commits or aborts", ["The next statement runs", "The transaction reads its last row", "The checkpoint"], "This prevents others from reading or overwriting uncommitted data, which avoids cascading rollbacks."),
        # deadlocks
        M("deadlocks", "medium", "Do these lock requests lead to a deadlock? Give the transactions involved.", "Deadlock: T1, T2", ["No deadlock", "Deadlock: T1 only", "Deadlock: T2 only"],
          "T1 holds A and waits for B, while T2 holds B and waits for A: a cycle in the wait-for graph.", fmt="transaction", code="X1(A) X2(B) X1(B) X2(A)",
          ref=("deadlock", {"schedule": "X1(A) X2(B) X1(B) X2(A)"}), hints=("Who holds what, and who is waiting for it?",)),
        M("deadlocks", "medium", "Do these requests lead to a deadlock?", "No deadlock", ["Deadlock: T1, T2", "Deadlock: T1 only", "Deadlock: T2 only"],
          "T2 waits for A, but T1 releases it with U1(A), after which T2 is granted the lock. No wait-for cycle remains.", fmt="transaction", code="X1(A) S2(A) U1(A) X2(B)",
          ref=("deadlock", {"schedule": "X1(A) S2(A) U1(A) X2(B)"})),
        M("deadlocks", "medium", "Which technique prevents deadlock by making all transactions request locks in the same global order?", "Lock ordering", ["Timestamp reset", "Cascading rollback", "Checkpointing"], "If every transaction acquires locks in one fixed order, a circular wait cannot form."),
        M("deadlocks", "hard", "In the wait-die scheme, what happens when an older transaction requests a lock held by a younger one?", "The older transaction waits", ["The older transaction is aborted", "Both are aborted", "The younger is granted the lock"], "Wait-die lets older transactions wait and aborts ('dies') a younger requester, so waits never form a cycle."),
        # recoverability
        _rec("recoverability", "medium", "W1(A) R2(A) C2 C1", "Which transaction committed first, and whose data did it read?"),
        _rec("recoverability", "medium", "W1(A) R2(A) C1 C2"),
        _rec("recoverability", "hard", "W1(A) C1 R2(A) W2(A) C2"),
        _rec("recoverability", "hard", "W1(A) W2(A) C1 C2"),
        # cascading-rollback
        M("cascading-rollback", "medium", "T1 aborts. Which transactions must also roll back?", "T2, T3", ["None", "T2 only", "T3 only"],
          "T2 read T1's uncommitted write of A, and T3 read T2's uncommitted write of B, so the rollback cascades to both.", fmt="transaction", code="W1(A) R2(A) W2(B) R3(B) A1",
          ref=("cascade_victims", {"schedule": "W1(A) R2(A) W2(B) R3(B) A1", "aborted": 1})),
        M("cascading-rollback", "medium", "T2 aborts in this schedule. Which other transactions must roll back?", "None", ["T1", "T1, T2", "T3"], "Nobody read data written by T2, so nothing cascades.", fmt="transaction", code="W1(A) R2(A) C1 A2",
          ref=("cascade_victims", {"schedule": "W1(A) R2(A) C1 A2", "aborted": 2})),
        M("cascading-rollback", "easy", "Which schedule class guarantees that no cascading rollback can occur?", "Cascadeless (avoids cascading aborts)", ["Any serializable schedule", "Any recoverable schedule", "Any serial-looking schedule"], "In a cascadeless schedule every read reads only committed data; recoverability alone does not prevent cascades."),
        # read-anomalies
        M("read-anomalies", "easy", "T1 updates a row but has not committed. T2 reads the new value, then T1 rolls back. This anomaly is a:", "Dirty read", ["Non-repeatable read", "Phantom read", "Lost commit"], "T2 saw data that never officially existed."),
        M("read-anomalies", "medium", "T1 reads a row twice. Between the reads T2 commits an update to that row, so T1 sees two different values. This is a:", "Non-repeatable read", ["Dirty read", "Phantom read", "Deadlock"], "The same row returns different values within one transaction."),
        M("read-anomalies", "medium", "T1 runs the same SELECT ... WHERE dept = 1 twice. Between runs T2 commits a new matching row, so the second run returns an extra row. This is a:", "Phantom read", ["Dirty read", "Non-repeatable read", "Lost update"], "A set of rows changes, not just a value in an existing row."),
        # isolation-levels
        M("isolation-levels", "medium", "According to the SQL standard, can a dirty read occur at READ COMMITTED?", "Not possible", ["Possible", "Only with explicit table locks", "Only for read-only transactions"], "READ COMMITTED prevents dirty reads; it still allows non-repeatable and phantom reads.", fmt="transaction",
          ref=("isolation_allows", {"level": "read committed", "anomaly": "dirty read"})),
        M("isolation-levels", "medium", "According to the SQL standard, can a phantom read occur at REPEATABLE READ?", "Possible", ["Not possible", "Only at READ UNCOMMITTED", "Only at SERIALIZABLE"], "The standard permits phantoms at REPEATABLE READ; only SERIALIZABLE forbids them. (Real products differ: PostgreSQL's REPEATABLE READ is snapshot isolation.)",
          fmt="transaction", ref=("isolation_allows", {"level": "repeatable read", "anomaly": "phantom read"})),
        M("isolation-levels", "easy", "According to the SQL standard, can a non-repeatable read occur at READ UNCOMMITTED?", "Possible", ["Not possible", "Only with locks", "Never in any DBMS"], "READ UNCOMMITTED is the weakest level and allows all three read anomalies.", fmt="transaction",
          ref=("isolation_allows", {"level": "read uncommitted", "anomaly": "non-repeatable read"})),
        M("isolation-levels", "hard", "In PostgreSQL, asking for READ UNCOMMITTED behaves like:", "READ COMMITTED", ["Dirty reads being allowed", "SERIALIZABLE", "No isolation at all"], "PostgreSQL never allows dirty reads, so READ UNCOMMITTED is treated as READ COMMITTED, its default.", dialect="postgresql"),
        M("isolation-levels", "medium", "What is the default isolation level of MySQL's InnoDB engine?", "REPEATABLE READ", ["READ UNCOMMITTED", "READ COMMITTED", "SERIALIZABLE"], "InnoDB defaults to REPEATABLE READ (using consistent snapshots and gap locks).", dialect="mysql"),
    ]
