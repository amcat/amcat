ALTER TABLE codings ADD COLUMN "start" SMALLINT;
ALTER TABLE codings ADD COLUMN "end" SMALLINT;

UPDATE amcat_system SET db_version = 20;
