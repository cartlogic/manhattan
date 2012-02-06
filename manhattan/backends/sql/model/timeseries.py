import time
from datetime import datetime, timedelta

from sqlalchemy import Table, Column, ForeignKey, types
from sqlalchemy.sql import select, func

from . import meta


granularities = ('all', 'month', 'week', 'day', 'hour')


conversion_tables = {}
impression_tables = {}
variant_conversion_tables = {}


for granularity in granularities:
    conv = Table('conversions_%s_bucket' % granularity,
                 meta.metadata,
                 Column('goal_id', None, ForeignKey('goals.id'),
                        primary_key=True),
                 Column('start_timestamp', types.Integer, primary_key=True),
                 Column('count', types.Integer, nullable=False, default=0),
                 mysql_engine='InnoDB')
    conversion_tables[granularity] = conv

    impr = Table('impressions_%s_bucket' % granularity,
                 meta.metadata,
                 Column('variant_id', None, ForeignKey('variants.id'),
                        primary_key=True),
                 Column('start_timestamp', types.Integer, primary_key=True),
                 Column('count', types.Integer, nullable=False, default=0),
                 mysql_engine='InnoDB')
    impression_tables[granularity] = impr

    varc = Table('variant_conversions_%s_bucket' % granularity,
                 meta.metadata,
                 Column('variant_id', None, ForeignKey('variants.id'),
                        primary_key=True),
                 Column('goal_id', None, ForeignKey('goals.id'),
                        primary_key=True),
                 Column('start_timestamp', types.Integer, primary_key=True),
                 Column('count', types.Integer, nullable=False, default=0),
                 mysql_engine='InnoDB')
    variant_conversion_tables[granularity] = varc


def bucket_for_timestamp(granularity, timestamp):
    """
    Given a timestamp and granularity, return the start_timestamp corresponding
    to the bucket containing the given timestamp.
    """
    dt = datetime.fromtimestamp(timestamp)
    if granularity == 'all':
        return 0

    new = datetime(year=dt.year, month=dt.month, day=dt.day)
    if granularity == 'month':
        new = new.replace(day=1)
    elif granularity == 'week':
        new = new - timedelta(days=dt.weekday())
    elif granularity == 'day':
        pass
    elif granularity == 'hour':
        new = new.replace(day=dt.day, hour=dt.hour)
    else:
        raise ValueError('invalid granularity %r' % granularity)

    return int(time.mktime(new.timetuple()))


def filter_q(t, q, start, goal_id=None, variant_id=None):
    if goal_id:
        q = q.where(t.c.goal_id == goal_id)
    if variant_id:
        q = q.where(t.c.variant_id == variant_id)
    q = q.where(t.c.start_timestamp == start)
    return q


def increment(tables, timestamp, goal_id=None, variant_id=None):
    for granularity in granularities:
        start = bucket_for_timestamp(granularity, timestamp)
        t = tables[granularity]

        q = filter_q(t, select([t.c.count]), start, goal_id, variant_id)

        if not q.scalar():
            kw = {}
            if goal_id:
                kw['goal_id'] = goal_id
            if variant_id:
                kw['variant_id'] = variant_id
            t.insert().values(count=1,
                              start_timestamp=start,
                              **kw).execute()
        else:
            q = t.update().values(count=t.c.count + 1)
            q = filter_q(t, q, start, goal_id, variant_id)
            q.execute()


def record_conversion(goal_id, timestamp):
    increment(conversion_tables, timestamp, goal_id=goal_id)


def record_impression(variant_id, timestamp):
    increment(impression_tables, timestamp, variant_id=variant_id)


def record_variant_conversion(variant_id, goal_id, timestamp):
    increment(variant_conversion_tables, timestamp,
              goal_id=goal_id, variant_id=variant_id)


def count_at_granularity(tables, granularity, goal_id, variant_id=None):
    t = tables[granularity]
    q = select([func.sum(t.c.count)])

    q = q.where(t.c.goal_id == goal_id)

    if variant_id:
        q = q.where(t.c.variant_id == variant_id)

    return q.scalar()


def count(goal_id, variant_id=None, start=None, end=None):
    if variant_id:
        tables = variant_conversion_tables
    else:
        tables = conversion_tables

    # FIXME Add support for time range filtering with the right granularity.
    assert not start and not end
    granularity = 'all'

    return count_at_granularity(tables, granularity,
                                goal_id=goal_id, variant_id=variant_id)