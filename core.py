#############################################################################
##
## Copyright (C) 2014 Alex Merry <alex.merry@kde.org>
## Contact: http://www.qt-project.org/legal
##
## This file is part of the GDB pretty printers for the Qt Toolkit.
##
## $QT_BEGIN_LICENSE:LGPL$
## Commercial License Usage
## Licensees holding valid commercial Qt licenses may use this file in
## accordance with the commercial license agreement provided with the
## Software or, alternatively, in accordance with the terms contained in
## a written agreement between you and Digia.  For licensing terms and
## conditions see http://qt.digia.com/licensing.  For further information
## use the contact form at http://qt.digia.com/contact-us.
##
## GNU Lesser General Public License Usage
## Alternatively, this file may be used under the terms of the GNU Lesser
## General Public License version 2.1 as published by the Free Software
## Foundation and appearing in the file LICENSE.LGPL included in the
## packaging of this file.  Please review the following information to
## ensure the GNU Lesser General Public License version 2.1 requirements
## will be met: http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html.
##
## In addition, as a special exception, Digia gives you certain additional
## rights.  These rights are described in the Digia Qt LGPL Exception
## version 1.1, included in the file LGPL_EXCEPTION.txt in this package.
##
## GNU General Public License Usage
## Alternatively, this file may be used under the terms of the GNU
## General Public License version 3.0 as published by the Free Software
## Foundation and appearing in the file LICENSE.GPL included in the
## packaging of this file.  Please review the following information to
## ensure the GNU General Public License version 3.0 requirements will be
## met: http://www.gnu.org/copyleft/gpl.html.
##
##
## $QT_END_LICENSE$
##
#############################################################################

import gdb.printing
import itertools
from . import typeinfo
try:
    import urlparse
except ImportError:
    # Python 3
    import urllib.parse as urlparse

"""Qt5Core pretty printer for GDB."""

# NB: no QPair printer: the default should be fine

