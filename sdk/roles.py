"""
SAP SDK - Roles and Permissions

Role-based access control for Admin and Delegate operations.
Enforces least-privilege principle at the SDK level.
"""

from enum import Enum
from typing import Set
from dataclasses import dataclass

from .errors import SAPError


class PermissionError(SAPError):
    """Operation not allowed for the current role."""
    
    def __init__(self, role: "Role", operation: str):
        super().__init__(
            f"Role '{role.value}' is not allowed to perform '{operation}'",
            {"role": role.value, "operation": operation}
        )
        self.role = role
        self.operation = operation


class Role(Enum):
    """
    User roles in the SAP system.
    
    ADMIN: Root authority with full control
    - Can drain vault (deactivate delegate)
    - Can revoke any certificate
    - Can issue certificates (but typically delegates this)
    
    DELEGATE: Delegated authority for day-to-day operations
    - Can issue certificates
    - Can revoke certificates they issued
    - Cannot drain vault or access admin functions
    """
    ADMIN = "admin"
    DELEGATE = "delegate"


@dataclass(frozen=True)
class Permission:
    """A permission for an operation."""
    name: str
    description: str


class Permissions:
    """Available permissions in the SAP system."""
    
    # Vault operations
    VAULT_READ = Permission("vault:read", "Read vault balance and UTXOs")
    VAULT_DRAIN = Permission("vault:drain", "Drain vault (deactivate delegate)")
    
    # Certificate operations
    CERT_ISSUE = Permission("cert:issue", "Issue new certificates")
    CERT_REVOKE_OWN = Permission("cert:revoke_own", "Revoke own certificates")
    CERT_REVOKE_ANY = Permission("cert:revoke_any", "Revoke any certificate")
    CERT_READ = Permission("cert:read", "Read certificate status")
    CERT_LIST = Permission("cert:list", "List certificates")
    
    # Fee operations
    FEE_ESTIMATE = Permission("fee:estimate", "Estimate transaction fees")


# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permissions.VAULT_READ,
        Permissions.VAULT_DRAIN,
        Permissions.CERT_ISSUE,
        Permissions.CERT_REVOKE_OWN,
        Permissions.CERT_REVOKE_ANY,
        Permissions.CERT_READ,
        Permissions.CERT_LIST,
        Permissions.FEE_ESTIMATE,
    },
    Role.DELEGATE: {
        Permissions.VAULT_READ,
        # No VAULT_DRAIN
        Permissions.CERT_ISSUE,
        Permissions.CERT_REVOKE_OWN,
        # No CERT_REVOKE_ANY
        Permissions.CERT_READ,
        Permissions.CERT_LIST,
        Permissions.FEE_ESTIMATE,
    },
}


def has_permission(role: Role, permission: Permission) -> bool:
    """
    Check if a role has a specific permission.
    
    Args:
        role: The user's role.
        permission: The permission to check.
    
    Returns:
        True if the role has the permission.
    """
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(role: Role, permission: Permission, operation: str) -> None:
    """
    Require a permission or raise PermissionError.
    
    Args:
        role: The user's role.
        permission: The required permission.
        operation: Name of the operation being attempted.
    
    Raises:
        PermissionError: If the role lacks the permission.
    """
    if not has_permission(role, permission):
        raise PermissionError(role, operation)


class RoleContext:
    """
    Context manager for role-based operations.
    
    Tracks the current role and validates permissions.
    
    Example:
        ctx = RoleContext(Role.DELEGATE)
        
        ctx.require(Permissions.CERT_ISSUE, "issue_certificate")  # OK
        ctx.require(Permissions.VAULT_DRAIN, "drain_vault")  # Raises PermissionError
    """
    
    def __init__(self, role: Role):
        """
        Initialize role context.
        
        Args:
            role: The role for this context.
        """
        self.role = role
        self._permissions = ROLE_PERMISSIONS.get(role, set())
    
    def has(self, permission: Permission) -> bool:
        """Check if context has permission."""
        return permission in self._permissions
    
    def require(self, permission: Permission, operation: str) -> None:
        """Require permission or raise error."""
        require_permission(self.role, permission, operation)
    
    @property
    def can_drain_vault(self) -> bool:
        """Check if can drain vault."""
        return self.has(Permissions.VAULT_DRAIN)
    
    @property
    def can_issue(self) -> bool:
        """Check if can issue certificates."""
        return self.has(Permissions.CERT_ISSUE)
    
    @property
    def can_revoke_any(self) -> bool:
        """Check if can revoke any certificate."""
        return self.has(Permissions.CERT_REVOKE_ANY)
    
    def __repr__(self) -> str:
        return f"RoleContext(role={self.role.value})"
