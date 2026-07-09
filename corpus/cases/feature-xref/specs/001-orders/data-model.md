# Data Model: Order History

## Entities

### Order

- id, customer_id, placed_at, status, total.

### Invoice

- id, order_id, issued_at, pdf_uri; generated on first download, then cached.
