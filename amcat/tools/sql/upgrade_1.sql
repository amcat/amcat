alter table codes add column uuid uuid not null default uuid_generate_v1();
ALTER TABLE codes ADD CONSTRAINT codes_uuid_key UNIQUE (uuid);

UPDATE amcat_system SET db_version = 2;
