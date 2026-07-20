-- Tables required by the Go services' repositories and startup seeds
-- (user-service: roles/users/groups/invitations/password_policies;
--  media-service: media_files; notification-service: notification_configs/logs).
--
-- WHY THIS EXISTS: these tables are NOT in database/schema.sql. They were
-- created by the original Java services' Flyway migrations (Feb 2026) and the
-- docker-compose stack still runs against that old volume; the Go port has no
-- GORM AutoMigrate, so a FRESH database needs this DDL. Extracted with
-- pg_dump --schema-only from the working compose athena_db (2026-07-20).

\restrict JKQCtSM1djVQnCg3lH9XWWsTaOeZtCczXDpads6Ip3jmytekcWjrTEacLWdtlZB

CREATE TABLE public.group_roles (
    group_id bigint NOT NULL,
    role_id bigint NOT NULL
);

CREATE TABLE public.invitation_groups (
    invitation_id bigint NOT NULL,
    group_id bigint NOT NULL
);

CREATE TABLE public.invitation_roles (
    invitation_id bigint NOT NULL,
    role_id bigint NOT NULL
);

CREATE TABLE public.invitations (
    id bigint NOT NULL,
    token character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    expiry_date timestamp without time zone NOT NULL,
    used boolean DEFAULT false NOT NULL
);

CREATE SEQUENCE public.invitations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.invitations_id_seq OWNED BY public.invitations.id;

CREATE TABLE public.media_files (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    customer_id bigint,
    category character varying(50) NOT NULL,
    media_type character varying(50) NOT NULL,
    original_filename character varying(500) NOT NULL,
    stored_filename character varying(500) NOT NULL,
    content_type character varying(200) NOT NULL,
    file_size bigint,
    uploaded_by character varying(200),
    description text,
    status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    reference_id uuid,
    tags character varying(500),
    is_public boolean DEFAULT false NOT NULL,
    thumbnail character varying(255),
    service_name character varying(255),
    channel character varying(255)
);

CREATE TABLE public.notification_configs (
    id bigint NOT NULL,
    type character varying(20) NOT NULL,
    provider character varying(50),
    host character varying(255),
    port integer,
    username character varying(255),
    password character varying(255),
    from_address character varying(255),
    api_key character varying(255),
    api_secret character varying(255),
    sender_id character varying(50),
    enabled boolean DEFAULT false NOT NULL
);

CREATE SEQUENCE public.notification_configs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.notification_configs_id_seq OWNED BY public.notification_configs.id;

CREATE TABLE public.notification_logs (
    id bigint NOT NULL,
    service_name character varying(100) NOT NULL,
    type character varying(20) NOT NULL,
    recipient character varying(255) NOT NULL,
    subject character varying(500),
    body text,
    status character varying(20) NOT NULL,
    error_message text,
    sent_at timestamp without time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE public.notification_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.notification_logs_id_seq OWNED BY public.notification_logs.id;

CREATE TABLE public.password_policies (
    id bigint NOT NULL,
    min_length integer DEFAULT 8 NOT NULL,
    require_uppercase boolean DEFAULT true NOT NULL,
    require_lowercase boolean DEFAULT true NOT NULL,
    require_numbers boolean DEFAULT true NOT NULL,
    require_special_chars boolean DEFAULT false NOT NULL,
    expiration_days integer DEFAULT 90 NOT NULL,
    special_chars character varying(100)
);

CREATE SEQUENCE public.password_policies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.password_policies_id_seq OWNED BY public.password_policies.id;

CREATE TABLE public.roles (
    id bigint NOT NULL,
    name character varying(100) NOT NULL,
    description character varying(255)
);

CREATE SEQUENCE public.roles_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;

CREATE TABLE public.user_group_members (
    user_id bigint NOT NULL,
    group_id bigint NOT NULL
);

CREATE TABLE public.user_groups (
    id bigint NOT NULL,
    name character varying(100) NOT NULL,
    description character varying(255)
);

CREATE SEQUENCE public.user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.user_groups_id_seq OWNED BY public.user_groups.id;

CREATE TABLE public.user_roles (
    user_id bigint NOT NULL,
    role_id bigint NOT NULL
);

CREATE TABLE public.users (
    id bigint NOT NULL,
    username character varying(255) NOT NULL,
    password character varying(255) NOT NULL,
    first_name character varying(100),
    last_name character varying(100),
    email character varying(255),
    status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL
);

CREATE SEQUENCE public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;

ALTER TABLE ONLY public.invitations ALTER COLUMN id SET DEFAULT nextval('public.invitations_id_seq'::regclass);

ALTER TABLE ONLY public.notification_configs ALTER COLUMN id SET DEFAULT nextval('public.notification_configs_id_seq'::regclass);

ALTER TABLE ONLY public.notification_logs ALTER COLUMN id SET DEFAULT nextval('public.notification_logs_id_seq'::regclass);

ALTER TABLE ONLY public.password_policies ALTER COLUMN id SET DEFAULT nextval('public.password_policies_id_seq'::regclass);

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);

