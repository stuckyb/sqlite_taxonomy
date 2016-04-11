from abc import ABCMeta, abstractmethod


class Matcher:
    """
    An abstract base class for approximate string matching implementations.
    """
    __metaclass__ = ABCMeta

    def __init__(self, dbtablename=None, dbcolname=None, dbcursor=None):
        """
        Initializes the Matcher and optionally specifies the database table
        name and column name to use as the search "dictionary", and a cursor
        object to use for database queries.
        """
        self.setDBTableInfo(dbtablename, dbcolname)
        self.setDBCursor(dbcursor)

    def setDBTableInfo(self, dbtablename, dbcolname):
        """
        Sets the database table name and column name to use as the "dictionary"
        of valid strings for approximate string matching.
        """
        self.dbtable = dbtablename
        self.dbcol = dbcolname

    def setDBCursor(self, dbcursor):
        """
        Sets the database cursor object to use for running database queries.
        """
        self.dbcursor = dbcursor

    @abstractmethod
    def match(self, searchstr):
        """
        Do an approximate string matching search of the valid strings dictionary
        (i.e., the specified database table and column).  This method should be
        implemented by child classes.
        """
        pass


class ExactMatcher(Matcher):
    """
    Implements exact string comparison using the SQL "=" operator.
    """
    def match(self, searchstr):
        query = """SELECT {0} FROM {1} n
            WHERE n.{0}=%s""".format(self.dbcol, self.dbtable)
        #print query
    
        #print self.dbcursor.mogrify(query, (searchstr,))
        self.dbcursor.execute(query, (searchstr,))
        results = self.dbcursor.fetchall()
    
        return [result[0] for result in results]


class QgramMatcher(Matcher):
    """
    Implements approximate string matching using the q-gram comparison method,
    where q=3 (i.e., trigrams).  By default, a similarity score cutoff of 0.4
    is used to limit the search result sets.
    """
    def __init__(self, dbtablename=None, dbcolname=None, dbcursor=None):
        # Set the default similarity score cutoff.
        self.simcutoff = 0.4

        # Call the superclass initializer.
        Matcher.__init__(self, dbtablename, dbcolname, dbcursor)

    def setDBCursor(self, dbcursor):
        # Call the superclass method.
        Matcher.setDBCursor(self, dbcursor)

        # If we were provided with a cursor instance, be sure that the correct
        # similarity score threshold is set.
        if self.dbcursor != None:
            self.setSimilarityCutoff(self.simcutoff)

    def getSimilarityCutoff(self):
        """
        Returns the current similarity score cutoff for limiting search result sets.
        """
        return self.simcutoff

    def setSimilarityCutoff(self, similarity_cutoff):
        """
        Sets the similarity score threshold to use when performing q-gram approximate
        matching.  Similarity scores range from 0 (no q-grams in common) to 1 (a perfect
        match).  Strings with similarity scores less than the specified cutoff will not
        be returned when performing a search.
        """
        self.simcutoff = similarity_cutoff

        # Set the similarity threshold for the database session.  Note that if we do
        # not yet have a valid cursor object, this method will be called again when
        # a cursor object is provided.
        if self.dbcursor != None:
            query = 'SELECT set_limit(%s)'
            self.dbcursor.execute(query, (self.simcutoff,))

    def match(self, searchstr):
        query = """SELECT {0}, similarity({0}, %s) FROM {1} n
            WHERE n.{0} %% %s""".format(self.dbcol, self.dbtable)
        #print query
    
        #print self.dbcursor.mogrify(query, (searchstr, searchstr))
        self.dbcursor.execute(query, (searchstr, searchstr))
        results = self.dbcursor.fetchall()
    
        return [result[0] for result in results]


