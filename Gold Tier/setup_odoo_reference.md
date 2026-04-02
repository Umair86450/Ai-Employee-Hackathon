# Odoo 19 Setup Reference

This file is the working reference for the local Odoo setup used in the Gold Tier hackathon project for the Digital AI Employee flow.

## Purpose

Use this document when you need to:

- understand how Odoo was installed locally
- restart the stack
- verify the `AI_Employee_Business` database
- recover the API bot user
- regenerate the API key
- locate the custom no-delete security logic

## Environment

- Host: macOS
- Runtime: Docker
- Odoo version: `19.0`
- Database: `AI_Employee_Business`
- Odoo URL: `http://localhost:8069`

## Local Stack Files

- Docker stack: [odoo19-local/docker-compose.yml](/Users/mac/Desktop/P/Silver Tier/Ai-Employee-Hackathon/Gold Tier/odoo19-local/docker-compose.yml)
- Odoo config: [odoo19-local/config/odoo.conf](/Users/mac/Desktop/P/Silver Tier/Ai-Employee-Hackathon/Gold Tier/odoo19-local/config/odoo.conf)
- Helper script: [odoo19-local/manage.sh](/Users/mac/Desktop/P/Silver Tier/Ai-Employee-Hackathon/Gold Tier/odoo19-local/manage.sh)

## Custom Security Module

This custom module was added to enforce "Accounting access but no delete" for the bot user.

- Manifest: [odoo19-local/odoo-data/addons/19.0/ai_employee_accounting_guard/__manifest__.py](/Users/mac/Desktop/P/Silver Tier/Ai-Employee-Hackathon/Gold Tier/odoo19-local/odoo-data/addons/19.0/ai_employee_accounting_guard/__manifest__.py)
- Python logic: [odoo19-local/odoo-data/addons/19.0/ai_employee_accounting_guard/models/no_delete_guard.py](/Users/mac/Desktop/P/Silver Tier/Ai-Employee-Hackathon/Gold Tier/odoo19-local/odoo-data/addons/19.0/ai_employee_accounting_guard/models/no_delete_guard.py)
- Security group XML: [odoo19-local/odoo-data/addons/19.0/ai_employee_accounting_guard/security/security.xml](/Users/mac/Desktop/P/Silver Tier/Ai-Employee-Hackathon/Gold Tier/odoo19-local/odoo-data/addons/19.0/ai_employee_accounting_guard/security/security.xml)

## Current Odoo State

The following were created and verified in `AI_Employee_Business`:

- Company country: `PK`
- Company currency: `PKR`
- 10 accounting accounts
- 3 test customers
- 3 test service products
- 3 posted customer invoices
- 1 API bot user with accounting access
- no-delete guard enabled for that bot user

## Test Records Created

### Accounts

- `1000` Cash in Hand PK
- `1010` Meezan Bank PK
- `1100` Accounts Receivable PK
- `2000` Accounts Payable PK
- `3000` Owner Capital PK
- `4000` Sales Revenue PK
- `5000` Cost of Revenue PK
- `6100` Salaries Expense PK
- `6200` Rent Expense PK
- `6300` Utilities Expense PK

### Customers

- `ABC Traders`
- `Karachi Retail`
- `Lahore Distribution`

### Products

- `AI Employee Subscription` = `50000 PKR`
- `AI Employee Setup Fee` = `120000 PKR`
- `Support Retainer` = `30000 PKR`

### Invoices

- `INV/2026/00001` ref `TEST-INV-ABC-001` = `170000 PKR`
- `INV/2026/00002` ref `TEST-INV-KHI-001` = `30000 PKR`
- `INV/2026/00003` ref `TEST-INV-LHE-001` = `100000 PKR`

## Odoo Web Login

Open:

```text
http://localhost:8069
```

Use database:

```text
AI_Employee_Business
```

## Bot User Reference

The bot user created for JSON-2 integration is:

- Login: `api.bot@local`

Do not treat the originally displayed password or API key as permanent secrets. Rotate them if this environment is used beyond demo or hackathon testing.

## Start / Stop Commands

