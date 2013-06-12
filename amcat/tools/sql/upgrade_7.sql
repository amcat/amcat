ALTER TABLE rulesets ADD COLUMN "lexicon_codebook_id" integer NULL REFERENCES "codebooks" ("codebook_id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE rulesets ADD COLUMN "lexicon_language_id" integer NULL REFERENCES "languages" ("language_id") DEFERRABLE INITIALLY DEFERRED;

UPDATE amcat_system SET db_version = 8;
