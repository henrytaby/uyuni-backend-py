# Product Context - Uyuni Backend

## Problem Statement
Commercial ventures and enterprises (such as Nova Box Bolivia and white-label client businesses) need a robust, dedicated transactional ERP to manage:
- Commercial operations (products, imported batches, sales, live baskets, investment rounds)
- Inventory pricing rules (floor price protection via `minimum_price`, profit margins, break-even)
- User accounts and access control (RBAC with granular permissions and role impersonation)
- Audit trails for operations and security compliance (CDC)

## Solution
Uyuni Backend provides a high-performance RESTful API that enables:
1. **Secure Access**: JWT-based authentication with token rotation, logout revocation, and account lockout
2. **Granular Permissions**: RBAC system with CRUD permissions per module and dynamic domain manifests
3. **Commerce Management**: Atomic sales with Bolivian payment methods (QR, cash, carrier transfer), batches with landed cost tracking, SKU master records, and live catalog endpoints
4. **Account & Access Management**: User management, active role selection, and audit logging
5. **Audit Trail**: Automatic CDC logging of all entity modifications via SQLAlchemy hooks

## User Personas

### System Administrator
- Manages users, accounts, and security settings
- Configures global settings and monitors system health
- Reviews audit logs
- Full access to all modules

### Commercial / Store Manager
- Manages inventory SKUs, categories, and batches
- Registers sales and manages customer orders
- Tracks break-even points, profit margins, and sales channels
- Needs access to commerce module (`commerce_*`)

### Auditor / Operations
- Reviews audit trails and transaction histories
- Generates operational and financial reconciliation reports
- Read-only access to audit logs and sales data

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
3. System retrieves user's active role (supports `X-Active-Role` header)
4. System checks if role has required permission for module and action
5. If permitted: request proceeds
6. If denied: returns 403 Forbidden

### Commerce Sales Flow
1. User creates a sale with items, channel, and payment modality
2. System verifies price is at or above `minimum_price`
3. In a single atomic transaction: records sale, sale items, calculates net margin, and transitions product status to `vendido`

### Audit Logging Flow
1. Request enters audit middleware
2. Middleware captures request metadata (user, path, method, IP, user agent)
3. SQLAlchemy hooks capture entity changes (CDC)
4. Changes recorded in `audit_log` table
5. On error: logged but doesn't affect main transaction

## Technical Constraints
- Must support PostgreSQL database (with strict singular table naming convention)
- Compatible with Docker containers (Render), Serverless (Vercel), and VPS (Ubuntu)
- Must follow REST API conventions and strict type safety

## Integration Points
- Frontend Admin: Angular 21 + PrimeNG 21 (`uyuni-frontend-ng`)
- Public Customer Catalog: React + Vite PWA (`catalog-pwa`)
- Database: Dedicated PostgreSQL instance per tenant (Neon.tech / Render)
