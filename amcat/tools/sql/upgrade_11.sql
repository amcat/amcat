CREATE TABLE "codingschemas_highlighters" (
    "id" serial NOT NULL PRIMARY KEY,
    "codingschema_id" integer NOT NULL,
    "codebook_id" integer NOT NULL REFERENCES "codebooks" ("codebook_id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("codingschema_id", "codebook_id")
);

UPDATE amcat_system SET db_version = 12;
