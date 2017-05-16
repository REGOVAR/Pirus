-- 
-- CREATE ALL - V0.2.0
--
CREATE TYPE file_status AS ENUM ('uploading', 'uploaded', 'checked', 'error');
CREATE TYPE pipe_status AS ENUM ('initializing', 'installing', 'ready', 'error');
CREATE TYPE job_status AS ENUM ('waiting', 'initializing', 'running', 'pause', 'finalizing', 'done', 'canceled', 'error');








CREATE TABLE public.file
(
    id serial NOT NULL,
    name character varying(255) COLLATE pg_catalog."C",
    type character varying(50) COLLATE pg_catalog."C",
    "path" text COLLATE pg_catalog."C",
    size bigint DEFAULT 0,
    upload_offset bigint DEFAULT 0,
    status file_status,
    create_date timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tags text COLLATE pg_catalog."C",
    md5sum character varying(32) COLLATE pg_catalog."C",
    job_source_id int,
    CONSTRAINT file_pkey PRIMARY KEY (id),
    CONSTRAINT file_ukey UNIQUE ("path")
);
ALTER TABLE public.file OWNER TO pirus;


CREATE TABLE public.pipeline
(
    id serial NOT NULL,
    name character varying(255) COLLATE pg_catalog."C",
    type character varying(50) COLLATE pg_catalog."C",
    status pipe_status,
    description text COLLATE pg_catalog."C",
    license character varying(255) COLLATE pg_catalog."C",
    developers text COLLATE pg_catalog."C",
    installation_date timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,

    version character varying(50) COLLATE pg_catalog."C",
    pirus_api character varying(50) COLLATE pg_catalog."C",

    image_file_id int,
    root_path character varying(500) COLLATE pg_catalog."C",
    vm_settings text COLLATE pg_catalog."C",
    ui_form text COLLATE pg_catalog."C",
    ui_icon character varying(255) COLLATE pg_catalog."C",

    CONSTRAINT pipe_pkey PRIMARY KEY (id),
    CONSTRAINT pipe_ukey UNIQUE (name, version)
);
ALTER TABLE public.pipeline OWNER TO pirus;


CREATE TABLE public.job
(
    id serial NOT NULL,
    pipeline_id int,
    name character varying(255) COLLATE pg_catalog."C",
    priority int,

    config text COLLATE pg_catalog."C",
    start_date timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status job_status,

    root_path character varying(500) COLLATE pg_catalog."C",
    progress_value real,
    progress_label character varying(255) COLLATE pg_catalog."C",

    CONSTRAINT job_pkey PRIMARY KEY (id)
);
ALTER TABLE public.job OWNER TO pirus;

CREATE TABLE public.job_file
(
    job_id int NOT NULL,
    file_id int NOT NULL,
    as_input boolean,
    CONSTRAINT job_file_pkey PRIMARY KEY (job_id, file_id)
);
ALTER TABLE public.job_file OWNER TO pirus;