def _format_jd(jd):
    """Format a Julian Day in YYYY-MM-DD format."""
    # maths from http://www.tondering.dk/claus/cal/julperiod.php
    a = jd + 32044
    b = (4 * a + 3) // 146097
    c = a - ( (146097 * b) // 4 )
    d = (4 * c + 3) // 1461
    e = c - ( (1461 * d) // 4 )
    m = (5 * e + 2) // 153
    day = e - ( (153 * m + 2) // 5 ) + 1
    month = m + 3 - 12 * ( m // 10 )
    year = 100 * b + d - 4800 + ( m // 10 )
    return '{:0=4}-{:0=2}-{:0=2}'.format(year, month, day)

def _jd_is_valid(jd):
    """Return whether QDate would consider a given Julian Day valid."""
    return jd >= -784350574879 and jd <= 784354017364

def _format_time_ms(msecs):
    """Format a number of milliseconds since midnight in HH:MM:SS.ssss format."""
    secs = msecs // 1000
    mins = secs // 60
    hours = mins // 60
    return '{:0=2}:{:0=2}:{:0=2}.{:0=3}'.format(
            hours % 24, mins % 60, secs % 60, msecs % 1000)

def _ms_is_valid(msecs):
    """Return whether QTime would consider a ms since midnight valid."""
    return msecs >= 0 and msecs <= 86400000

class ArrayIter:
    """Iterates over a fixed-size array."""
    def __init__(self, array, size):
        self.array = array
        self.i = -1
        self.size = size

    def __iter__(self):
        return self

    def __next__(self):
        if self.i + 1 >= self.size:
            raise StopIteration
        self.i += 1
        return ('[%d]' % self.i, self.array[self.i])

    def next(self):
        return self.__next__()

class StructReader:
    """Reads entries from a struct."""
    def __init__(self, data):
        self.data = data.reinterpret_cast(gdb.lookup_type('char').pointer())
        self.ptr_t = gdb.lookup_type('void').pointer()

    def next_aligned_val(self, typ):
        ptr_val = int(str(self.data.reinterpret_cast(self.ptr_t)), 16)
        misalignment = ptr_val % self.ptr_t.sizeof
        if misalignment > 0:
            self.data += self.ptr_t.sizeof - misalignment
        val = self.data.reinterpret_cast(typ.pointer())
        self.data += typ.sizeof
        return val.referenced_value()

    def next_val(self, typ):
        val = self.data.reinterpret_cast(typ.pointer())
        self.data += typ.sizeof
        return val.referenced_value()

class QBitArrayPrinter:
    """Print a Qt5 QBitArray"""

    class Iter:
        def __init__(self, data, size):
            self.data = data
            self.i = -1
            self.size = size

        def __iter__(self):
            return self

        def __next__(self):
            if self.i + 1 >= self.size:
                raise StopIteration
            self.i += 1
            if self.data[1 + (self.i >> 3)] & (1 << (self.i&7)):
                return (str(self.i), 1)
            else:
                return (str(self.i), 0)

        def next(self):
            return self.__next__()

    def __init__(self, val):
        self.val = val

    def children(self):
        d = self.val['d']['d']
        data = d.reinterpret_cast(gdb.lookup_type('char').pointer()) + d['offset']
        size = (int(d['size']) << 3) - int(data[0])

        return self.Iter(data, size)

    def to_string(self):
        d = self.val['d']['d']
        data = d.reinterpret_cast(gdb.lookup_type('char').pointer()) + d['offset']
        size = (int(d['size']) << 3) - int(data[0])
        if size == 0:
            return '<empty>'
        return None

    def display_hint(self):
        return 'array'

class QByteArrayPrinter:
    """Print a Qt5 QByteArray"""

    def __init__(self, val):
        self.val = val

    def children(self):
        d = self.val['d']
        data = d.reinterpret_cast(gdb.lookup_type('char').pointer()) + d['offset']
        return ArrayIter(data, d['size'])

    def to_string(self):
        d = self.val['d']
        data = d.reinterpret_cast(gdb.lookup_type('char').pointer()) + d['offset']
        return data.string('', 'replace', d['size'])

    def display_hint(self):
        return 'string'

class QCharPrinter:
    """Print a Qt5 QChar"""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        ucs = self.val['ucs']
        data = ucs.address.reinterpret_cast(gdb.lookup_type('char').pointer())
        unicode_str = data.string('utf-16', 'replace', 2)
        uch = unicode_str[0]
        if uch == unichr(0x27):
            return "'\\''"
        # this actually gives us Python escapes, but they should all be
        # valid C escapes as well
        return "'" + uch.encode('unicode_escape') + "'"

    def display_hint(self):
        # this is not recognized by gdb, hence the manual escaping and quoting
        # we do above
        return 'char'

class QDatePrinter:
    """Print a Qt5 QDate"""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        jd = int(self.val['jd'])
        if not _jd_is_valid(jd):
            return '<invalid>'
        return _format_jd(jd)

    def display_hint(self):
        return 'date'

class QDateTimePrinter:
    """Print a Qt5 QDateTime"""

    def __init__(self, val):
        self.val = val

    _unix_epoch_jd = 2440588
    _ms_per_day = 86400000

    # status field
    _validDate = 0x04
    _validTime = 0x08
    _validDateTime = 0x10
    _timeZoneCached = 0x20

    # time spec
    _localTime = 0
    _UTC = 1
    _offsetFromUTC = 2
    _timeZone = 3

    def to_string(self):
        d = self.val['d']['d']
        if not d:
            return '<invalid>'

        try:
            qshareddata_t = gdb.lookup_type('QSharedData')
        except gdb.error:
            try:
                # well, it only has a QAtomicInt in it
                qshareddata_t = gdb.lookup_type('QAtomicInt')
            except gdb.error:
                # let's hope it's the same size as an int
                qshareddata_t = gdb.lookup_type('int')
        try:
            timespec_t = gdb.lookup_type('Qt::TimeSpec')
        except gdb.error:
            # probably an int
            timespec_t = gdb.lookup_type('int')

        reader = StructReader(d)
        reader.next_val(qshareddata_t)
        m_msecs = reader.next_aligned_val(gdb.lookup_type('qint64'))
        spec = int(reader.next_val(timespec_t))
        m_offsetFromUtc = reader.next_val(gdb.lookup_type('int'))
        m_timeZone = reader.next_val(gdb.lookup_type('QTimeZone'))
        status = int(reader.next_val(gdb.lookup_type('int')))

        if spec == self._timeZone:
            timeZoneStr = QTimeZonePrinter(m_timeZone).to_string()
            if timeZoneStr == '':
                return '<invalid>'

        if spec == self._localTime or (spec == self._timeZone and
                not status & self._timeZoneCached):
            # Because QDateTime delays timezone calculations as far as
            # possible, the ValidDateTime flag may not be set even if
            # it is a valid DateTime.
            if not status & self._validDate or not status & self._validTime:
                return '<invalid>'
        elif not (status & self._validDateTime):
            return '<invalid>'

        # actually fetch:
        m_msecs = int(m_msecs)

        jd = self._unix_epoch_jd # UNIX epoch
        jd += m_msecs // self._ms_per_day
        msecs = m_msecs % self._ms_per_day
        if msecs < 0:
            # need to adjust back to the previous day
            jd -= 1
            msecs += self._ms_per_day

        result = _format_jd(jd) + ' ' + _format_time_ms(msecs)

        if spec == self._localTime:
            result += ' (Local)'
        elif spec == self._UTC:
            result += ' (UTC)'
        elif spec == self._offsetFromUTC:
            offset = int(m_offsetFromUtc)
            if offset == 0:
                diffstr = ''
            else:
                hours = abs(offset // 3600)
                mins = abs((offset % 3600) // 60)
                secs = abs(offset % 60)
                sign = '+' if offset > 0 else '-'
                diffstr = '{:}{:0=2d}:{:0=2d}'.format(sign, hours, mins)
                if secs > 0:
                    diffstr += ':{:0=2d}'.format(secs)
            result += ' (UTC{:})'.format(diffstr)
        elif spec == self._timeZone:
            result += ' ({:})'.format(timeZoneStr)

        return result

    def display_hint(self):
        return 'datetime'

class QHashPrinter:
    """Print a Qt5 QHash"""

    class Iter:
        def __init__(self, d, e):
            self.buckets_left = d['numBuckets']
            self.node_type = e.type
            # set us up at the end of a "dummy bucket"
            self.current_bucket = d['buckets'] - 1
            self.current_node = None
            self.i = -1
            self.waiting_for_value = False

        def __iter__(self):
            return self

        def __next__(self):
            if self.waiting_for_value:
                self.waiting_for_value = False
                node = self.current_node.reinterpret_cast(self.node_type)
                return ('value' + str(self.i), node['value'])

            if self.current_node:
                self.current_node = self.current_node['next']

            # the dummy node that terminates a bucket is distinguishable
            # by not having its 'next' value set
            if not self.current_node or not self.current_node['next']:
                while self.buckets_left:
                    self.current_bucket += 1
                    self.buckets_left -= 1
                    self.current_node = self.current_bucket.referenced_value()
                    if self.current_node['next']:
                        break
                else:
                    raise StopIteration

            self.i += 1
            self.waiting_for_value = True
            node = self.current_node.reinterpret_cast(self.node_type)
            return ('key' + str(self.i), node['key'])

        def next(self):
            return self.__next__()

    def __init__(self, val):
        self.val = val

    def children(self):
        d = self.val['d']

        if d['size'] == 0:
            return []

        return self.Iter(d, self.val['e'])

    def to_string(self):
        # if we return an empty list from children, gdb doesn't print anything
        if self.val['d']['size'] == 0:
            return '<empty>'
        return None

    def display_hint(self):
        return 'map'

class QJsonObjectPrinter:
    """Print a Qt5 QJsonObject"""

    def __init__(self, val):
        # delegate everything to map
        self.printer = QMapPrinter(gdb.parse_and_eval('((QJsonObject*){:})->toVariantMap()'.format(int(val.address))))

    def children(self):
        return self.printer.children()

    def to_string(self):
        return self.printer.to_string()

    def display_hint(self):
        return 'map'

class QJsonArrayPrinter:
    """Print a Qt5 QJsonArray"""

    def __init__(self, val):
        # delegate everything to list
        self.printer = QListPrinter(gdb.parse_and_eval('((QJsonArray*){:})->toVariantList()'.format(int(val.address))))

    def children(self):
        return self.printer.children()

    def to_string(self):
        return self.printer.to_string()

    def display_hint(self):
        return 'array'

class QLatin1StringPrinter:
    """Print a Qt5 QLatin1String"""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        return self.val['m_data'].string('', 'replace', self.val['m_size'])

    def display_hint(self):
        return 'string'

class QLinkedListPrinter:
    """Print a Qt5 QLinkedList"""

    class Iter:
        def __init__(self, tail, size):
            self.current = tail
            self.i = -1
            self.size = size

        def __iter__(self):
            return self

        def __next__(self):
            if self.i + 1 >= self.size:
                raise StopIteration
            self.i += 1
            self.current = self.current['n']
            return (str(self.i), self.current['t'])

        def next(self):
            return self.__next__()

    def __init__(self, val):
        self.val = val

    def children(self):
        size = int(self.val['d']['size'])

        if size == 0:
            return []

        return self.Iter(self.val['e'], size)

    def to_string(self):
        # if we return an empty list from children, gdb doesn't print anything
        if self.val['d']['size'] == 0:
            return '<empty>'
        return None

    def display_hint(self):
        return 'array'

class QListPrinter:
    """Print a Qt5 QList"""

    class Iter:
        def __init__(self, array, begin, end, typ):
            self.array = array
            self.end = end
            self.begin = begin
            self.offset = 0
            if typ.name == 'QStringList':
                self.el_type = gdb.lookup_type('QString')
            else:
                self.el_type = typ.template_argument(0)

            if ((self.el_type.sizeof > gdb.lookup_type('void').pointer().sizeof)
                    or typeinfo.type_is_known_static(self.el_type)):
                self.is_pointer = True
            elif (typeinfo.type_is_known_movable(self.el_type) or
                    typeinfo.type_is_known_primitive(self.el_type)):
                self.is_pointer = False
            else:
                raise ValueError("Could not determine whether QList stores " +
                        self.el_type.name + " directly or as a pointer: to fix " +
                        "this, add it to one of the variables in the "+
                        "qt5printers.typeinfo module")
            self.node_type = gdb.lookup_type(typ.name + '::Node').pointer()

        def __iter__(self):
            return self

        def __next__(self):
            if self.begin + self.offset >= self.end:
                raise StopIteration
            node = self.array[self.begin + self.offset].reinterpret_cast(self.node_type)
            if self.is_pointer:
                p = node['v']
            else:
                p = node
            self.offset += 1
            value = p.address.cast(self.el_type.pointer()).dereference()
            return (str(self.offset), value)

        def next(self):
            return self.__next__()

    def __init__(self, val):
        self.val = val

    def children(self):
        d = self.val['d']
        begin = int(d['begin'])
        end = int(d['end'])

        if begin == end:
            return []

        return self.Iter(d['array'], begin, end, self.val.type.strip_typedefs())

    def to_string(self):
        # if we return an empty list from children, gdb doesn't print anything
        if self.val['d']['begin'] == self.val['d']['end']:
            return '<empty>'
        return None

    def display_hint(self):
        return 'array'

class QMapPrinter:
    """Print a Qt5 QMap"""

    class Iter:
        def __init__(self, root, node_p_type):
            self.root = root
            self.current = None
            self.node_p_type = node_p_type
            self.next_is_key = True
            self.i = -1
            # we store the path here to avoid keeping re-fetching
            # values from the inferior (also, skips the pointer
            # arithmetic involved in using the parent pointer)
            self.path = []

        def __iter__(self):
            return self

        def moveToNextNode(self):
            if self.current is None:
                # find the leftmost node
                if not self.root['left']:
                    return False
                self.current = self.root
                while self.current['left']:
                    self.path.append(self.current)
                    self.current = self.current['left']
            elif self.current['right']:
                self.path.append(self.current)
                self.current = self.current['right']
                while self.current['left']:
                    self.path.append(self.current)
                    self.current = self.current['left']
            else:
                last = self.current
                self.current = self.path.pop()
                while self.current['right'] == last:
                    last = self.current
                    self.current = self.path.pop()
                # if there are no more parents, we are at the root
                if len(self.path) == 0:
                    return False
            return True

        def __next__(self):
            if self.next_is_key:
                if not self.moveToNextNode():
                    raise StopIteration
                self.current_typed = self.current.reinterpret_cast(self.node_p_type)
                self.next_is_key = False
                self.i += 1
                return ('key' + str(self.i), self.current_typed['key'])
            else:
                self.next_is_key = True
                return ('value' + str(self.i), self.current_typed['value'])

        def next(self):
            return self.__next__()

    def __init__(self, val):
        self.val = val

    def children(self):
        d = self.val['d']
        size = int(d['size'])

        if size == 0:
            return []

        realtype = self.val.type.strip_typedefs()
        keytype = realtype.template_argument(0)
        valtype = realtype.template_argument(1)
        node_type = gdb.lookup_type('QMapData<' + keytype.name + ',' + valtype.name + '>::Node')

        return self.Iter(d['header'], node_type.pointer())

    def to_string(self):
        # if we return an empty list from children, gdb doesn't print anything
        if self.val['d']['size'] == 0:
            return '<empty>'
        return None

    def display_hint(self):
        return 'map'

class QSetPrinter:
    """Print a Qt5 QSet"""

    def __init__(self, val):
        self.val = val

    def children(self):
        hashPrinter = QHashPrinter(self.val['q_hash'])
        # the keys of the hash are the elements of the set, so select
        # every other item (starting with the first)
        return itertools.islice(hashPrinter.children(), 0, None, 2)

    def to_string(self):
        # if we return an empty list from children, gdb doesn't print anything
        if self.val['q_hash']['d']['size'] == 0:
            return '<empty>'
        return None

    def display_hint(self):
        return 'array'

class QStringPrinter:
    """Print a Qt5 QString"""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        d = self.val['d']
        data = d.reinterpret_cast(gdb.lookup_type('char').pointer()) + d['offset']
        data_len = d['size'] * gdb.lookup_type('unsigned short').sizeof
        return data.string('utf-16', 'replace', data_len)

    def display_hint(self):
        return 'string'

class QTimePrinter:
    """Print a Qt5 QTime"""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        msecs = int(self.val['mds'])
        if not _ms_is_valid(msecs):
            return '<invalid>'
        return _format_time_ms(msecs)

    def display_hint(self):
        return 'time'

class QTimeZonePrinter:
    """Print a Qt5 QTimeZone"""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        d = self.val['d']['d']
        if not d:
            return ''

        try:
            # Accessing the private data is error-prone,
            # so try just calling the id() method.
            # This should be reasonably safe, as all it will
            # do is create a QByteArray that references the
            # same internal data as the stored one. However,
            # it will only work with an attached process.
            m_id = gdb.parse_and_eval('((QTimeZone*){:})->id()'.format(self.val.address))
        except:
            ptr_size = gdb.lookup_type('void').pointer().sizeof
            try:
                qshareddata_t = gdb.lookup_type('QSharedData')
            except gdb.error:
                try:
                    # well, it only has a QAtomicInt in it
                    qshareddata_t = gdb.lookup_type('QAtomicInt')
                except gdb.error:
                    # let's hope it's the same size as an int
                    qshareddata_t = gdb.lookup_type('int')

            reader = StructReader(d)
            reader.next_val(gdb.lookup_type('void').pointer()) # vtable
            reader.next_val(qshareddata_t)
            m_id = reader.next_aligned_val(gdb.lookup_type('QByteArray'))

        return QByteArrayPrinter(m_id).to_string()

    def display_hint(self):
        return 'string'

class QVariantPrinter:
    """Print a Qt5 QVariant"""

    _varmap = {
        'char': 'c',
        'uchar': 'uc',
        'short': 's',
        'signed char': 'sc',
        'ushort': 'us',
        'int': 'i',
        'uint': 'u',
        'long': 'l',
        'ulong': 'ul',
        'bool': 'b',
        'double': 'd',
        'float': 'f',
        'qreal': 'real',
        'qlonglong': 'll',
        'qulonglong': 'ull',
        'QObject*': 'o',
        'void*': 'ptr'
    }

    def __init__(self, val):
        self.val = val

    def to_string(self):
        d = self.val['d']
        typ = int(d['type'])
        if typ == typeinfo.meta_type_unknown:
            return '<invalid type>'

        data = d['data']

        if typ in typeinfo.meta_type_names:
            typename = typeinfo.meta_type_names[typ]
            if typename in self._varmap:
                field = self._varmap[typename]
                return data[field]

            try:
                if typename.endswith('*'):
                    gdb_type = gdb.lookup_type(typename[0:-1]).pointer()
                else:
                    gdb_type = gdb.lookup_type(typename)
            except gdb.error:
                # couldn't find any type information
                return data

            if gdb_type.sizeof > data.type.sizeof:
                is_pointer = True
            elif (typeinfo.type_is_known_movable(gdb_type) or
                    typeinfo.type_is_known_primitive(gdb_type)):
                is_pointer = False
            elif gdb_type.tag == 'enum':
                is_pointer = False
            else:
                # couldn't figure out how the type is stored
                return data['o'].cast(gdb_type)

            if is_pointer:
                value = data['shared']['ptr'].reinterpret_cast(gdb_type.pointer())
            else:
                void_star = gdb.lookup_type('void').pointer()
                data_void = data['c'].address.reinterpret_cast(void_star)
                value = data_void.reinterpret_cast(gdb_type.pointer())

            return value.referenced_value()
        else:
            # custom type?
            return data

class QVarLengthArrayPrinter:
    """Print a Qt5 QVarLengthArray"""

    def __init__(self, val):
        self.val = val

    def children(self):
        size = int(self.val['s'])

        if size == 0:
            return []

        return ArrayIter(self.val['ptr'], size)

    def to_string(self):
        # if we return an empty list from children, gdb doesn't print anything
        if self.val['s'] == 0:
            return '<empty>'
        return None

    def display_hint(self):
        return 'array'

class QVectorPrinter:
    """Print a Qt5 QVector"""

    def __init__(self, val):
        self.val = val

    def children(self):
        d = self.val['d']
        el_type = self.val.type.template_argument(0)
        data_len = int(d['size'])

        if data_len == 0:
            return []

        data_char = d.reinterpret_cast(gdb.lookup_type('char').pointer()) + d['offset']
        data = data_char.reinterpret_cast(el_type.pointer())

        return ArrayIter(data, data_len)

    def to_string(self):
        # if we return an empty list from children, gdb doesn't print anything
        if self.val['d']['size'] == 0:
            return '<empty>'
        return None

    def display_hint(self):
        return 'array'

class QUrlPrinter:
    """Print a Qt5 QUrl"""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        d = self.val['d']
        if not d:
            return '<empty>'

        int_t = gdb.lookup_type('int')
        try:
            atomicint_t = gdb.lookup_type('QAtomicInt')
        except gdb.error:
            # let's hope it's the same size as an int
            atomicint_t = int_t
        qstring_t = gdb.lookup_type('QString')
        uchar_t = gdb.lookup_type('uchar')

        reader = StructReader(d)

        # These fields (including order) are unstable, and
        # may change between even patch-level Qt releases
        reader.next_val(atomicint_t)
        port = int(reader.next_val(int_t))
        scheme = reader.next_val(qstring_t)
        userName = reader.next_val(qstring_t)
        password = reader.next_val(qstring_t)
        host = reader.next_val(qstring_t)
        path = reader.next_val(qstring_t)
        query = reader.next_val(qstring_t)
        fragment = reader.next_val(qstring_t)
        reader.next_val(gdb.lookup_type('void').pointer())
        sections = int(reader.next_val(uchar_t))
        flags = int(reader.next_val(uchar_t))

        # isLocalFile and no query and no fragment
        if flags & 0x01 and not (sections & 0x40) and not (sections & 0x80):
            # local file
            return path

        def qs_to_s(qstring):
            return QStringPrinter(qstring).to_string()

        # QUrl::toString() is way more complicated than what we do here,
        # but this is good enough for debugging
        result = ''
        if sections & 0x01:
            result += qs_to_s(scheme) + ':'
        if sections & (0x02 | 0x04 | 0x08 | 0x10) or flags & 0x01:
            result += '//'
        if sections & 0x02 or sections & 0x04:
            result += qs_to_s(userName)
            if sections & 0x04:
                # this may appear in backtraces that will be sent to other
                # people
                result += ':<omitted>'
            result += '@'
        if sections & 0x08:
            result += qs_to_s(host)
        if port != -1:
            result += ':' + str(port)
        result += qs_to_s(path)
        if sections & 0x40:
            result += '?' + qs_to_s(query)
        if sections & 0x80:
            result += '#' + qs_to_s(fragment)
        return result

    def display_hint(self):
        return 'string'


def build_pretty_printer():
    """Builds the pretty printer for Qt5Core."""
    pp = gdb.printing.RegexpCollectionPrettyPrinter("Qt5Core")
    pp.add_printer('QBitArray', '^QBitArray$', QBitArrayPrinter)
    pp.add_printer('QByteArray', '^QByteArray$', QByteArrayPrinter)
    pp.add_printer('QChar', '^QChar$', QCharPrinter)
    pp.add_printer('QDate', '^QDate$', QDatePrinter)
    pp.add_printer('QDateTime', '^QDateTime$', QDateTimePrinter)
    pp.add_printer('QJsonArray', '^QJsonArray', QJsonArrayPrinter)
    pp.add_printer('QJsonObject', '^QJsonObject$', QJsonObjectPrinter)
    pp.add_printer('QLatin1String', '^QLatin1String$', QLatin1StringPrinter)
    pp.add_printer('QLinkedList', '^QLinkedList<.*>$', QLinkedListPrinter)
    pp.add_printer('QList', '^QList<.*>$', QListPrinter)
    pp.add_printer('QMap', '^QMap<.*>$', QMapPrinter)
    pp.add_printer('QHash', '^QHash<.*>$', QHashPrinter)
    pp.add_printer('QQueue', '^QQueue<.*>$', QListPrinter)
    pp.add_printer('QSet', '^QSet<.*>$', QSetPrinter)
    pp.add_printer('QStack', '^QStack<.*>$', QVectorPrinter)
    pp.add_printer('QString', '^QString$', QStringPrinter)
    pp.add_printer('QStringList', '^QStringList$', QListPrinter)
    pp.add_printer('QTime', '^QTime$', QTimePrinter)
    pp.add_printer('QTimeZone', '^QTimeZone$', QTimeZonePrinter)
    pp.add_printer('QVariant', '^QVariant$', QVariantPrinter)
    pp.add_printer('QVariantList', '^QVariantList$', QListPrinter)
    pp.add_printer('QVariantMap', '^QVariantMap$', QMapPrinter)
    pp.add_printer('QVector', '^QVector<.*>$', QVectorPrinter)
    pp.add_printer('QVarLengthArray', '^QVarLengthArray<.*>$', QVarLengthArrayPrinter)
    pp.add_printer('QUrl', '^QUrl$', QUrlPrinter)
    return pp

printer = build_pretty_printer()
"""The pretty printer for Qt5Core.

This can be registered using gdb.printing.register_pretty_printer().
"""
