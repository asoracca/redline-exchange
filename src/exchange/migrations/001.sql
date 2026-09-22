BEGIN IMMEDIATE;
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE events (
 seq INTEGER PRIMARY KEY,
 request_id TEXT NOT NULL UNIQUE,
 command TEXT NOT NULL,
 result TEXT NOT NULL
);
CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN
 SELECT RAISE(ABORT, 'append-only journal');
END;
CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN
 SELECT RAISE(ABORT, 'append-only journal');
END;
PRAGMA user_version = 1;
COMMIT;
