"""
Provides classes that perform operations on a taxonomic tree by recursively traversing
all taxa within the tree.
"""


import csv, sys


class TaxonVisitor:
    """
    Base class for all taxon tree visitor classes.  Client code calls the visit() method
    with an instance of Taxon as an argument.  The visitor class will then traverse the
    taxon tree and operate on each Taxon object in the tree.  The traversal can be limited
    by either the total number of taxa processed or tree depth (or both).  In essence, this
    base class encapsulates an algorithm for traversing a taxa tree and allows operations
    on tree objects to be implemented independently of the Taxon implementation.
    """
    def __init__(self, numtaxa=-1, maxdepth=-1):
        """
        If numtaxa > 0, only the first numtaxa taxa will be visited when a taxon tree
        is traversed.  If maxdepth > -1, the tree will only be traversed to a depth
        of maxdepth.
        """
        self.numtaxa = numtaxa
        self.maxdepth = maxdepth

    def visit(self, taxon):
        """
        Initiates the taxon tree traversal.
        """
        self.taxacnt = 0

        self._traverseTree(taxon, 0)

    def _traverseTree(self, taxon, depth):
        """
        Internal method for traversing a taxon tree that tracks the recursion depth.
        """
        self.processTaxon(taxon, depth)

        self.taxacnt += 1

        if (self.maxdepth < 0 or depth < self.maxdepth) and self.doRecursion():
            for child in taxon.children:
                if self.numtaxa > 0 and self.taxacnt >= self.numtaxa:
                    break
                self._traverseTree(child, depth + 1)

        self.postTaxonProcessing(taxon, depth)

    def doRecursion(self):
        """
        This method can be overriden by child classes and used to implement additional
        criteria for deciding whether to recursively descend into the next level of a
        taxa tree.  The method is called prior to processing the child taxa of a taxon;
        if it returns True, the recursion is continued, otherwise, the children are
        not visited.
        """
        return True

    def processTaxon(self, taxon, depth):
        """
        This method is called for each Taxon object in the tree.  The argument 'depth'
        provides the current depth in the tree, with the root at 0.  This method should
        be overridden by child classes to actually do something with each Taxon object.
        """
        pass

    def postTaxonProcessing(self, taxon, depth):
        """
        This method is called after tree traversal has returned from recursively
        traversing taxon's descendents.  It can be overridden by child classes to
        implement "clean up" code that should be run before leaving a taxon.
        """
        pass


class PrintTaxonVisitor(TaxonVisitor):
    """
    Prints a simple text representation of a taxon tree.
    """
    def processTaxon(self, taxon, depth):
        print '   ' * depth + taxon.__str__()
        synstr = taxon.getSynonymsString()
        if synstr != '':
            print '   ' * depth + '  -- Synonyms: ' + synstr


class RankAccumulatorTaxonVisitor(TaxonVisitor):
    """
    A taxon visitor class that builds a list of all taxonomic ranks that are used in
    a taxonomy tree.
    """
    def visit(self, taxon):
        """
        Returns a list of all taxonomic rank names used in a taxonomy tree.  The rank
        names will be sorted according to their IDs in the database.
        """
        # Initialize a list for the rank strings.
        self.ranks = []

        # Call the superclass method implementation to initiate the traversal.
        TaxonVisitor.visit(self, taxon)

        # Sort the ranks according to their rank IDs.
        self.ranks.sort(key=lambda rankstr: taxon.rankt.getID(rankstr, taxon.ranksys))

        return self.ranks

    def processTaxon(self, taxon, depth):
        rankstr = taxon.getRankString()

        if rankstr not in self.ranks:
            self.ranks.append(rankstr)


class CSVTaxonVisitor(TaxonVisitor):
    """
    Prints a CSV representation of a taxon tree.
    """
    def visit(self, taxon):
        # Get a list of all ranks used in the tree..
        ranks = RankAccumulatorTaxonVisitor().visit(taxon)

        # Set up the CSV writer.
        csvheader = ranks + ['Author', 'Synonyms', 'Citation']
        self.writer = csv.DictWriter(sys.stdout, fieldnames=csvheader)
        self.writer.writeheader()

        # Create a dictionary for storing CSV row values.
        self.rowvals = {}
        for colname in csvheader:
            self.rowvals[colname] = ''

        # Call the superclass method implementation to initiate the traversal.
        TaxonVisitor.visit(self, taxon)

        return

    def processTaxon(self, taxon, depth):
        rank = taxon.getRankString()
        self.rowvals[rank] = taxon.name.namestr

        # Only get author and synonym information and print a row if we're at a
        # leaf of the tree.  This makes the CSV output consistent with the way
        # CSV taxonomy files are parsed by the input routines.
        if len(taxon.children) == 0:
            self.rowvals['Author'] = taxon.getAuthorDisplayString()
            self.rowvals['Synonyms'] = taxon.getSynonymsString()
            #self.rowvals['Citation'] = taxon.name.getCitationString()
            self.writer.writerow(self.rowvals)

    def postTaxonProcessing(self, taxon, depth):
        self.rowvals[taxon.getRankString()] = ''
        self.rowvals['Author'] = ''
        self.rowvals['Synonyms'] = ''
        self.rowvals['Citation'] = ''


class NamesTaxonVisitor(TaxonVisitor):
    """
    A taxon visitor class that builds a list of all Name objects in the taxa tree.
    The results are returned as a list of tuples, where each tuple contains the
    Name object and a string representing the taxonomic rank of the name; i.e.:
    (Name, rankstring).
    """
    def visit(self, taxon):
        # Initialize a list for the Name objects.
        self.names = []

        # Call the superclass method implementation.
        TaxonVisitor.visit(self, taxon)

        return self.names

    def processTaxon(self, taxon, depth):
        self.names.append((taxon.name, taxon.getRankString()))