class DLMatcher(Matcher):
    """
    Implements approximate string matching by searching for strings within a
    specific Damerau-Levenshtein distance (1 by default) of a target string.
    """
    # Define "constants" for specifying alternative search algorithms.
    METHOD_FULLNHOOD = 0
    METHOD_WCNHOOD = 1

    def __init__(self, dbtablename=None, dbcolname=None, dbcursor=None):
        # Generate the default alphabet.
        self.alpha = [chr(val) for val in range(ord('a'), ord('a') + 26)]

        # Set the default D-L distance limit.
        self.k = 1

        # Set the default search algorithm.
        self.setSearchMethod(DLMatcher.METHOD_FULLNHOOD)

        # Call the superclass initializer.
        Matcher.__init__(self, dbtablename, dbcolname, dbcursor)

    def getSearchMethod(self):
        """
        Returns the current search algorithm for D-L matching.  See the documentation
        for setSearchMethod() for more details.
        """
        return self.searchmethod

    def setSearchMethod(self, method):
        """
        Sets the specific search algorithm to use for D-L matching.  The options
        are defined as class "constants".  METHOD_FULLNHOOD (the default) uses
        exact SQL string matching to search the full D-L k-neighborhood.
        METHOD_WCNHOOD uses a reduced "wildcard" neighborhood with string pattern
        matching and is only available for k=1.
        """
        self.searchmethod = method

        if self.searchmethod == DLMatcher.METHOD_FULLNHOOD:
            self.match = self._matchFullNhood
        elif self.searchmethod == DLMatcher.METHOD_WCNHOOD:
            self.match = self._matchWCNhood

    def getDLDistance(self):
        """
        Returns the current maximum D-L distance (k) for string matching.
        """
        return self.k

    def setDLDistance(self, distance):
        """
        Sets the maximum D-L distance (k) between two strings that is required
        to consider the strings a match.  Values greater than 1 increase the
        "fuzziness" of the matching, but substantially increase search times.
        Currently, k > 1 is only implemented for full neighborhood matching
        (METHOD_FULLNHOOD).  If "wildcard" neighborhood matching is used
        (METHOD_WCNHOOD), k is always 1.
        """
        self.k = distance

    def generateNeighborhood(self, searchstr, dist=1):
        """
        Generates the Damerau-Levenshtein neighborhood of a search string
        where k = dist.  Except for a simple optimization when generating the
        k = 1 neighborhood, this implementation does not attempt to check for
        and avoid duplicate strings in the final neighborhood.  See Boytsov 2011
        for why checking for duplicates is usually not a good idea.
        """
        # If k >= 2, we don't need to explicitly include the original search
        # string because it will automatically be recovered by at least some
        # sequences of edit operations.  If k < 2, we need to explicitly include
        # the original search string.
        if dist < 2:
            nhood = [searchstr]
        else:
            nhood = []
    
        nhood.extend(self._generateNeighborhood(searchstr, dist))
    
        # As a final step, apply the proper casing to each neighborhood string so
        # that it will work with a dictionary of scientific names.
        nhood = [neighbor[0].upper() + neighbor[1:] for neighbor in nhood]
    
        return nhood
    
    def _generateNeighborhood(self, searchstr, dist=1):
        """
        Internal, recursive method for generating the Damerau-Levenshtein
        neighborhood of a search string where k = dist.
        """
        nhood = self.generateK1Neighborhood(searchstr)
    
        if dist > 1:
            nextnhood = []
            for neighbor in nhood:
                nextnhood.extend(self.generateNeighborhood(neighbor, dist - 1))
    
            nhood.extend(nextnhood)
    
        return nhood
        
    def generateK1Neighborhood(self, searchstr):
        """
        Generates the k=1 Damerau-Levenshtein neighborhood of a search string.
        If a 26-character alphabet is used, and if strlen = the length of the
        search string, then the algorithm implemented here will generate: strlen
        strings from deletion operations, (strlen + 1) * 26 strings from insertions,
        strlen * 25 strings from substitutions, and strlen - 1 strings from
        transpositions.  The total k=1 neighborhood size, then, is 53 * strlen + 25.
        Each additional character of the search string adds 53 strings to the k=1
        neighborhood.  (Note that this formula is exact only when strlen > 1).
        """
        searchstr = searchstr.lower()
        strlen = len(searchstr)
        nhood = []
    
        # Deletions.  In this case, if the head and tail deletions are rewritten as
        # simpler statements, they only run about 1.8x faster, in my testing, so I
        # retain them inside the loop for simplicity.
        if strlen > 1:
            for pos in range(strlen):
                nhood.append(searchstr[:pos] + searchstr[pos+1:])
    
        # Insertions.  The head and tail insertions are done outside the inner loop because
        # the simpler statements without indexing run about 6x faster, in my testing.
        for char in self.alpha:
            nhood.append(char + searchstr)
            for pos in range(1, strlen):
                nhood.append(searchstr[:pos] + char + searchstr[pos:])
            nhood.append(searchstr + char)
    
        # Substitutions.  If the head and tail substitutions are rewritten as simpler
        # statements, they only run about 1.5x faster, in my testing, so I retain them
        # inside the loop for simplicity.
        for char in self.alpha:
            for pos in range(0, strlen):
                if char != searchstr[pos]:
                    nhood.append(searchstr[:pos] + char + searchstr[pos+1:])
    
        # Transpositions.
        for pos in range(strlen - 1):
            nhood.append(searchstr[:pos] + searchstr[pos+1] + searchstr[pos] + searchstr[pos+2:])
    
        return nhood

    def generateK1WCNeighborhood(self, searchstr):
        """
        TODO: Properly handle search strings that include the "_" character.  This
        character should never appear in valid scientific names, though.
    
        Generates the k=1 Damerau-Levenshtein "wildcard" neighborhood of a search
        string.  This function is conceptually the same as generateK1Neighborhood(),
        except that all insertions and substitutions at a single position are
        represented by the wildcard character "_" instead of by actually generating
        all of the strings.  The results are returned as a tuple where the first
        element is the neighborhood members that should be matched with an exact
        search (i.e., that contain no wildcard characters), and the second element is
        all neighboorhood elements containing a wildcard.  If a 26-character alphabet
        is used, and if strlen = the length of the search string, then this algorithm
        will generate: strlen strings from deletion operations, strlen + 1 strings
        from insertions, strlen strings from substitutions, and strlen - 1 strings
        from transpositions.  The total k=1 neighborhood size, then, is 4 * strlen.
        Each additional character of the search string adds 4 strings to the k=1
        neighborhood.  (Note that this formula is exact only when strlen > 1).
        More specifically, the final neighborhood will contain 2 * strlen - 1
        strings for exact matching and 2 * strlen + 1 strings with wildcards.
        """
        searchstr = searchstr.lower()
        strlen = len(searchstr)
        exact_nhood = []
        wc_nhood = []
    
        # Deletions.  In this case, if the head and tail deletions are rewritten as
        # simpler statements, they only run about 1.8x faster, in my testing, so I
        # retain them inside the loop for simplicity.
        if strlen > 1:
            for pos in range(strlen):
                exact_nhood.append(searchstr[:pos] + searchstr[pos+1:])
    
        # Insertions.  The head and tail insertions are done outside the inner loop because
        # the simpler statements without indexing run about 6x faster, in my testing.
        wc_nhood.append('_' + searchstr)
        for pos in range(1, strlen):
            wc_nhood.append(searchstr[:pos] + '_' + searchstr[pos:])
        wc_nhood.append(searchstr + '_')
    
        # Substitutions.  If the head and tail substitutions are rewritten as simpler
        # statements, they run about 1.5x faster, in my testing.  This is a relatively
        # minor gain, so I retain them inside the loop for simplicity.
        for pos in range(0, strlen):
            wc_nhood.append(searchstr[:pos] + '_' + searchstr[pos+1:])
    
        # Transpositions.
        for pos in range(strlen - 1):
            exact_nhood.append(searchstr[:pos] + searchstr[pos+1] + searchstr[pos]
                    + searchstr[pos+2:])
    
        # As a final step, apply the proper casing to each neighborhood string so
        # that it will work with a dictionary of scientific names.
        exact_nhood = [neighbor[0].upper() + neighbor[1:] for neighbor in exact_nhood]
        wc_nhood = [neighbor[0].upper() + neighbor[1:] for neighbor in wc_nhood]
    
        return (exact_nhood, wc_nhood)
    
    def generatePartialK1WCNeighborhood(self, searchstr):
        """
        TODO: Properly handle search strings that include the "_" character.  This
        character should never appear in valid scientific names, though.
        TODO: Make sure the original search string is included in the neighborhood.
    
        Generates a "modified" k=1 Damerau-Levenshtein "wildcard" neighborhood of a
        search string.  This function is conceptually the same as
        generateK1WCNeighborhood(), except that leading character insertions and
        substitutions use the full alphabet (rather than a wildcard) so that standard
        B-tree database indexes can be efficiently exploited for searching.  The
        results are returned in the same format as generateK1WCNeighborhood().  If a
        26-character alphabet is used, and if strlen = the length of the search
        string, then the algorithm implemented here will generate: strlen strings
        from deletion operations, 26 + strlen strings from insertions,
        25 + (strlen - 1) strings from substitutions, and strlen - 1 strings from
        transpositions.  The total k=1 neighborhood size, then, is 4 * strlen + 49.
        Each additional character of the search string adds 4 strings to the k=1
        neighborhood.  (Note that this formula is exact only when strlen > 1).
        More specifically, the final neighborhood will contain 2 * strlen + 50
        strings for exact matching and 2 * strlen - 1 strings with wildcards.
        """
        searchstr = searchstr.lower()
        strlen = len(searchstr)
        exact_nhood = []
        wc_nhood = []
    
        # Deletions.  In this case, if the head and tail deletions are rewritten as
        # simpler statements, they only run about 1.8x faster, in my testing, so I
        # retain them inside the loop for simplicity.
        if strlen > 1:
            for pos in range(strlen):
                exact_nhood.append(searchstr[:pos] + searchstr[pos+1:])
    
        # Insertions.  The head and tail insertions are done outside the inner loop because
        # the simpler statements without indexing run about 6x faster, in my testing.
        # For the leading character, generate all possibilities.
        for char in self.alpha:
            exact_nhood.append(char + searchstr)
        # For the remaining positions, use the wildcard character.
        for pos in range(1, strlen):
            wc_nhood.append(searchstr[:pos] + '_' + searchstr[pos:])
        wc_nhood.append(searchstr + '_')
    
        # Substitutions.  If the head and tail substitutions are rewritten as simpler
        # statements, they run about 1.5x faster, in my testing.  This is a relatively
        # minor gain, so I retain the tail substitution inside the loop for simplicity.
        # For the leading character, generate all possibilities.
        for char in self.alpha:
            if char != searchstr[0]:
                exact_nhood.append(char + searchstr[1:])
        # For the remaining positions, use the wildcard character.
        for pos in range(1, strlen):
            wc_nhood.append(searchstr[:pos] + '_' + searchstr[pos+1:])
    
        # Transpositions.
        for pos in range(strlen - 1):
            exact_nhood.append(searchstr[:pos] + searchstr[pos+1] + searchstr[pos] +
                    searchstr[pos+2:])
    
        # As a final step, apply the proper casing to each neighborhood string so
        # that it will work with a dictionary of scientific names.
        exact_nhood = [neighbor[0].upper() + neighbor[1:] for neighbor in exact_nhood]
        wc_nhood = [neighbor[0].upper() + neighbor[1:] for neighbor in wc_nhood]
    
        return (exact_nhood, wc_nhood)

    def match(self, searchstr):
        """
        This method merely provides a "concrete" implementation of the abstract
        method in the superclass.  When DLMatcher is instantiated, this placeholder
        will be replaced with one of the two real matching methods implemented below.
        """
        pass
    
    def _matchFullNhood(self, searchstr):
        nhood = self.generateNeighborhood(searchstr, self.k)
        #print nhood
 
        # This approach uses the IN operator and is very slightly slower than the method below.
        # Note: Generating the argument string can be expressed more compactly using the string
        # join() method, but in my testing, implementing it as below is about 22x faster.
        #argstr = ('%s, ' * (len(nhood) - 1)) + '%s'
        #query = """SELECT {0} FROM {1} n
        #    WHERE n.{0} IN ({2})""".format(self.dbcol, self.dbtable, argstr)
        #print self.dbcursor.mogrify(query, nhood)
        #self.dbcursor.execute(query, nhood)

        # This approaches uses the ANY operator on an array of strings.
        query = """SELECT {0} FROM {1} n
            WHERE n.{0}=ANY(%s)""".format(self.dbcol, self.dbtable)
        #print query

        self.dbcursor.execute(query, (nhood,))
        results = self.dbcursor.fetchall()
    
        return [result[0] for result in results]

    def _matchWCNhood(self, searchstr, usepartial=False):
        """
        Performs a Damerau-Levenshtein 1-neighborhood search using either a standard wildcard
        neighborhood from generateWCNeighborhood() or a partial wildcard neighborhood from
        generatePartialWCNeighborhood() (if usepartial is True).
        """
        if usepartial:
            nhood = self.generatePartialK1WCNeighborhood(searchstr)
        else:
            nhood = self.generateK1WCNeighborhood(searchstr)
        #print nhood
    
        # First, build the exact match part of the WHERE clause.
        # Note: Generating the argument string can be expressed more compactly using the string
        # join() method, but in my testing, implementing it as below is about 22x faster.
        exact_argstr = ('%s, ' * (len(nhood[0]) - 1)) + '%s'
    
        # Then build the wildcard part of the WHERE clause.
        wc_argstr = ' OR n.namestr LIKE %s' * len(nhood[1])
    
        query = """SELECT {0} FROM {1} n
            WHERE n.{0} IN ({2}){3}""".format(self.dbcol, self.dbtable, exact_argstr, wc_argstr)
        #print query
    
        arglist = nhood[0]
        arglist.extend(nhood[1])
        #print self.dbcursor.mogrify(query, arglist)
        self.dbcursor.execute(query, arglist)
        results = self.dbcursor.fetchall()
    
        return [result[0] for result in results]


