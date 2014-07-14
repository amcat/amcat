CREATE SEQUENCE record_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE records (
    record_id integer DEFAULT nextval('record_id_seq'::regclass) NOT NULL,
    category text,
    event_type text,
    target_id integer,
    ts timestamp without time zone,
    article_id integer,
    codingjob_id integer,
    user_id integer
);