alter table articlesets add featured boolean not null default false;

UPDATE amcat_system SET db_version = 28;
