# Copyright (c) 2013-2016 Christian Geier et al.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""this module contains some helper functions converting strings or list of
strings to date(time) or event objects"""

from calendar import isleap
from datetime import date, datetime, timedelta, time
import random
import string
import re
from time import strptime

import icalendar
import pytz

from khal.log import logger
from khal.exceptions import FatalError


def timefstr(dtime_list, timeformat):
    """converts a time (as a string) to a datetimeobject

    the date is today
    removes "used" elements of list

    :returns: datetimeobject
    """
    if len(dtime_list) == 0:
        raise ValueError()
    time_start = datetime.strptime(dtime_list[0], timeformat)
    time_start = time(*time_start.timetuple()[3:5])
    day_start = date.today()
    dtstart = datetime.combine(day_start, time_start)
    dtime_list.pop(0)
    return dtstart


def datetimefstr(dtime_list, dtformat):
    """
    converts a datetime (as one or several string elements of a list) to
    a datetimeobject

    removes "used" elements of list

    :returns: a datetime
    :rtype: datetime.datetime
    """
    parts = dtformat.count(' ') + 1
    dtstring = ' '.join(dtime_list[0:parts])
    dtstart = datetime.strptime(dtstring, dtformat)
    for _ in range(parts):
        dtime_list.pop(0)
    return dtstart


def weekdaypstr(dayname):
    """converts an (abbreviated) dayname to a number (mon=0, sun=6)

    :param dayname: name of abbreviation of the day
    :type dayname: str
    :return: number of the day in a week
    :rtype: int
    """

    if dayname in ['monday', 'mon']:
        return 0
    if dayname in ['tuesday', 'tue']:
        return 1
    if dayname in ['wednesday', 'wed']:
        return 2
    if dayname in ['thursday', 'thu']:
        return 3
    if dayname in ['friday', 'fri']:
        return 4
    if dayname in ['saturday', 'sat']:
        return 5
    if dayname in ['sunday', 'sun']:
        return 6
    raise ValueError('invalid weekday name `%s`' % dayname)


def calc_day(dayname):
    """converts a relative date's description to a datetime object

    :param dayname: relative day name (like 'today' or 'monday')
    :type dayname: str
    :returns: date
    :rtype: datetime.datetime
    """
    today = datetime.today()
    dayname = dayname.lower()
    if dayname == 'today':
        return today
    if dayname == 'tomorrow':
        return today + timedelta(days=1)

    wday = weekdaypstr(dayname)
    days = (wday - today.weekday()) % 7
    days = 7 if days == 0 else days
    day = today + timedelta(days=days)
    return day


def datefstr_weekday(dtime_list, _):
    """interprets first element of a list as a relative date and removes that
    element

    :param dtime_list: event descrpition in list form
    :type dtime_list: list
    :returns: date
    :rtype: datetime.datetime

    """
    if len(dtime_list) == 0:
        raise ValueError()
    day = calc_day(dtime_list[0])
    dtime_list.pop(0)
    return day


def datetimefstr_weekday(dtime_list, timeformat):
    if len(dtime_list) == 0:
        raise ValueError()
    day = calc_day(dtime_list[0])
    this_time = timefstr(dtime_list[1:], timeformat)
    dtime_list.pop(0)
    dtime_list.pop(0)  # we need to pop twice as timefstr gets a copy
    dtime = datetime.combine(day, this_time.time())
    return dtime


def guessdatetimefstr(dtime_list, locale, default_day=None):
    """
    :type dtime_list: list
    :type locale: dict
    :type default_day: datetime.datetime
    :rtype: datetime.datetime
    """
    # if now() is called as default param, mocking with freezegun won't work
    if default_day is None:
        default_day = datetime.now().date()
    # TODO rename in guessdatetimefstrLIST or something saner altogether

    def timefstr_day(dtime_list, timeformat):
        if locale['timeformat'] == '%H:%M' and dtime_list[0] == '24:00':
            a_date = datetime.combine(default_day, time(0))
            dtime_list.pop(0)
        else:
            a_date = timefstr(dtime_list, timeformat)
            a_date = datetime(*(default_day.timetuple()[:3] + a_date.timetuple()[3:5]))
        return a_date

    def datefstr_year(dtime_list, dateformat):
        """should be used if a date(time) without year is given

        we cannot use datetimefstr() here, because only time.strptime can
        parse the 29th of Feb. if no year is given

        example: dtime_list = ['17.03.', 'description']
                 dateformat = '%d.%m.'
        or     : dtime_list = ['17.03.', '16:00', 'description']
                 dateformat = '%d.%m. %H:%M'
        """
        parts = dateformat.count(' ') + 1
        dtstring = ' '.join(dtime_list[0:parts])
        dtstart = strptime(dtstring, dateformat)
        if dtstart.tm_mon == 2 and dtstart.tm_mday == 29 and not isleap(default_day.year):
            raise ValueError

        for _ in range(parts):
            dtime_list.pop(0)

        a_date = datetime(*(default_day.timetuple()[:1] + dtstart[1:5]))
        return a_date

    dtstart = None
    for fun, dtformat, all_day in [
            (datefstr_year, locale['datetimeformat'], False),
            (datetimefstr, locale['longdatetimeformat'], False),
            (timefstr_day, locale['timeformat'], False),
            (datetimefstr_weekday, locale['timeformat'], False),
            (datefstr_year, locale['dateformat'], True),
            (datetimefstr, locale['longdateformat'], True),
            (datefstr_weekday, None, True),

    ]:
        try:
            dtstart = fun(dtime_list, dtformat)
            return dtstart, all_day
        except ValueError:
            pass
    raise ValueError()


def guesstimedeltafstr(delta_string):
    """parses a timedelta from a string

    :param delta_string: string encoding time-delta, e.g. '1h 15m'
    :type delta_string: str
    :rtype: datetime.timedelta
    """

    tups = re.split(r'(-?\d+)', delta_string)
    if not re.match(r'^\s*$', tups[0]):
        raise ValueError('Invalid beginning of timedelta string "%s": "%s"'
                         % (delta_string, tups[0]))
    tups = tups[1:]
    res = timedelta()

    for num, unit in zip(tups[0::2], tups[1::2]):
        try:
            numint = int(num)
        except ValueError:
            raise ValueError('Invalid number in timedelta string "%s": "%s"'
                             % (delta_string, num))

        ulower = unit.lower().strip()
        if ulower == 'd' or ulower == 'day' or ulower == 'days':
            res += timedelta(days=numint)
        elif ulower == 'h' or ulower == 'hour' or ulower == 'hours':
            res += timedelta(hours=numint)
        elif (ulower == 'm' or ulower == 'minute' or ulower == 'minutes' or
              ulower == 'min'):
            res += timedelta(minutes=numint)
        else:
            raise ValueError('Invalid unit in timedelta string "%s": "%s"'
                             % (delta_string, unit))

    return res


def guessrangefstr(daterange, locale, default_timedelta=None):
    """parses a range string

    :param daterange: date1 [date2 | timedelta]
    :type daterange: str or list
    :param locale:
    :rtype: (datetime, datetime)

    """

    range_list = daterange
    if isinstance(daterange, str):
        range_list = daterange.split()

    try:
        if len(default_timedelta) == 0:
            default_timedelta = None
        else:
            default_timedelta = guesstimedeltafstr(default_timedelta)
    except ValueError:
        default_timedelta = None

    for i in range(1, len(range_list) + 1):
        start = ' '.join(range_list[:i])
        end = ' '.join(range_list[i:])
        try:
            if start is None:
                start = datetime_fillin(end=False)
            elif not isinstance(start, date):
                split = start.split(" ")
                start = guessdatetimefstr(split, locale)[0]
                if len(split) != 0:
                    continue

            if end is None or len(end) == 0:
                if default_timedelta is not None:
                    end = start + default_timedelta
                else:
                    end = datetime_fillin(day=start)
            else:
                if end.lower() == 'eod':
                    end = datetime_fillin(day=start)
                else:
                    try:
                        delta = guesstimedeltafstr(end)
                        end = start + delta
                    except ValueError:
                        split = end.split(" ")
                        end = guessdatetimefstr(split, locale, default_day=start.date())[0]
                        if len(split) != 0:
                            continue
                    end = datetime_fillin(end)
            return start, end
        except Exception:   # XXX FIXME what kind of exceptions do we want to catch here?
            pass

    return None, None


def datetime_fillin(dt=None, end=True, locale=None, day=None):
    """returns a datetime that is filled in (with time etc)

    :param dt:
    :type dt: datetime or date or time if None then day is used
    :param end:
    :type end: boolean set True if time.max should be used (else min)
    :param locale:
    :type locale: if set the time will be in this locale
    :param day:
    :type day: the day to be used if just a time is passed in (else today)
    :rtype: datetime

    """
    if day is None:
        day = datetime.today()

    if isinstance(day, datetime):
        day = day.date()

    if dt is None:
        dt = day

    if isinstance(dt, time) and not isinstance(dt, datetime):
        dt = datetime.combine(day, dt)

    if isinstance(dt, date) and not isinstance(dt, datetime):
        t = time.max if end else time.min
        dt = datetime.combine(dt, t)

    if locale is not None:
        try:
            dt = locale['local_timezone'].localize(dt)
        except:
            pass

    return dt


def generate_random_uid():
    """generate a random uid

    when random isn't broken, getting a random UID from a pool of roughly 10^56
    should be good enough"""
    choice = string.ascii_uppercase + string.digits
    return ''.join([random.choice(choice) for _ in range(36)])


def construct_event(dtime_list, locale,
                    defaulttimelen=60, defaultdatelen=1, description=None,
                    location=None, categories=None, repeat=None, until=None,
                    alarm=None, **kwargs):
    """takes a list of strings and constructs a vevent from it

    the parts of the list can be either of these:
        * datetime datetime description
            start and end datetime specified, if no year is given, this year
            is used, if the second datetime has no year, the same year as for
            the first datetime object will be used, unless that would make
            the event end before it begins, in which case the next year is
            used
        * datetime time description
            end date will be same as start date, unless that would make the
            event end before it has started, then the next day is used as
            end date
        * datetime description
            event will last for defaulttime
        * time time description
            event starting today at the first time and ending today at the
            second time, unless that would make the event end before it has
            started, then the next day is used as end date
        * time description
            event starting today at time, lasting for the default length
        * date date description
            all day event starting on the first and ending on the last event
        * date description
            all day event starting at given date and lasting for default length

    datetime should match datetimeformat or longdatetimeformat
    time should match timeformat

    where description is the unused part of the list
    see tests for examples

    """
    # TODO remove if this survives for some time in the wild without getting any reports
    first_type = type(dtime_list[0])
    try:
        for part in dtime_list:
            assert first_type == type(part)
    except AssertionError:
        logger.error(
            "An internal error occured, please report the below error message "
            "to khal's developers at https://github.com/pimutils/khal/issues or "
            "via email at khal@lostpackets.de")
        logger.error(' '.join(['{} ({})'.format(part, type(part)) for part in dtime_list]))

    today = datetime.today()
    try:
        dtstart, all_day = guessdatetimefstr(dtime_list, locale)
    except ValueError:
        logger.fatal("Cannot parse: '{}'\nPlease have a look at "
                     "the documentation.".format(' '.join(dtime_list)))
        raise FatalError()

    try:
        dtend, _ = guessdatetimefstr(dtime_list, locale, dtstart)
    except ValueError:
        if all_day:
            dtend = dtstart + timedelta(days=defaultdatelen - 1)
        else:
            dtend = dtstart + timedelta(minutes=defaulttimelen)

    if all_day:
        dtend += timedelta(days=1)
        # test if dtend's year is this year, but dtstart's year is not
        if dtend.year == today.year and dtstart.year != today.year:
            dtend = datetime(dtstart.year, *dtend.timetuple()[1:6])

        if dtend < dtstart:
            dtend = datetime(dtend.year + 1, *dtend.timetuple()[1:6])

    if dtend < dtstart:
        dtend = datetime(*dtstart.timetuple()[0:3] +
                         dtend.timetuple()[3:5])
    if dtend < dtstart:
        dtend = dtend + timedelta(days=1)
    if all_day:
        dtstart = dtstart.date()
        dtend = dtend.date()

    else:
        if not dtime_list:
            logger.fatal('No event summary provided, aborting.')
            raise FatalError
        try:
            # next element is a valid Olson db timezone string
            dtstart = pytz.timezone(dtime_list[0]).localize(dtstart)
            dtend = pytz.timezone(dtime_list[0]).localize(dtend)
            dtime_list.pop(0)
        except (pytz.UnknownTimeZoneError, UnicodeDecodeError):
            dtstart = locale['default_timezone'].localize(dtstart)
            dtend = locale['default_timezone'].localize(dtend)

    event = icalendar.Event()
    text = ' '.join(dtime_list)
    if not description or not location:
        summary = text.split(' :: ', 1)[0]
        try:
            description = text.split(' :: ', 1)[1]
        except IndexError:
            pass
    else:
        summary = text

    if description:
        event.add('description', description)
    if location:
        event.add('location', location)
    if categories:
        event.add('categories', categories)
    if repeat and repeat != "none":
        if repeat in ["daily", "weekly", "monthly", "yearly"]:
            rrule_settings = {'freq': repeat}
            if until:
                until_date = None
                for fun, dformat in [(datetimefstr, locale['datetimeformat']),
                                     (datetimefstr, locale['longdatetimeformat']),
                                     (timefstr, locale['timeformat']),
                                     (datetimefstr, locale['dateformat']),
                                     (datetimefstr, locale['longdateformat'])]:
                    try:
                        until_date = fun(until, dformat)
                        break
                    except ValueError:
                        pass
                if until_date is None:
                    logger.fatal("Cannot parse until date: '{}'\nPlease have a look "
                                 "at the documentation.".format(until))
                    raise FatalError()
                rrule_settings['until'] = until_date

            event.add('rrule', rrule_settings)
        else:
            logger.fatal("Invalid value for the repeat option. \
                    Possible values are: daily, weekly, monthly or yearly")
            raise FatalError()
    if alarm:
        alarm_trig = -1 * guesstimedeltafstr(alarm)
        new_alarm = icalendar.Alarm()
        new_alarm.add('ACTION', 'DISPLAY')
        new_alarm.add('TRIGGER', alarm_trig)
        new_alarm.add('DESCRIPTION', description)
        event.add_component(new_alarm)

    event.add('dtstart', dtstart)
    event.add('dtend', dtend)
    event.add('dtstamp', datetime.now())
    event.add('summary', summary)
    event.add('uid', generate_random_uid())  # TODO add proper UID
    return event


def new_event(dtstart=None, dtend=None, summary=None, timezone=None,
              allday=False):
    """create a new event

    :param dtstart: starttime of that event
    :type dtstart: datetime
    :param dtend: end time of that event, if this is a *date*, this value is
        interpreted as being the last date the event is scheduled on, i.e.
        the VEVENT DTEND will be *one day later*
    :type dtend: datetime
    :param summary: description of the event, used in the SUMMARY property
    :type summary: unicode
    :param timezone: timezone of the event (start and end)
    :type timezone: pytz.timezone
    :param allday: if set to True, we will not transform dtstart and dtend to
        datetime
    :type allday: bool
    :returns: event
    :rtype: icalendar.Event
    """
    now = datetime.now().timetuple()
    now = datetime(now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour)
    inonehour = now + timedelta(minutes=60)
    if dtstart is None:
        dtstart = inonehour
    elif isinstance(dtstart, date) and not allday:
        time_start = inonehour.time()
        dtstart = datetime.combine(dtstart, time_start)

    if dtend is None:
        dtend = dtstart + timedelta(minutes=60)
    if allday:
        dtend += timedelta(days=1)
    if summary is None:
        summary = ''
    if timezone is not None:
        dtstart = timezone.localize(dtstart)
        dtend = timezone.localize(dtend)
    event = icalendar.Event()
    event.add('dtstart', dtstart)
    event.add('dtend', dtend)
    event.add('dtstamp', datetime.now())
    event.add('summary', summary)
    event.add('uid', generate_random_uid())
    event.add('sequence', 0)
    return event


def ics_from_list(vevent, random_uid=False):
    """convert an iterable of icalendar.Event to an icalendar.Calendar

    :param random_uid: asign the same random UID to all events
    :type random_uid: bool
    """
    calendar = icalendar.Calendar()
    calendar.add('version', '2.0')
    calendar.add('prodid', '-//CALENDARSERVER.ORG//NONSGML Version 1//EN')
    if random_uid:
        new_uid = icalendar.vText(generate_random_uid())
    for sub_event in vevent:
        if random_uid:
            sub_event['uid'] = new_uid
        calendar.add_component(sub_event)
    return calendar
