ALTER TABLE codingschemas ADD COLUMN "highlight_language_id" integer NULL REFERENCES "languages" ("language_id") DEFERRABLE INITIALLY DEFERRED;

UPDATE amcat_system SET db_version = 13;
