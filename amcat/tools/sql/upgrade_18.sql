-- This SQL populates 'coded_articles' based on the current codings in 'codings'. It
-- needs multiple transactions as PostgreSQL does not support altering schema after
-- performing UPDATE.

-- In case transaction 2 went wrong
ALTER TABLE codings DROP COLUMN IF EXISTS coded_article_id;
DROP INDEX IF EXISTS temp_codingjob_article_index;
CREATE INDEX temp_codingjob_article_index ON coded_articles (codingjob_id, article_id);
DELETE FROM coded_articles;

-- Add coded_article_id (FK) and populate coded_articles
START TRANSACTION;
	-- Populate coded_articles. Has DISTINCT ON to cope with corrupt datasets which
  -- hold multiple "article codings" per codingjob/article.
	INSERT INTO coded_articles (codingjob_id, article_id, status_id, comments)
	   (SELECT DISTINCT ON (codingjob_id, article_id) codingjob_id, article_id, status_id, comments
	    FROM codings
	    WHERE sentence_id IS NULL);

	ALTER TABLE codings ADD
	    coded_article_id integer NULL
	    REFERENCES "coded_articles" ("id");
END;

-- Set coded_article_id and add 'missing' codings
START TRANSACTION;
	INSERT INTO coded_articles (codingjob_id, article_id, status_id)
	   (SELECT c.codingjob_id, aset.article_id, 0
	    FROM codingjobs c INNER JOIN articlesets_articles aset ON aset.articleset_id = c.articleset_id
	    WHERE NOT EXISTS (
         SELECT *
         FROM coded_articles ca
         WHERE
           ca.codingjob_id = c.codingjob_id AND
           ca.article_id = aset.article_id
      ));

	UPDATE codings SET coded_article_id = ca.id
		FROM codings c, coded_articles ca
		WHERE
		    c.codingjob_id = ca.codingjob_id AND
		    c.article_id = ca.article_id;
END;

-- Clean up by deleting obsolete columns
START TRANSACTION;
  DROP INDEX temp_codingjob_article_index;
	ALTER TABLE codings DROP COLUMN article_id;
	ALTER TABLE codings DROP COLUMN codingjob_id;
	ALTER TABLE codings DROP COLUMN status_id;
	ALTER TABLE codings DROP COLUMN comments;
	ALTER TABLE codings ALTER COLUMN coded_article_id SET NOT NULL;
  UPDATE amcat_system SET db_version = 19;
END;

