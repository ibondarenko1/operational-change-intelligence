from enum import StrEnum


class Environment(StrEnum):
    entra_id = "entra_id"
    microsoft_365 = "microsoft_365"
    defender = "defender"
    azure = "azure"
    other = "other"


class ChangeType(StrEnum):
    mfa_rollout = "mfa_rollout"
    conditional_access = "conditional_access"
    legacy_authentication_block = "legacy_authentication_block"
    admin_role_change = "admin_role_change"
    guest_access_change = "guest_access_change"
    defender_policy_change = "defender_policy_change"
    device_compliance = "device_compliance"
    password_policy = "password_policy"
    other = "other"


class ChangeStatus(StrEnum):
    draft = "draft"
    analyzing = "analyzing"
    review_required = "review_required"
    approved = "approved"
    rejected = "rejected"
    completed = "completed"
    failed = "failed"
