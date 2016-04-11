-- Creates all tables for the MOL taxonomy database schema.
-- This code was initially generated by Parse::SQL::Dia version 0.23,
-- with substantial SQL customizations and additions by hand afterwards.

-- get_constraints_drop 

-- get_permissions_drop 

-- get_view_drop

-- get_schema_drop
drop table "names_to_taxonconcepts";
drop table "tc_relationships";
drop table "taxon_concepts";
drop table "taxonomies";
drop table "name_spellings";
drop table "names";
drop table "citations";
drop table "ranks";
drop table "rank_systems";

-- get_smallpackage_pre_sql 

-- get_schema_create
create table "rank_systems" (
   ranksys_id  integer ,
   namestr     text    ,
   description text    ,
   CONSTRAINT pk_rank_systems PRIMARY KEY (ranksys_id)
)   ;
-- Note the foreign key constraint: if a rank system is deleted, we should automatically
-- delete its component ranks.
create table "ranks" (
   rank_id            integer ,
   ranksys_id         integer REFERENCES rank_systems (ranksys_id) ON DELETE CASCADE,
   namestr            text    ,
   nearest_parent_id  integer ,
   obligate_parent_id integer ,
   CONSTRAINT pk_ranks PRIMARY KEY (rank_id)
)   ;
create table "citations" (
   citation_id   uuid DEFAULT uuid_generate_v1mc(),
   citationstr   text            ,
   URL           text            ,
   DOI           text            ,
   authordisplay text            ,
   CONSTRAINT pk_citations PRIMARY KEY (citation_id)
)   ;
-- Names are allowed to exist without citations, so if a referenced citation is deleted,
-- just set the citation_id value to NULL.
create table "names" (
   name_id     uuid DEFAULT uuid_generate_v1mc()      ,
   namestr     text            ,
   citation_id uuid REFERENCES citations (citation_id) ON DELETE SET NULL,
   CONSTRAINT pk_names PRIMARY KEY (name_id)
)   ;
create table "name_spellings" (
   name_id uuid REFERENCES names (name_id) ON DELETE CASCADE,
   spelling text    
)   ;
-- The taxonomies table could also be considered for a foreign key constraint on
-- root_tc_id.  However, this would create circular foreign key constraints with
-- the taxon_concepts table, and it probably makes more sense to enforce the
-- constraint on taxon_concepts, not taxonomies.
create table "taxonomies" (
   taxonomy_id integer ,
   name        text    ,
   ismaster    boolean ,
   root_tc_id  uuid    ,
   citation_id uuid REFERENCES citations (citation_id) ON DELETE SET NULL,
   CONSTRAINT pk_taxonomies PRIMARY KEY (taxonomy_id)
)   ;
-- Note the foreign key constraint.  We should be able to delete an entire taxonomy
-- simply by deleting the metadata entry in the taxonomies table.  This will cause
-- a cascaded delete that deletes all of the child taxon concepts, names_to_taxonconcepts
-- entries, and tc_relationships entries.  Names and citations will not be automatically
-- deleted because they might be used by a different taxonomy.
create table "taxon_concepts" (
   tc_id       uuid DEFAULT uuid_generate_v1mc(),
   parent_id   uuid             ,
   taxonomy_id integer REFERENCES taxonomies (taxonomy_id) ON DELETE CASCADE,
   rank_id     integer REFERENCES ranks (rank_id)         ,
   depth       integer          ,
   sort_order  integer DEFAULT 0,
   CONSTRAINT pk_taxon_concepts PRIMARY KEY (tc_id)
)   ;
-- Make sure that the prefix/postfix always have a default value of '' so that
-- queries don't have to worry about handling NULL values.  Also set the default
-- value of preferred to FALSE.  Finally, if either the referenced name or taxon
-- concept is deleted, automaticaly delete the relationship connecting them.
create table "names_to_taxonconcepts" (
   tc_id uuid REFERENCES taxon_concepts (tc_id) ON DELETE CASCADE,
   name_id uuid REFERENCES names (name_id) ON DELETE CASCADE     ,
   preferred boolean DEFAULT FALSE   ,
   authordisp_prefix text DEFAULT '' ,
   authordisp_postfix text DEFAULT ''
)   ;
create table "tc_relationships" (
   master_tc_id uuid REFERENCES taxon_concepts (tc_id) ON DELETE CASCADE,
   alt_tc_id uuid REFERENCES taxon_concepts (tc_id) ON DELETE CASCADE   ,
   relationshiptype text    
)   ;