ALTER TABLE ONLY public.user_groups ALTER COLUMN id SET DEFAULT nextval('public.user_groups_id_seq'::regclass);

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);

ALTER TABLE ONLY public.group_roles
    ADD CONSTRAINT group_roles_pkey PRIMARY KEY (group_id, role_id);

ALTER TABLE ONLY public.invitation_groups
    ADD CONSTRAINT invitation_groups_pkey PRIMARY KEY (invitation_id, group_id);

ALTER TABLE ONLY public.invitation_roles
    ADD CONSTRAINT invitation_roles_pkey PRIMARY KEY (invitation_id, role_id);

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_token_key UNIQUE (token);

ALTER TABLE ONLY public.media_files
    ADD CONSTRAINT media_files_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.notification_configs
    ADD CONSTRAINT notification_configs_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.notification_configs
    ADD CONSTRAINT notification_configs_type_key UNIQUE (type);

ALTER TABLE ONLY public.notification_logs
    ADD CONSTRAINT notification_logs_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.password_policies
    ADD CONSTRAINT password_policies_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_name_key UNIQUE (name);

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.user_group_members
    ADD CONSTRAINT user_group_members_pkey PRIMARY KEY (user_id, group_id);

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT user_groups_name_key UNIQUE (name);

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT user_groups_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_pkey PRIMARY KEY (user_id, role_id);

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);

CREATE INDEX idx_invitations_token ON public.invitations USING btree (token);

CREATE INDEX idx_media_files_category ON public.media_files USING btree (category);

CREATE INDEX idx_media_files_created_at ON public.media_files USING btree (created_at);

CREATE INDEX idx_media_files_customer_id ON public.media_files USING btree (customer_id);

CREATE INDEX idx_media_files_reference_id ON public.media_files USING btree (reference_id);

CREATE INDEX idx_media_files_status ON public.media_files USING btree (status);

CREATE INDEX idx_media_files_tags ON public.media_files USING btree (tags);

CREATE INDEX idx_notification_logs_recipient ON public.notification_logs USING btree (recipient);

CREATE INDEX idx_notification_logs_sent_at ON public.notification_logs USING btree (sent_at);

CREATE INDEX idx_notification_logs_service_name ON public.notification_logs USING btree (service_name);

CREATE INDEX idx_users_username ON public.users USING btree (username);

ALTER TABLE ONLY public.group_roles
    ADD CONSTRAINT group_roles_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.user_groups(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.group_roles
    ADD CONSTRAINT group_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.invitation_groups
    ADD CONSTRAINT invitation_groups_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.user_groups(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.invitation_groups
    ADD CONSTRAINT invitation_groups_invitation_id_fkey FOREIGN KEY (invitation_id) REFERENCES public.invitations(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.invitation_roles
    ADD CONSTRAINT invitation_roles_invitation_id_fkey FOREIGN KEY (invitation_id) REFERENCES public.invitations(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.invitation_roles
    ADD CONSTRAINT invitation_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.user_group_members
    ADD CONSTRAINT user_group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.user_groups(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.user_group_members
    ADD CONSTRAINT user_group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

\unrestrict JKQCtSM1djVQnCg3lH9XWWsTaOeZtCczXDpads6Ip3jmytekcWjrTEacLWdtlZB

