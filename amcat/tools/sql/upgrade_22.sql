alter table auth_user_profile add theme varchar(255) not null default 'AmCAT';

UPDATE amcat_system SET db_version = 23;