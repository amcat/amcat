alter table codingjobs add archived boolean not null default false;

UPDATE amcat_system SET db_version = 26;
