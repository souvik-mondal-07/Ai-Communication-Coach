"""
Unit G: NoSQL and MongoDB. MongoDB examples use MongoDB shell syntax and declare dialect 'mongodb' (they are NOT SQL).
Questions that predict a MongoDB result embed a `mongo_check` spec; tests and tools/verify_dbms_bank.py recompute them with mongomock.
"""

from __future__ import annotations

from app.services.dbms_sql.content.build import MANUAL_NOTE, mcq as M

ITEMS = [{"name": "pen", "qty": 50}, {"name": "book", "qty": 12}, {"name": "bag", "qty": 30}]
_MONGOMOCK = "Result recomputed with mongomock by tests and tools/verify_dbms_bank.py; the explanation is a maintainer-written justification."


def _mongo(spec: dict) -> dict:
    return {"mongo_check": spec}


def questions() -> list[dict]:
    return [
        # nosql-concepts
        M("nosql-concepts", "easy", "Which of these is NOT one of the common NoSQL data models?", "Relational (tables linked by foreign keys)", ["Document", "Key-value", "Graph"], "NoSQL families include document, key-value, wide-column and graph stores; the relational model is the contrast."),
        M("nosql-concepts", "medium", "The CAP theorem says a distributed data store cannot guarantee all three of:", "Consistency, availability and partition tolerance at once", ["Atomicity, caching and persistence", "Cost, speed and security", "Durability, isolation and indexing"],
          "During a network partition a system must give up either consistency or availability."),
        M("nosql-concepts", "medium", "BASE, often contrasted with ACID, stands for:", "Basically Available, Soft state, Eventually consistent", ["Binary, Atomic, Serial, Exclusive", "Backed-up, Atomic, Secure, Encrypted", "Buffered, Asynchronous, Stable, Elastic"], "BASE describes systems that favour availability and accept temporary inconsistency."),
        # mongodb-intro
        M("mongodb-intro", "easy", "MongoDB stores records as:", "BSON documents (a binary form of JSON)", ["Fixed-width rows in tables", "Edges between nodes only", "Plain CSV files"], "A document is a set of field-value pairs; BSON adds extra types such as dates and ObjectId.", dialect="mongodb"),
        M("mongodb-intro", "easy", "Which field does MongoDB use as the primary key of every document?", "_id", ["pk", "id_key", "docid"], "Every document must have a unique _id; if you omit it the driver generates an ObjectId.", dialect="mongodb"),
        M("mongodb-intro", "medium", "MongoDB scales reads and writes horizontally mainly by:", "Sharding data across several servers (with replica sets for availability)", ["Adding more columns", "Disabling indexes", "Storing everything in one file"], "Sharding partitions a collection by a shard key; replica sets provide redundancy and failover.", dialect="mongodb"),
        # dynamodb-concepts
        M("dynamodb-concepts", "medium", "In Amazon DynamoDB an item is uniquely identified by:", "Its primary key: a partition key, or a partition key plus a sort key", ["A row number", "Any attribute chosen at query time", "A foreign key to another table"], "DynamoDB hashes the partition key to place data; an optional sort key orders items within one partition key.", dialect="dynamodb"),
        M("dynamodb-concepts", "medium", "Which DynamoDB access pattern is efficient?", "Query by partition key, optionally with a sort-key condition", ["Scanning the whole table for every request", "Ad hoc joins across tables", "Arbitrary GROUP BY queries"], "Query reads only the matching partition; a Scan reads everything and is costly on large tables.", dialect="dynamodb"),
        M("dynamodb-concepts", "easy", "DynamoDB offers which two capacity modes?", "Provisioned and on-demand", ["Primary and secondary", "Row and column", "Public and private"], "Provisioned mode reserves read/write capacity; on-demand pays per request and scales automatically.", dialect="dynamodb"),
        # serverless-databases
        M("serverless-databases", "easy", "What does 'serverless' mean for a cloud database?", "You do not manage servers; capacity scales automatically and billing follows usage", ["There are no servers anywhere", "It runs only on your laptop", "It cannot store data persistently"], "Servers still exist, but the provider handles provisioning, scaling and maintenance."),
        M("serverless-databases", "medium", "Why can a serverless database suit a spiky workload?", "Capacity follows demand instead of being provisioned for the peak", ["It never needs indexes", "It ignores consistency", "It stores data only in memory"], "You avoid paying for idle peak capacity."),
        M("serverless-databases", "hard", "A typical trade-off of serverless databases is:", "Possible cold-start latency and less control over low-level tuning", ["They cannot be queried", "They forbid encryption", "They allow only one user"], "Scaling to zero or abstracting the hardware can add warm-up delay and limit tuning options; details vary by product."),
        # mongodb-structure
        M("mongodb-structure", "easy", "In MongoDB terminology, a relational table corresponds most closely to a:", "Collection", ["Document", "Field", "Shard"], "A collection groups documents; a database holds collections.", dialect="mongodb"),
        M("mongodb-structure", "easy", "A relational row corresponds most closely to a MongoDB:", "Document", ["Collection", "Index", "Cluster"], "Each document is one record, made of field-value pairs.", dialect="mongodb"),
        M("mongodb-structure", "medium", "Documents in the same MongoDB collection:", "May have different fields, optionally constrained by a JSON Schema validator", ["Must have identical fields", "Cannot contain nested documents", "Are limited to one field"], "MongoDB is schema-flexible; schema validation can be added when stricter structure is wanted.", dialect="mongodb"),
        # mongodb-crud
        M("mongodb-crud", "easy", "Which mongosh command inserts a single document into the items collection?", "db.items.insertOne({ name: \"pen\", qty: 50 })", ["db.items.add({ name: \"pen\", qty: 50 })", "db.items.put({ name: \"pen\", qty: 50 })", "db.items.insert_row({ name: \"pen\", qty: 50 })"],
          "insertOne adds one document; insertMany takes an array.", dialect="mongodb", fmt="concept"),
        M("mongodb-crud", "medium", "Given items = pen/50, book/12, bag/30 (name/qty), what does this return?", "bag, pen", ["pen, bag", "book", "bag, book, pen"],
          "The filter keeps qty greater than 20 (pen 50, bag 30); the projection keeps only name; the sort orders names ascending.", dialect="mongodb", fmt="output",
          code="db.items.find({ qty: { $gt: 20 } }, { _id: 0, name: 1 }).sort({ name: 1 })", note=_MONGOMOCK,
          extra=_mongo({"docs": ITEMS, "op": "find", "filter": {"qty": {"$gt": 20}}, "projection": {"_id": 0, "name": 1}, "sort": [["name", 1]], "expected": [{"name": "bag"}, {"name": "pen"}], "render": "names"})),
        M("mongodb-crud", "medium", "Given items = pen/50, book/12, bag/30, what is the qty of book after this command runs?", "17", ["12", "5", "62"],
          "$inc adds 5 to the existing value 12.", dialect="mongodb", fmt="output", code="db.items.updateOne({ name: \"book\" }, { $inc: { qty: 5 } })", note=_MONGOMOCK,
          extra=_mongo({"docs": ITEMS, "op": "update_then_find", "filter": {"name": "book"}, "update": {"$inc": {"qty": 5}}, "expected": [{"name": "book", "qty": 17}], "render": "qty"})),
        M("mongodb-crud", "medium", "What does db.items.deleteMany({}) do?", "Deletes every document but keeps the collection and its indexes", ["Drops the whole database", "Deletes only the first document", "Does nothing without a filter"],
          "An empty filter matches all documents. Use drop() to remove the collection itself.", dialect="mongodb"),
        # sql-vs-nosql
        M("sql-vs-nosql", "medium", "Which requirement most strongly favours a relational (SQL) database?", "Complex multi-table joins with ACID transactions", ["Storing unrelated blobs by key", "Schemaless prototypes only", "Caching HTTP responses"], "Mature joins, constraints and transactions are the relational strengths."),
        M("sql-vs-nosql", "medium", "A good reason to choose a document store is:", "Hierarchical data that is usually read together as one unit", ["Needing many-to-many joins everywhere", "Needing strict foreign keys on every field", "Avoiding any schema forever"], "Embedding related data in one document makes a single read return it all."),
        M("sql-vs-nosql", "easy", "Polyglot persistence means:", "Using different database types for different parts of one application", ["Translating SQL into many languages", "Storing every record twice", "Using one database for everything"], "For example SQL for orders, a key-value store for sessions and a search index for text."),
        # json-document-modelling
        M("json-document-modelling", "easy", "Which of these is valid JSON?", "{\"name\": \"Asha\", \"skills\": [\"SQL\", \"Mongo\"]}", ["{name: \"Asha\", skills: [\"SQL\"]}", "{'name': 'Asha'}", "{\"name\": \"Asha\",}"],
          "JSON requires double-quoted keys and strings and forbids trailing commas.", verify={"method": "json_valid"}),
        M("json-document-modelling", "medium", "When is embedding a sub-document usually the better MongoDB model?", "The data is read together and stays small and bounded (for example one user with a few addresses)", ["The sub-documents grow without bound", "The data is never read with its parent", "Each sub-document is shared by millions of parents"],
          "Embedding avoids joins for data accessed together; it suits one-to-few relationships.", dialect="mongodb"),
        M("json-document-modelling", "hard", "A blog post may collect millions of comments. Which model is safer in MongoDB?", "Store comments in their own collection with a post_id reference", ["Embed every comment in the post document", "Store all comments in one string field", "Use one collection per comment"], "Unbounded arrays make documents grow toward the 16 MB document limit and slow updates, so reference them.", dialect="mongodb"),
        # mongodb-indexes
        M("mongodb-indexes", "easy", "Which command creates an ascending index on the email field of users?", "db.users.createIndex({ email: 1 })", ["db.users.index({ email: 1 })", "db.users.addIndex(\"email\")", "db.users.createIndex(\"email\", \"ascending\")"], "createIndex takes a key document: 1 is ascending and -1 is descending.", dialect="mongodb"),
        M("mongodb-indexes", "medium", "A compound index { a: 1, b: 1 } can efficiently support a query that filters on:", "a alone, or a and b together (a leftmost prefix)", ["b alone", "Neither a nor b", "Only queries that sort by c"], "Compound indexes follow the prefix rule: the leading fields must be constrained.", dialect="mongodb"),
        M("mongodb-indexes", "medium", "Which index does every MongoDB collection have automatically?", "A unique index on _id", ["An index on every field", "A text index", "No index at all"], "MongoDB creates the _id index when a collection is created.", dialect="mongodb"),
        # explain-query-plans
        M("explain-query-plans", "medium", "In explain() output, which stage indicates a full collection scan?", "COLLSCAN", ["IXSCAN", "FETCH", "PROJECTION"], "COLLSCAN reads every document; IXSCAN reads an index.", dialect="mongodb"),
        M("explain-query-plans", "medium", "A plan with IXSCAN followed by FETCH means:", "An index finds matching entries and then the documents are read", ["No index was used", "Only the index was read, never documents", "The query failed"], "FETCH loads full documents for index matches; a covered query would skip it.", dialect="mongodb"),
        M("explain-query-plans", "hard", "In explain('executionStats'), which result suggests an efficient index use?", "totalDocsExamined is close to nReturned", ["totalDocsExamined is far larger than nReturned", "nReturned is always zero", "executionTimeMillis is negative"], "Examining many more documents than are returned means the index is not selective for this query.", dialect="mongodb"),
        # vector-databases
        M("vector-databases", "easy", "A vector database is optimised for:", "Finding the nearest neighbours of an embedding vector", ["Enforcing foreign keys", "Storing only JSON", "Running stored procedures"], "Embeddings place similar items near each other; the database retrieves the closest ones."),
        M("vector-databases", "medium", "Which measure is commonly used to compare embedding vectors?", "Cosine similarity", ["Row count", "Hamming weight of the primary key", "Checksum"], "Cosine similarity compares direction; Euclidean distance and dot product are also common."),
        M("vector-databases", "medium", "A typical use case for a vector database is:", "Semantic search that supplies context to a language model (retrieval-augmented generation)", ["Double-entry bookkeeping", "Enforcing unique usernames", "Compressing log files"], "Documents are embedded and the closest ones to a query embedding are retrieved as context."),
    ]
