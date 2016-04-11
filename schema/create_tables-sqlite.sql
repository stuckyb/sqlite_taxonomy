-- This is derived from create_tables.sql, which was written for PostgreSQL.
-- This version was modified to work with SQLite.
--
-- The changes are as follows:
-- 1. UUID columns were changed to integer columns.  If UUIDs are
--    desired, the best solution seems to be to use the "blob" type.
--    See http://wtanaka.com/node/8106.
-- 2. SQLite doesn't have an enum type, so this is simulated using a
--    separate table for the enum values and a foreign key constraint
--    in the table(s) that use the enum "type".
-- 3. The "copy" statements were replaced with ".import" statements.
-- 4. Removed the index for trigram matching.
-- 5. Removed the indexes for primary keys, as these are created automatically.
--    (This should be the case in Postgres, too, I think.)



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
   ranksys_id  integer PRIMARY KEY,
   namestr     text    ,
   description text
)   ;
-- Note the foreign key constraint: if a rank system is deleted, we should automatically
-- delete its component ranks.
create table "ranks" (
   rank_id            integer PRIMARY KEY,
   ranksys_id         integer REFERENCES rank_systems (ranksys_id) ON DELETE CASCADE,
   namestr            text    ,
   nearest_parent_id  integer ,
   obligate_parent_id integer
)   ;
create table "citations" (
   citation_id   integer PRIMARY KEY,
   citationstr   text            ,
   URL           text            ,
   DOI           text            ,
   authordisplay text
)   ;
-- Names are allowed to exist without citations, so if a referenced citation is deleted,
-- just set the citation_id value to NULL.
create table "names" (
   name_id     integer PRIMARY KEY	,
   namestr     text			,
   citation_id integer REFERENCES citations (citation_id) ON DELETE SET NULL
)   ;
create table "name_spellings" (
   name_id integer REFERENCES names (name_id) ON DELETE CASCADE,
   spelling text    
)   ;
-- The taxonomies table could also be considered for a foreign key constraint on
-- root_tc_id.  However, this would create circular foreign key constraints with
-- the taxon_concepts table, and it probably makes more sense to enforce the
-- constraint on taxon_concepts, not taxonomies.
create table "taxonomies" (
   taxonomy_id integer PRIMARY KEY,
   name        text    ,
   ismaster    boolean ,
   root_tc_id  integer ,
   citation_id integer REFERENCES citations (citation_id) ON DELETE SET NULL
)   ;
-- Note the foreign key constraint.  We should be able to delete an entire taxonomy
-- simply by deleting the metadata entry in the taxonomies table.  This will cause
-- a cascaded delete that deletes all of the child taxon concepts, names_to_taxonconcepts
-- entries, and tc_relationships entries.  Names and citations will not be automatically
-- deleted because they might be used by a different taxonomy.
create table "taxon_concepts" (
   tc_id       integer PRIMARY KEY,
   parent_id   integer          ,
   taxonomy_id integer REFERENCES taxonomies (taxonomy_id) ON DELETE CASCADE,
   rank_id     integer REFERENCES ranks (rank_id)         ,
   depth       integer          ,
   sort_order  integer DEFAULT 0
)   ;
-- Create an enum "type" to record the status of a taxonomic name.
CREATE table validity_enum (
   value text PRIMARY KEY
);
INSERT INTO validity_enum VALUES
   ('valid'), ('invalid-synonym'), ('invalid-homonym'), ('invalid-unavailable'),
   ('invalid-misapplied'), ('invalid-other');
-- Make sure that the prefix/postfix always have a default value of '' so that
-- queries don't have to worry about handling NULL values.  Also set the default
-- value of validity to 'valid'.  Finally, if either the referenced name or
-- taxon concept is deleted, automaticaly delete the relationship connecting them.
create table "names_to_taxonconcepts" (
   tc_id integer REFERENCES taxon_concepts (tc_id) ON DELETE CASCADE,
   name_id integer REFERENCES names (name_id) ON DELETE CASCADE     ,
   validity text REFERENCES validity_enum (value) DEFAULT 'valid'   ,
   authordisp_prefix text DEFAULT '' ,
   authordisp_postfix text DEFAULT ''
)   ;
create table "tc_relationships" (
   master_tc_id integer REFERENCES taxon_concepts (tc_id) ON DELETE CASCADE,
   alt_tc_id integer REFERENCES taxon_concepts (tc_id) ON DELETE CASCADE   ,
   relationshiptype text    
)   ;


-- Load the row data for the "rank_systems" and "ranks" tables by
-- copying them directly from the source CSV files.  Note that the
-- CSV files must not include header rows.
-- These must be run from the SQLite command shell.
.separator ','
.import schema/rank_systems.csv rank_systems
.import schema/mol_ranks.csv ranks


-- Set up the minimal pieces needed for the backbone taxonomy.
-- The backbone taxonomy begins with a single top-level taxon
-- concept, the unranked clade "Eukaryota".  The following INSERT
-- commands create the taxonomy definition along with the root
-- taxon concept, name, and citation.
INSERT INTO citations
    (citation_id, citationstr, url, doi, authordisplay)
    VALUES (1, '', '', '');
INSERT INTO taxonomies
    (taxonomy_id, name, ismaster, root_tc_id, citation_id)
    VALUES (1, 'MOL backbone', true, 1, 1);
INSERT INTO citations
    (citation_id, citationstr, url, doi, authordisplay)
    VALUES (2,
	'Chatton, É. 1925. Pansporella perplexa: amoebiens à spores protégées parasite de daphnies: réflexions sur la biologie et la phylogénie des protozoaires. Annales des Sciences Naturelles, séries Botanique et Zoologie (10) 8: 1–84.',
	null, null, 'Chatton 1925');
-- Note that the ID number 0 is intended to act as a null ID.
INSERT INTO taxon_concepts
    (tc_id, parent_id, taxonomy_id, rank_id, depth, sort_order)
    VALUES (1, 0, 1, 0, 0, 0);
INSERT INTO names
    (name_id, namestr, citation_id)
    VALUES (1, 'Eukaryota', 2);
INSERT INTO names_to_taxonconcepts
    (tc_id, name_id, validity, authordisp_prefix, authordisp_postfix)
    VALUES (1, 1, 'valid', '', '');


-- Finally, create indexes to optimize table search operations.

-- Create an index for taxon concept names.
CREATE INDEX names_namestr_idx ON names (namestr);

-- Create an index for name validity.
CREATE INDEX names_to_taxonconcepts_validity_idx ON names_to_taxonconcepts (validity);

-- Create indexes for the ID columns of several important tables to speed up
-- common JOIN operations.
CREATE INDEX names_to_taxonconcepts_tcid_nameid_idx ON names_to_taxonconcepts (tc_id, name_id);
CREATE INDEX names_to_taxonconcepts_nameid_idx ON names_to_taxonconcepts (name_id);

