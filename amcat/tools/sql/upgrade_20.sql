alter table articles add insertdate timestamp  null;
alter table articles add insertscript varchar(500) null;

UPDATE amcat_system SET db_version = 21;
