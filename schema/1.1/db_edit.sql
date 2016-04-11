
CREATE TYPE validity_enum AS ENUM ('valid', 'invalid-synonym', 'invalid-homonym', 'invalid-unavailable', 'invalid-misapplied', 'invalid-other');

ALTER TABLE names_to_taxonconcepts ADD COLUMN validity validity_enum;

CREATE INDEX names_to_taxonconcepts_validity ON names_to_taxonconcepts USING BTREE(validity);

ALTER TABLE names_to_taxonconcepts ALTER validity SET DEFAULT 'valid';

UPDATE names_to_taxonconcepts SET validity = 'valid' WHERE preferred = 't';

UPDATE names_to_taxonconcepts SET validity = 'invalid-synonym' WHERE preferred = 'f';

#ALTER TABLE names_to_taxonconcepts DROP column preferred CASCADE;

