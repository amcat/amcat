ALTER TABLE media ADD CONSTRAINT media_name_key UNIQUE (name);

UPDATE amcat_system SET db_version = 10;
