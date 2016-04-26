
This directory contains command-line utilities for viewing and manipulating taxonomies in the taxonomy database.  There are currently five programs here: `print_csv_taxonomy.py`, `load_taxonomy.py`, `dump_db_taxonomy.py`, `ls_taxonomies.py`, and `search_taxa.py`.  Each of these is described in more detail below.

* [load_taxonomy.py](#load_taxonomypy)
* [print_csv_taxonomy.py](#print_csv_taxonomypy)
* [dump_db_taxonomy.py](#dump_db_taxonomypy)
* [ls_taxonomies.py](#ls_taxonomiespy)
* [search_taxa.py](#search_taxapy)


### load_taxonomy.py

Parses a CSV taxonomy file and loads it into the database.

Processing a CSV taxonomy file requires a configuration file that provides metadata for the taxonomy and defines which columns in the CSV file contain taxonomy information and how they should map to the rank names used in the database.  For a complete example, see the sample configuration file, "taxonomies/example.conf", which also includes extensive comments explaining the configuration file format.

To connect to the taxonomy database, `load_taxonomy.py` also needs a SQLite database file.  By default, `load_taxonomy.py` will look for a file called "database.sqlite", but an alternative database file can be specified using the `-d` option.

After parsing a taxonomy file, `load_taxonomy.py` will, by default, attempt to retrieve citation information for the taxa name strings.  Currently, a two-tiered strategy is used.  Name strings are first checked against Catalog of Life to retrieve name author data, then against the Zoobank database to retrieve any additional citation information.  Name citation resolution can be controlled with the `-l` option.  To use all name citation resolvers (which is also the default), use `-l all`.  To completely disable name citation resolution, use `-l none`.  Individual resolvers can be selected with an integer index.  Currently, 0 = Catalog of Life and 1 = Zoobank.

For large taxonomies, name citation resolution can take a long time.  To speed up the process of loading taxonomies, `load_taxonomy.py` can search for names and citation data in an existing taxonomy, and if citation data are found for a particular name, `load_taxonomy.py` can skip the citation resolving process for that name for a new taxonomy.  That is, once an initial taxonomy is loaded for a group of organisms (birds, for example), the citation data retrieved for the initial taxonomy can be used to speed up the loading process for new taxonomies for the same group (alternative bird taxonomies, in our example).  To enable this feature, use the `-c` option to provide the ID of a comparison taxonomy.  An ID of -1 (the default) disables this feature.

#### Features

There are a few important things to know about how `load_taxonomy.py` works.

First, it is fully generic.  It supports CSV taxonomy files with an arbitrary number of taxa columns, an arbitrary set of included taxonomic ranks, and arbitrary mappings of CSV file column names to taxonomic rank names.

Second, `load_taxonomy.py` also properly handles rows where one or more of the higher taxonomy columns are empty.  This could occur, for instance, if some genera are organized into tribes but others are not, which means that some genera should have a tribe as their parent taxon but others should have the family as their parent taxon.  `load_taxonomy.py` will detect these situations and assign the correct parent/child relationships.

Third, `load_taxonomy.py` automatically tracks tree depth and will assign correct values to the "depth" field for all new entries in the "taxon_concepts" table.

Fourth, given a rank system ID in the configuration file, `load_taxonomy.py` will load the rank information from the taxonomy database and automatically assign the correct rank IDs to all new entries in the "taxon_concepts" table.

Fifth, `load_taxonomy.py` allows the root node of a taxonomy to have a different taxonomy ID from the rest of the taxonomy.  This is required to properly support non-master and non-backbone taxonomies.

Sixth, `load_taxonomy.py` will attempt to link all incoming taxonomies to the MOL backbone taxonomy.  If needed higher-level taxa do not already exist in the database, `load_taxonomy.py` will attempt to create them by referencing the Catalog of Life taxonomy.  If an incoming taxonomy cannot be linked to the MOL backbone taxonomy, the program will abort.

Finally, `load_taxonomy.py` includes extensive checks to avoid creating duplicate records in the taxonomy database tables.  If the given taxonomy already exists in the database (as determined by the taxonomy ID), the program will not make any changes to the taxonomy metadata but will still visit each taxon concept in the taxonomy to see if it needs to be saved to the database.  In general, citations, names, and taxon concepts are not modified if they already exist in the database.

#### Assumptions/limitations

There are at least two assumptions/limitations that might be important (that I am currently aware of!).

First, `load_taxonomy.py` assumes that a taxonomy does not contain multiple taxa with the same name and the same rank.  For example, there cannot be two *different* genera with the same name wthin a given taxonomy.  If a taxonomy *does* contain two genera with the same name, each assigned to a different family, `load_taxonomy.py` will consider the second genus to be the same as the first.  This is strictly required by the International Code of Zoological Nomenclature.  See, for example, Article 52.1, which states, "When two or more taxa are distinguished from each other they must not be denoted by the same name."

However, I have found several generic names in the Jetz et al. taxonomy that do not follow this convention, presumably due to nomenclature that has not yet been updated to reflect phylogenetic knowledge.  It is probably worth discussing how this situation should best be handled since it has the potential to cause confusion for end users.

Second, `load_taxonomy.py` does not currently support unranked clades in a taxonomy.  This feature could be added, but I decided not to spend time on it until the need arises.

#### Examples

Using `load_taxonomy.py` is fairly straightforward.  The following example loads the Jetz et al. taxonomy into the database.

```
./load_taxonomy.py taxonomies/jetz_birds.conf
```

Load the Jetz et al. taxonomy into the database, but do not attempt any names citation resolution.

```
./load_taxonomy.py -l none taxonomies/jetz_birds.conf
```

Load the Jetz et al. taxonomy into the database, but use only the Catalog of Life names citation resolver.

```
./load_taxonomy.py -l 0 taxonomies/jetz_birds.conf
```

Load the BirdLife taxonomy into the database, and check the Jetz et al. taxonomy (ID 2) for names that already have citation data.  Citation resolution will be skipped for these names.

```
./load_taxonomy.py -c 2 taxonomies/birdlife.conf
```


### print_csv_taxonomy.py

This program parses a taxonomy contained in a CSV file and prints it to standard out.  The program prints metadata for the taxonomy (e.g., ID, citation, etc.) along with the tree of included taxa.

Like `load_taxonomy.py`, `print_csv_taxonomy.py` requires a taxonomy configuration file for the input CSV file and a SQLite database file.  (Rank information from the taxonomy database is required for parsing CSV taxonomy files.)  See the documentation for `load_taxonomy.py`, above, for more details about these two files.

By default, print_csv_taxonomy.py will print the taxonomy's full taxa tree.  For large taxonomies, though, it is often more useful to view only a subset of the full taxonomy.  Two options are currently provided to limit the output.  The option `-n NUMTAXA` will cause print_csv_taxonomy.py to only print the first `NUMTAXA` taxa from the taxonomy.  The option `-m MAXDEPTH` will cause print_csv_taxonomy.py to only descend into the taxa tree up to a maximum depth of `MAXDEPTH`.

#### Examples

Parse the Jetz et al. birds taxonomy and print the first 100 taxa.

```
./print_csv_taxonomy.py -n 100 taxonomies/jetz_birds.conf
```

Parse the Jetz et al. bird taxonomy and only print taxa down to the rank of family.

```
./print_csv_taxonomy.py -m 2 taxonomies/jetz_birds.conf
```

The two output-limiting options can be combined.  For, example the following command only descends to the rank of family and only prints the first 20 taxa.

```
./print_csv_taxonomy.py -m 2 -n 20 taxonomies/jetz_birds.conf
```


### dump_db_taxonomy.py

Reads a taxonomy from a database and prints it to the screen.  The output is nearly identical to that produced by `print_csv_taxonomy.py`.  In fact, the output of these two programs can be compared to verify that a database representation of a taxonomy is structurally the same as its CSV representation.

As with the previous two programs, `dump_db_taxonomy.py` requires a SQLite database file in order to connect to a taxonomy database.  See the documentation of `load_taxonomy.py` for more details.

The only required argument is the ID of the taxonomy to load from the database (that is, the value of "taxonomy_id" from the "taxonomies" table).

Like `print_csv_taxonomy.py`, `dump_db_taxonomy.py` also supports the `-n` and `-m` options.  See the documentation for `print_csv_taxonomy.py` for further description of these options.

By default, if the target taxonomy is not the MOL backbone taxonomy, `print_csv_taxonomy.py` will retrieve and display the higher-level taxa that link the root of the target taxonomy to the root of the MOL backbone taxonomy.  To disable this behavior, use the `-g` flag.

#### Examples

Read the taxonomy with ID 1 from the database, but only read the first 100 taxa.

```
./dump_db_taxonomy.py -n 100 1
```

Read the taxonomy with ID 1 from the database, but only traverse 2 levels deep into the taxa tree.

```
./dump_db_taxonomy.py -m 2 1
```


### ls_taxonomies.py

Prints a list of all taxonomies in a taxonomy database, along with some basic information about each taxonomy.

As with the previous programs, `ls_taxonomies.py` requires a SQLite database file in order to connect to a taxonomy database.  See the documentation of `load_taxonomy.py` for more details.

#### Example

List all taxonomies in the database specified by the default database configuration file.

```
./ls_taxonomies.py
```


### search_taxa.py

Searches the taxonomy database for taxon concepts with name strings that match a given search string.  The percent sign ('%') can be used as a wildcard character.

#### Examples

Search the taxonomy database for taxon concepts with the name "Bubo virginianus".

```
./search_taxa.py "Bubo virginianus"
```

Search the taxonomy database for taxon concepts with names that begin with "Bubo".

```
./search_taxa.py "Bubo%"
```

