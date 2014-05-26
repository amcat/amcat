alter table tasks add callback_class_name text null;

UPDATE amcat_system SET db_version = 24;
