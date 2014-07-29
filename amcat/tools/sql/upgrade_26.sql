alter table auth_user_profile add fluid boolean not null default false;

UPDATE amcat_system SET db_version = 27;