class HybridMatcher(Matcher):
    """
    Implements approximate string matching with a hybrid q-gram/Damerau-Levenshtein
    matching algorithm.  The cutoffs for the algorithm were tuned with the genus
    names dataset using a q-gram similarity threshold of 0.4.
    """
    def __init__(self, dbtablename=None, dbcolname=None, dbcursor=None):
        # Instantiate and initialize q-gram and D-L matchers.
        self.qgmatcher = QgramMatcher()
        self.qgmatcher.setSimilarityCutoff(0.4)
        self.dlmatcher = DLMatcher()

        # Set the search string length cutoff values.
        self.lowerlen = 4
        self.upperlen = 9

        # Call the superclass initializer.
        Matcher.__init__(self, dbtablename, dbcolname, dbcursor)

    def setDBTableInfo(self, dbtablename, dbcolname):
        # Call the superclass implementation.
        Matcher.setDBTableInfo(self, dbtablename, dbcolname)

        # Update the q-gram and DL matchers.
        self.qgmatcher.setDBTableInfo(dbtablename, dbcolname)
        self.dlmatcher.setDBTableInfo(dbtablename, dbcolname)

    def setDBCursor(self, dbcursor):
        # Call the superclass implementation.
        Matcher.setDBCursor(self, dbcursor)

        # Update the q-gram and DL matchers.
        self.qgmatcher.setDBCursor(dbcursor)
        self.dlmatcher.setDBCursor(dbcursor)

    def match(self, searchstr):
        searchlen = len(searchstr)
    
        if searchlen > self.lowerlen:
            # Do a q-gram search.
            results = self.qgmatcher.match(searchstr)
            if searchlen < self.upperlen:
                # Also do a D-L search and merge the results with the q-gram search.
                results2 = self.dlmatcher.match(searchstr)
                for result in results2:
                    if result not in results:
                        results.append(result)
        else:
            # Only do a D-L search.
            results = self.dlmatcher.match(searchstr)
    
        return results


