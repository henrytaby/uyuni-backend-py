# Product Context - Uyuni Backend

## Problem Statement
Organizations need a centralized system to manage:
- Organizational structure (units, positions, staff)
- Institutional assets (equipment, areas, groups, statuses)
- User authentication and authorization
- Audit trails for compliance and accountability

## Solution
Uyuni Backend provides a RESTful API that enables:
1. **Secure Access**: JWT-based authentication with token rotation and account lockout
2. **Granular Permissions**: RBAC system with CRUD permissions per module
3. **Asset Management**: Complete CRUD operations for assets, areas, groups, institutions, statuses, and acts
4. **Organizational Management**: Management of org units, positions, and staff assignments
5. **Audit Trail**: Automatic logging of all data changes for compliance

## User Personas

### System Administrator
- Manages users, roles, and permissions
- Configures system settings
- Reviews audit logs
- Needs full access to all modules

### Asset Manager
- Manages institutional assets
- Organizes assets into areas and groups
- Tracks asset statuses
- Needs read/write access to assets module

### Staff Manager
- Manages organizational units
- Assigns positions and staff
- Needs access to core module (org_units, positions, staff)

### Auditor
- Reviews audit trails
- Generates compliance reports
- Needs read-only access to audit data

## Key Workflows

### User Authentication Flow
1. User submits credentials (username/password)
2. System validates credentials and checks lockout status
3. On success: returns access token (15min) and refresh token (7 days)
4. On failure: increments failed attempts, locks account after 5 failures
5. Access token used for API requests
6. Refresh token used to obtain new access token

### RBAC Permission Check Flow
1. User makes request to protected endpoint
2. System extracts user from JWT token
3. System retrieves user's active role
4. System checks if role has required permission for module and action
5. If permitted: request proceeds
6. If denied: returns 403 Forbidden

### Audit Logging Flow
1. Request enters audit middleware
2. Middleware captures request metadata (user, path, method)
3. SQLAlchemy hooks capture entity changes
4. Changes recorded in audit_entries table
5. On error: logged but doesn't affect main transaction

## Technical Constraints
- Must support PostgreSQL database
- Must be compatible with Vercel serverless deployment
- Must follow REST API conventions
- Must maintain backward compatibility for API versions

## Integration Points
- Frontend: React/Next.js application consuming the API
- Database: PostgreSQL instance
- Authentication: Internal JWT system (no external OAuth providers)
- Logging: Structured logs for observability platforms
