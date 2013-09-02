ALTER TABLE codebooks DROP COLUMN "split";
ALTER TABLE codingschemas_fields ADD COLUMN "split_codebook" boolean NOT NULL DEFAULT false;

UPDATE amcat_system SET db_version = 15;
