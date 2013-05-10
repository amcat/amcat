CREATE TABLE "auth_user_profile_favourite_articlesets" (
    "id" serial NOT NULL PRIMARY KEY,
    "userprofile_id" integer NOT NULL,
    "articleset_id" integer NOT NULL REFERENCES "articlesets" ("articleset_id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("userprofile_id", "articleset_id")
)
;
CREATE TABLE "auth_user_profile_favourite_projects" (
    "id" serial NOT NULL PRIMARY KEY,
    "userprofile_id" integer NOT NULL,
    "project_id" integer NOT NULL REFERENCES "projects" ("project_id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("userprofile_id", "project_id")
)
;


ALTER TABLE "auth_user_profile_favourite_articlesets" ADD CONSTRAINT "userprofile_id_refs_id_479b5ccf" FOREIGN KEY ("userprofile_id") REFERENCES "auth_user_profile" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "auth_user_profile_favourite_projects" ADD CONSTRAINT "userprofile_id_refs_id_504a00f1" FOREIGN KEY ("userprofile_id") REFERENCES "auth_user_profile" ("id") DEFERRABLE INITIALLY DEFERRED;

UPDATE amcat_system SET db_version = 1;
