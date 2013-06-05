alter table codingschemas_fields drop constraint codingschemas_fields_codingschema_id_fieldnr_key;

UPDATE amcat_system SET db_version = 3;