```bash
cd "/Users/mac/Desktop/P/Silver Tier/Ai-Employee-Hackathon/Gold Tier/odoo19-local"
./manage.sh up
./manage.sh down
./manage.sh logs
```

## Check Container Status

```bash
cd "/Users/mac/Desktop/P/Silver Tier/Ai-Employee-Hackathon/Gold Tier/odoo19-local"
docker compose ps
```

## Reset Bot Password

Use this if the bot password is forgotten.

```bash
docker exec -i odoo19-web odoo shell -d AI_Employee_Business -c /etc/odoo/odoo.conf <<'PY'
user = env["res.users"].sudo().search([("login", "=", "api.bot@local")], limit=1)
if not user:
    raise Exception("User not found")
user.write({"password": "NewStrongPass123!"})
env.cr.commit()
print("password reset done for", user.login)
PY
```

## Generate a New API Key

Important:

- Odoo stores API keys hashed.
- A previously generated raw key cannot be viewed again in plain text.
- If the key is lost, generate a new one.

```bash
docker exec -i odoo19-web odoo shell -d AI_Employee_Business -c /etc/odoo/odoo.conf <<'PY'
import datetime as dt

login = "api.bot@local"
user = env["res.users"].sudo().search([("login", "=", login)], limit=1)
if not user:
    raise Exception("User not found")

expires = dt.datetime.utcnow() + dt.timedelta(days=365)

key = env["res.users.apikeys"].with_user(user).sudo()._generate(
    scope="rpc",
    name="JSON-2 Bot Key",
    expiration_date=expires,
)

env.cr.commit()
print("login =", login)
print("api_key =", key)
print("expires_utc =", expires.isoformat())
PY
```

## JSON-2 Test Call

Replace `YOUR_API_KEY_HERE` with the newly generated key.

```bash
export ODOO_API_KEY='YOUR_API_KEY_HERE'

curl -X POST "http://localhost:8069/json/2/res.partner/search_read" \
  -H "Authorization: bearer ${ODOO_API_KEY}" \
  -H "X-Odoo-Database: AI_Employee_Business" \
  -H "Content-Type: application/json" \
  -d '{"domain":[["is_company","=",true]],"fields":["name","email"],"context":{"lang":"en_US"}}'
```

## Verify Setup from Odoo Shell

```bash
docker exec -i odoo19-web odoo shell -d AI_Employee_Business -c /etc/odoo/odoo.conf <<'PY'
user = env["res.users"].search([("login", "=", "api.bot@local")], limit=1)
print(
    "VERIFY_COUNTS",
    env["account.account"].search_count([("code", "in", ["1000","1010","1100","2000","3000","4000","5000","6100","6200","6300"])]),
    env["res.partner"].search_count([("name", "in", ["ABC Traders", "Karachi Retail", "Lahore Distribution"])]),
    env["product.template"].search_count([("name", "in", ["AI Employee Subscription", "AI Employee Setup Fee", "Support Retainer"])]),
    env["account.move"].search_count([("ref", "in", ["TEST-INV-ABC-001", "TEST-INV-KHI-001", "TEST-INV-LHE-001"]), ("state", "=", "posted")]),
)
print("VERIFY_USER", user.login, sorted(user.group_ids.mapped("display_name")))
PY
```

Expected result:

- 10 accounts
- 3 customers
- 3 products
- 3 posted invoices
- user groups include:
  - `Accounting / Administrator`
  - `Accounting No Delete`
  - `Role / User`

## Odoo Web Path for Bot User

Inside Odoo:

1. Go to `Settings`
2. Open `Users & Companies`
3. Open `Users`
4. Search `API Bot`

There you can confirm:

- login
- groups
- company

## Why This Matters for Gold Tier

This Odoo setup gives the hackathon project:

- a local ERP backend
- accounting entities in PKR
- test customers and invoices for automation demos
- a machine user for JSON-2 integrations
- a security guard that blocks destructive deletes by the bot

That is the base needed for a Digital AI Employee demo where the AI agent can read and create accounting records without being allowed to delete them.
