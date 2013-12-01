CREATE INDEX "tasks_uuid" ON "tasks" ("uuid");
CREATE INDEX "tasks_uuid_like" ON "tasks" ("uuid" varchar_pattern_ops);

UPDATE amcat_system SET db_version = 18;
