
ALTER TABLE rules RENAME COLUMN "delete" TO remove;
UPDATE amcat_system SET db_version = 5;