-- Load the row data for the "rank_systems" and "ranks" tables by
-- copying them directly from the source CSV files.
copy "rank_systems" from 'rank_systems.csv' delimiter ',' csv header;
copy "ranks" from 'mol_ranks.csv' delimiter ',' csv header;


-- Set up the minimal pieces needed for the MOL backbone taxonomy.
-- The MOL backbone taxonomy begins with a single top-level taxon
-- concept, the unranked clade "Eukaryota".  The following INSERT
-- commands create the taxonomy definition and citation along with
-- the root taxon concept, name, and citation.
INSERT INTO citations
    (citation_id, citationstr, url, doi, authordisplay)
    VALUES ('0b6914f8-12e4-11e5-94b2-c3fe9c93646e',
	'Jetz, W., J.M. McPherson, R.P. Guralnick. 2012. Integrating biodiversity distribution knowledge: toward a global map of life. Trends in Ecology and Evolution 27: 151-159.',
	'http://www.sciencedirect.com/science/article/pii/S0169534711002679',
	'doi:10.1016/j.tree.2011.09.007', 'Jetz et al. 2012');
INSERT INTO taxonomies
    (taxonomy_id, name, ismaster, root_tc_id, citation_id)
    VALUES (1, 'MOL backbone', true, 'a025e068-12e3-11e5-94b1-37903a5f6c8a',
	'0b6914f8-12e4-11e5-94b2-c3fe9c93646e');
INSERT INTO citations
    (citation_id, citationstr, url, doi, authordisplay)
    VALUES ('668dc144-12e4-11e5-94b3-0757aa1b6825',
	'Chatton, É. 1925. Pansporella perplexa: amoebiens à spores protégées parasite de daphnies: réflexions sur la biologie et la phylogénie des protozoaires. Annales des Sciences Naturelles, séries Botanique et Zoologie (10) 8: 1–84.',
	null, null, 'Chatton 1925');
-- Note that the UUID '00000000-0000-0000-0000-000000000000' is the "nil" UUID constant
-- as returned by the uuid-osp module function uuid_nil().
INSERT INTO taxon_concepts
    (tc_id, parent_id, taxonomy_id, rank_id, depth, sort_order)
    VALUES ('a025e068-12e3-11e5-94b1-37903a5f6c8a', '00000000-0000-0000-0000-000000000000', 1, 0, 0, 0);
INSERT INTO names
    (name_id, namestr, citation_id)
    VALUES ('9fafe362-12e4-11e5-94b5-3f5794f4f8a3', 'Eukaryota', '668dc144-12e4-11e5-94b3-0757aa1b6825');
INSERT INTO names_to_taxonconcepts
    (tc_id, name_id, preferred, authordisp_prefix, authordisp_postfix)
    VALUES ('a025e068-12e3-11e5-94b1-37903a5f6c8a', '9fafe362-12e4-11e5-94b5-3f5794f4f8a3', TRUE, '', '');


-- Finally, create indexes to optimize table search operations.

-- Create a standard text index for taxon concept names.  We explicitly tell
-- Postgres not to use the default collation, which is often language-specific
-- (a common default for GNU/Linux is "en_US.UTF-8").  Instead, we want the
-- "C" collation for fast string comparison and LIKE optimization.
CREATE INDEX namestr_idx ON names (namestr text_pattern_ops);

-- Create an index for q-gram approximate string matching of names.
CREATE INDEX namestr_trgm_idx ON names USING gist (namestr gist_trgm_ops);

-- Create indexes for the ID columns of several important tables to speed up
-- common JOIN operations.
CREATE INDEX tc_id_idx ON taxon_concepts (tc_id);
CREATE INDEX tcid_nameid_idx ON names_to_taxonconcepts (tc_id, name_id);
CREATE INDEX nameid_idx ON names_to_taxonconcepts (name_id);
CREATE INDEX name_id_idx ON names (name_id);
CREATE INDEX citation_id_idx ON citations (citation_id);

