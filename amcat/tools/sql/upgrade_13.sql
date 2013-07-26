ALTER TABLE codebooks ADD COLUMN "split" boolean NOT NULL DEFAULT false;

UPDATE amcat_system SET db_version = 14;
