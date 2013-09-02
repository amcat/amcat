ALTER TABLE codebooks_codes ADD COLUMN "ordernr" integer NOT NULL DEFAULT 0;
CREATE INDEX "codebooks_codes_ordernr" ON "codebooks_codes" ("ordernr");

UPDATE amcat_system SET db_version = 16;
