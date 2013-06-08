CREATE TABLE "projects_favourite_articlesets" (
    "id" serial NOT NULL PRIMARY KEY,
    "project_id" integer NOT NULL,
    "articleset_id" integer NOT NULL REFERENCES "articlesets" ("articleset_id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("project_id", "articleset_id")
)
;

ALTER TABLE "projects_favourite_articlesets" ADD CONSTRAINT "project_id_refs_project_id_f63694ad" FOREIGN KEY ("project_id") REFERENCES "projects" ("project_id") DEFERRABLE INITIALLY DEFERRED;

-- Make any set that someone made favourite favourite in all projects it occurs in
insert into projects_favourite_articlesets (project_id, articleset_id)
select project_id, articleset_id from articlesets where articleset_id in (Select articleset_id from  auth_user_profile_favourite_articlesets);

insert into projects_favourite_articlesets (project_id, articleset_id)
select project_id, articleset_id from projects_articlesets where articleset_id in (Select articleset_id from  auth_user_profile_favourite_articlesets)
and not exists (select project_id from  projects_favourite_articlesets x where x.project_id = projects_articlesets.project_id and x.articleset_id = projects_articlesets.articleset_id);

drop table auth_user_profile_favourite_articlesets;



UPDATE amcat_system SET db_version = 6;
