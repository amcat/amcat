ALTER TABLE articlesets ADD needs_deduplication boolean NOT NULL DEFAULT FALSE;

UPDATE amcat_system SET db_version = 9;
