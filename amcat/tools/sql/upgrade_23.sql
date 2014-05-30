ALTER TABLE tasks ADD handler_class_name text NOT NULL DEFAULT '';
ALTER TABLE tasks ALTER handler_class_name DROP DEFAULT;

UPDATE amcat_system SET db_version = 24;
