class RoleTypes:
    ADMIN = "ADMIN"
    ROOT = "ROOT"
    USER = "USER"
    SOPORT = "SOPORT"


class UserStatusTypes:
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DELETED = "DELETED"


class AssignmentStatusTypes:
    PENDING = "PENDING"
    INSPECTED = "INSPECTED"
    REDISCOVERED = "REDISCOVERED"
    EQUIPMENT_DOWN = "EQUIPMENT_DOWN"


class SnmpModeTypes:
    LEGACY = "legacy"
    MODERN = "modern"
