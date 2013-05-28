alter table codes add column uuid uuid not null default uuid_generate_v1();

UPDATE amcat_system SET db_version = 2;