class SoundexMatcher(Matcher):
    """
    Implements approximate string matching using the classic Soundex phonetic
    encoding algorithm.
    """
    def match(self, searchstr):
        query = """SELECT {0} FROM {1} n
            WHERE soundex(n.{0})=soundex(%s)""".format(self.dbcol, self.dbtable)
        #print query
    
        #print self.dbcursor.mogrify(query, (searchstr,))
        self.dbcursor.execute(query, (searchstr,))
        results = self.dbcursor.fetchall()
    
        return [result[0] for result in results]


class DMetaphoneMatcher(Matcher):
    """
    Implements approximate string matching using Lawrence Philips' Double Metaphone
    phonetic encoding algorithm.  As currently implemented, both Double Metaphone
    encodings are used, if available.
    """
    def match(self, searchstr):
        query = """SELECT {0} FROM {1} n
            WHERE dmetaphone(n.{0})=dmetaphone(%s)
            OR dmetaphone_alt(n.{0})=dmetaphone_alt(%s)""".format(self.dbcol, self.dbtable)
        #print query
    
        #print self.dbcursor.mogrify(query, (searchstr, searchstr))
        self.dbcursor.execute(query, (searchstr, searchstr))
        results = self.dbcursor.fetchall()
    
        return [result[0] for result in results]

