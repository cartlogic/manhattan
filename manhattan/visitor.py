import time

from .util import choose_population
from .record import PageRecord, PixelRecord, GoalRecord, SplitRecord


# Goal Value Aggregation Types
RATE = 'R'
AVERAGE = 'A'
SUM = 'S'

# Goal Value Measurement Formats
NUMERIC = 'N'
CURRENCY = 'C'
PERCENTAGE = 'P'


class Visitor(object):
    """
    A handle to perform operations on the given visitor session.
    """
    def __init__(self, id, log, site_id=''):
        """
        Initialize the Visitor handle.

        :param id:
            id to reference this Visitor.
        :type id:
            str
        :param log:
            A log instance that implements the manhattan log interface methods.
        """
        self.id = id
        self.log = log
        self.site_id = str(site_id)

    def timestamp(self):
        """
        Override this to generate event timestamps in a different way. Defaults
        to the POSIX epoch.
        """
        return '%0.4f' % time.time()

    def write(self, rec):
        self.log.write(rec.to_list())

    def page(self, request):
        """
        Log a page view for this visitor.

        :param request:
            A request object corresponding to the page to log.
        :type request:
            webob.Request instance
        """
        rec = PageRecord(timestamp=self.timestamp(),
                         vid=self.id,
                         site_id=self.site_id,
                         ip=request.remote_addr or '0.0.0.0',
                         method=request.method,
                         url=request.url,
                         user_agent=request.user_agent or '',
                         referer=request.referer or '')
        self.write(rec)

    def pixel(self):
        """
        Log a pixel view for this visitor.
        """
        rec = PixelRecord(timestamp=self.timestamp(),
                          vid=self.id,
                          site_id=self.site_id)
        self.write(rec)

    def goal(self, name, value=None, value_type=None, value_format=None):
        """
        Log a goal hit for this visitor.

        :param name:
            Name of the goal.
        :type name:
            str
        :param value:
            Value of this goal.
        :type value:
            int or float
        :param value_type:
            Type of goal value aggregation to perform.
        :type value_type:
            RATE, AVERAGE or SUM
        :param value_format:
            Display format for this goal value.
        :type value_format:
            NUMERIC, CURRENCY, or PERCENTAGE
        """
        value = value and str(value)
        rec = GoalRecord(timestamp=self.timestamp(),
                         vid=self.id,
                         site_id=self.site_id,
                         name=name.encode('ascii', 'replace'),
                         value=value or '',
                         value_type=value_type or '',
                         value_format=value_format or '')
        self.write(rec)

    def split(self, test_name, populations=None):
        """
        Perform a split test for this visitor. The resulting population is
        calculated deterministically based on the test name and the visitor id,
        so the same visitor id and the same test name will always be assigned
        to the same population.

        :param test_name:
            Name of the test.
        :type test_name:
            str
        :param populations:
            Population specified. Can be any of the following:

                None -- 50/50 split performed between True or False.
                list -- Select evenly between entries in the list.
                dict -- A weighted split between keys in the dict. The weight
                of each population is specified by the value, as a float.

        :returns:
            The population selected for the visitor.
        """
        selected = choose_population(self.id + test_name, populations)
        rec = SplitRecord(timestamp=self.timestamp(),
                          vid=self.id,
                          site_id=self.site_id,
                          test_name=test_name,
                          selected=str(selected))
        self.write(rec)
        return selected
