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

"""Qt5 Type Information

Since the QTypeInfo information is not necessarily available at debug time, this
module contains useful type information about standard and Qt types (such as
whether a type is movable) that is necessary for the operation of the printers.
This information allows the QList printer, for example, to determine how the
elements are stored in the list.
"""

primitive_types = set([
    'HB_FixedPoint',
    'HB_GlyphAttributes',
    'QCharAttributes',
    'QFlag',
    'QIncompatibleFlag',
    'QRegExpAnchorAlternation',
    'QRegExpAtom',
    'QRegExpCharClassRange',
    'QStaticPlugin',
    'QStringRef',
    'QTzType',
    'QUuid'
    ])
"""Primitive (non-template) types.

This does not need to include compiler-primitive types (like int).

If you use the Q_DECLARE_TYPEINFO macro with Q_PRIMITIVE_TYPE flag, you
should add the type to this set. This is particularly important for
types that are the same size as a pointer or smaller.
"""

primitive_tpl_types = set(['QFlags'])
"""Primitive template types.

If you use the Q_DECLARE_TYPEINFO_BODY macro with Q_PRIMITIVE_TYPE flag
on a type with template parameters, you should add the type to this
set. This is particularly important for types that are the same size as
a pointer or smaller.

Entries should just be the base typename, without any template
parameters (eg: "QFlags", rather than "QFlags<T>").
"""

movable_types = set([
    'QBasicTimer',
    'QBitArray',
    'QByteArray',
    'QChar',
    'QCharRef',
    'QCustomTypeInfo',
    'QDate',
    'QDateTime',
    'QFileInfo',
    'QEasingCurve',
    'QFileSystemWatcherPathKey',
    'QHashDummyValue',
    'QItemSelectionRange',
    'QLatin1String',
    'QLine',
    'QLineF',
    'QLocale',
    'QLoggingRule',
    'QMargins',
    'QMarginsF',
    'QMetaClassInfo',
    'QMetaEnum',
    'QMetaMethod',
    'QMimeMagicRule',
    'QModelIndex',
    'QPersistentModelIndex',
    'QObjectPrivate::Connection',
    'QObjectPrivate::Sender',
    'QPoint',
    'QPointF',
    'QPostEvent',
    'QProcEnvKey',
    'QProcEnvValue',
    'QRect',
    'QRectF',
    'QRegExp',
    'QRegExpAutomatonState',
    'QRegExpCharClass',
    'QResourceRoot',
    'QSize',
    'QSizeF',
    'QString',
    'QStringList',
    'QTime',
    'QTimeZone::OffsetData',
    'QUrl',
    'QVariant',
    'QXmlStreamAttribute',
    'QXmlStreamEntityDeclaration',
    'QXmlStreamNamespaceDeclaration',
    'QXmlStreamNotationDeclaration'
    ])
"""Movable (non-template) types.

If you use the Q_DECLARE_TYPEINFO macro with Q_MOVABLE_TYPE flag, you
should add the type to this set. This is particularly important for
types that are the same size as a pointer or smaller.
"""

movable_tpl_types = set([
    'QExplicitlySharedDataPointer',
    'QLinkedList',
    'QList',
    'QPointer',
    'QQueue',
    'QSet',
    'QSharedDataPointer',
    'QSharedPointer',
    'QStack',
    'QVector',
    'QWeakPointer'
    ])
"""Movable template types.

If you use the Q_DECLARE_TYPEINFO_BODY macro with Q_MOVABLE_TYPE flag
on a type with template parameters, you should add the type to this
set. This is particularly important for types that are the same size as
a pointer or smaller.

Entries should just be the base typename, without any template
parameters (eg: "QFlags", rather than "QFlags<T>").
"""

static_types = set()
"""Static (non-template) types.

If you define a custom type that is neither primitive nor movable, you
can add the type to this set to indicate this. This is particularly
important for types that are the same size as a pointer or smaller.
"""

static_tpl_types = set()
"""Static template types.

If you define a custom type with template parameters that is neither
primitive nor movable, you can add the type to this set to indicate
this. This is particularly important for types that are the same size as
a pointer or smaller.

Entries should just be the base typename, without any template
parameters (eg: "QFlags", rather than "QFlags<T>").
"""

def type_is_known_primitive(typ):
    """Returns True if the given gdb type is known to be primitive."""
    if typ.code == gdb.TYPE_CODE_PTR or typ.code == gdb.TYPE_CODE_INT or typ.code == gdb.TYPE_CODE_FLT or typ.code == gdb.TYPE_CODE_CHAR or typ.code == gdb.TYPE_CODE_BOOL:
        return True
    pos = typ.name.find('<')
    if pos > 0:
        return typ.name[0:pos] in primitive_tpl_types
    else:
        return typ.name in primitive_types

