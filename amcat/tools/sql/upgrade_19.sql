ALTER TABLE codings ADD COLUMN "start" SMALLINT;
ALTER TABLE codings ADD COLUMN "end" SMALLINT;
ALTER TABLE codingschemas ADD COLUMN "subsentences" BOOL DEFAULT FALSE;
ALTER TABLE codingschemas DROP COLUMN "quasisentences";
ALTER TABLE codingschemas DROP COLUMN "isnet";

UPDATE amcat_system SET db_version = 20;
