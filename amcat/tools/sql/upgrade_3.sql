
ALTER TABLE rules ADD COLUMN display boolean NOT NULL;

UPDATE amcat_system SET db_version = 4;
