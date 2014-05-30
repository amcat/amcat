alter table tasks rename called_with to arguments;

DROP INDEX tasks_uuid;
DROP INDEX tasks_uuid_like;

ALTER TABLE tasks ALTER COLUMN "uuid" TYPE uuid USING (uuid::uuid);
ALTER TABLE tasks DROP task_name;

create unique index tasks_uuid on tasks  (uuid);

UPDATE amcat_system SET db_version = 25;
