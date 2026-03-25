-- Remove loop_history table. It was a misguided port of InMemoryStateManager's
-- bounded Queue (needed to prevent unbounded memory growth). In Postgres, rows
-- don't consume process memory, and the cleanup logic could delete active loops.
DROP TABLE IF EXISTS loop_history;