def type_is_known_movable(typ):
    """Returns True if the given gdb type is known to be movable."""
    if not typ.name:
        return False
    pos = typ.name.find('<')
    if pos > 0:
        return typ.name[0:pos] in movable_tpl_types
    else:
        return typ.name in movable_types

def type_is_known_static(typ):
    """Returns True if the given gdb type is known to be neither primitive nor movable."""
    if not typ.name:
        return False
    pos = typ.name.find('<')
    if pos > 0:
        return typ.name[0:pos] in static_tpl_types
    else:
        return typ.name in static_types

meta_type_unknown = 0
"""The unknown/invalid meta type ID."""
meta_type_user = 1024
"""The starting value for custom type IDs."""
meta_type_ids = {
    'bool': 1,
    'int': 2,
    'uint': 3,
    'qlonglong': 4,
    'qulonglong': 5,
    'double': 6,
    'QChar': 7,
    'QVariantMap': 8,
    'QVariantList': 9,
    'QString': 10,
    'QStringList': 11,
    'QByteArray': 12,
    'QBitArray': 13,
    'QDate': 14,
    'QTime': 15,
    'QDateTime': 16,
    'QUrl': 17,
    'QLocale': 18,
    'QRect': 19,
    'QRectF': 20,
    'QSize': 21,
    'QSizeF': 22,
    'QLine': 23,
    'QLineF': 24,
    'QPoint': 25,
    'QPointF': 26,
    'QRegExp': 27,
    'QVariantHash': 28,
    'QEasingCurve': 29,
    'QUuid': 30,
    'void*': 31,
    'long': 32,
    'short': 33,
    'char': 34,
    'ulong': 35,
    'ushort': 36,
    'uchar': 37,
    'float': 38,
    'QObject*': 39,
    'signed char': 40,
    'QVariant': 41,
    'QModelIndex': 42,
    'void': 43,
    'QRegularExpression': 44,
    'QJsonValue': 45,
    'QJsonObject': 46,
    'QJsonArray': 47,
    'QJsonDocument': 48,
    'QFont': 64,
    'QPixmap': 65,
    'QBrush': 66,
    'QColor': 67,
    'QPalette': 68,
    'QIcon': 69,
    'QImage': 70,
    'QPolygon': 71,
    'QRegion': 72,
    'QBitmap': 73,
    'QCursor': 74,
    'QKeySequence': 75,
    'QPen': 76,
    'QTextLength': 77,
    'QTextFormat': 78,
    'QMatrix': 79,
    'QTransform': 80,
    'QMatrix4x4': 81,
    'QVector2D': 82,
    'QVector3D': 83,
    'QVector4D': 84,
    'QQuaternion': 85,
    'QPolygonF': 86,
    'QSizePolicy': 121
}
"""Map from type names to meta type IDs."""
meta_type_names = {
    1: 'bool',
    2: 'int',
    3: 'uint',
    4: 'qlonglong',
    5: 'qulonglong',
    6: 'double',
    7: 'QChar',
    8: 'QVariantMap',
    9: 'QVariantList',
    10: 'QString',
    11: 'QStringList',
    12: 'QByteArray',
    13: 'QBitArray',
    14: 'QDate',
    15: 'QTime',
    16: 'QDateTime',
    17: 'QUrl',
    18: 'QLocale',
    19: 'QRect',
    20: 'QRectF',
    21: 'QSize',
    22: 'QSizeF',
    23: 'QLine',
    24: 'QLineF',
    25: 'QPoint',
    26: 'QPointF',
    27: 'QRegExp',
    28: 'QVariantHash',
    29: 'QEasingCurve',
    30: 'QUuid',
    31: 'void*',
    32: 'long',
    33: 'short',
    34: 'char',
    35: 'ulong',
    36: 'ushort',
    37: 'uchar',
    38: 'float',
    39: 'QObject*',
    40: 'signed char',
    41: 'QVariant',
    42: 'QModelIndex',
    43: 'void',
    44: 'QRegularExpression',
    45: 'QJsonValue',
    46: 'QJsonObject',
    47: 'QJsonArray',
    48: 'QJsonDocument',
    64: 'QFont',
    65: 'QPixmap',
    66: 'QBrush',
    67: 'QColor',
    68: 'QPalette',
    69: 'QIcon',
    70: 'QImage',
    71: 'QPolygon',
    72: 'QRegion',
    73: 'QBitmap',
    74: 'QCursor',
    75: 'QKeySequence',
    76: 'QPen',
    77: 'QTextLength',
    78: 'QTextFormat',
    79: 'QMatrix',
    80: 'QTransform',
    81: 'QMatrix4x4',
    82: 'QVector2D',
    83: 'QVector3D',
    84: 'QVector4D',
    85: 'QQuaternion',
    86: 'QPolygonF',
    121: 'QSizePolicy'
}
"""Map from meta type IDs to type names."""
