ALTER TABLE articlesets DROP COLUMN indexed;
ALTER TABLE articlesets DROP COLUMN index_dirty;
ALTER TABLE articlesets DROP COLUMN needs_deduplication;

ALTER TABLE projects DROP COLUMN index_default;


UPDATE amcat_system SET db_version = 17;
