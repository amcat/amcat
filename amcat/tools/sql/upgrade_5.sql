
ALTER TABLE articles ADD COLUMN "addressee" text;

UPDATE amcat_system SET db_version = 6;
