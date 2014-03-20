alter table rulesets add preprocessing varchar(1000) not null default '';

UPDATE amcat_system SET db_version = 22;
