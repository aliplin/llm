from enum import Enum


class Capability(Enum):
    LONG_PASSWORD                  = 0x00000001
    FOUND_ROWS                     = 0x00000002
    LONG_FLAG                      = 0x00000004
    CONNECT_WITH_DB                = 0x00000008
    NO_SCHEMA                      = 0x00000010
    PROTOCOL_41                    = 0x00000200
    TRANSACTIONS                   = 0x00002000
    SECURE_CONNECTION              = 0x00008000
    PLUGIN_AUTH                    = 0x00080000
    CONNECT_ATTRS                  = 0x00100000
    PLUGIN_AUTH_LENENC_CLIENT_DATA = 0x00200000
    SESSION_TRACK                  = 0x00800000
    DEPRECATE_EOF                  = 0x01000000


class Status(Enum):
    STATUS_IN_TRANS             = 0x0001
    STATUS_AUTOCOMMIT           = 0x0002
    MORE_RESULTS_EXISTS         = 0x0008
    STATUS_NO_GOOD_INDEX_USED   = 0x0010
    STATUS_NO_INDEX_USED        = 0x0020
    STATUS_CURSOR_EXISTS        = 0x0040
    STATUS_LAST_ROW_SENT        = 0x0080
    STATUS_DB_DROPPED           = 0x0100
    STATUS_NO_BACKSLASH_ESCAPES = 0x0200
    STATUS_METADATA_CHANGED     = 0x0400
    QUERY_WAS_SLOW              = 0x0800
    PS_OUT_PARAMS               = 0x1000
    STATUS_IN_TRANS_READONLY    = 0x2000
    SESSION_STATE_CHANGED       = 0x4000

#https://dev.mysql.com/doc/internals/en/character-set.html#packet-Protocol::CharacterSet
class CharacterSet(Enum):
    # 基础字符集
    latin1_swedish_ci = 0x08
    utf8 = 0x21
    utf8_general_ci = 0x21  # 别名
    binary = 0x3f
    
    # utf8mb4字符集
    utf8mb4_general_ci = 0x2d
    utf8mb4_unicode_ci = 0x2e
    utf8mb4_0900_ai_ci = 0x2f
    utf8mb4_0900_as_ci = 0x30
    utf8mb4_0900_as_cs = 0x31
    utf8mb4_0900_bin = 0x32
    utf8mb4_bin = 0x33
    utf8mb4_croatian_ci = 0x34
    utf8mb4_czech_ci = 0x35
    utf8mb4_danish_ci = 0x36
    utf8mb4_esperanto_ci = 0x37
    utf8mb4_estonian_ci = 0x38
    utf8mb4_german2_ci = 0x39
    utf8mb4_hungarian_ci = 0x3a
    utf8mb4_icelandic_ci = 0x3b
    utf8mb4_latvian_ci = 0x3c
    utf8mb4_lithuanian_ci = 0x3d
    utf8mb4_persian_ci = 0x3e
    utf8mb4_polish_ci = 0x40
    utf8mb4_romanian_ci = 0x41
    utf8mb4_sinhala_ci = 0x43
    utf8mb4_slovak_ci = 0x44
    utf8mb4_slovenian_ci = 0x45
    utf8mb4_spanish2_ci = 0x46
    utf8mb4_spanish_ci = 0x47
    utf8mb4_swedish_ci = 0x48
    utf8mb4_turkish_ci = 0x49
    utf8mb4_unicode_520_ci = 0x4a
    utf8mb4_vietnamese_ci = 0x4b
    
    # 数值映射（用于处理客户端发送的未知值）
    utf8_28 = 0x1c
    utf8_29 = 0x1d
    utf8_30 = 0x1e
    utf8_31 = 0x1f
    utf8_32 = 0x20
    utf8_33 = 0x21  # 标准utf8
    utf8_34 = 0x22
    utf8_35 = 0x23
    utf8_36 = 0x24
    utf8_37 = 0x25
    utf8_38 = 0x26
    utf8_39 = 0x27
    utf8_40 = 0x28  # 客户端发送的值
    utf8_41 = 0x29
    utf8_42 = 0x2a
    utf8_43 = 0x2b
    utf8_44 = 0x2c
    utf8_45 = 0x2d
    utf8_46 = 0x2e
    utf8_47 = 0x2f
    utf8_48 = 0x30
    utf8_49 = 0x31
    utf8_50 = 0x32
    utf8_51 = 0x33
    utf8_52 = 0x34
    utf8_53 = 0x35
    utf8_54 = 0x36
    utf8_55 = 0x37
    utf8_56 = 0x38
    utf8_57 = 0x39
    utf8_58 = 0x3a
    utf8_59 = 0x3b
    utf8_60 = 0x3c
    utf8_61 = 0x3d
    utf8_62 = 0x3e
    utf8_63 = 0x3f  # binary


class _EnumSet(set):
    __slots__ = ()

    @property
    def int(self):
        ret = 0
        for i in self:
            ret |= i.value
        return ret

    @int.setter
    def int(self, data):
        self.clear()
        for i in Capability:
            if i.value & data:
                self.add(i)


class CapabilitySet(_EnumSet):
    __slots__ = ()


class StatusSet(_EnumSet):
    __slots__ = ()
    enum = Status
