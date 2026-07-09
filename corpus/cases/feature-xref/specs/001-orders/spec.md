# Feature Specification: Order History

## User Scenarios & Testing

### User Story 1 - View past orders (Priority: P1)

As a customer, I want to see my past orders so that I can reorder items I liked.

**Acceptance criteria**

- Given I have past orders, when I open order history, then I see my orders sorted
  newest-first with date, total, and status.

### User Story 2 - Download an invoice (Priority: P2)

As a customer, I want to download an invoice for an order so that I can file expenses.

**Acceptance criteria**

- Given a completed order, when I request its invoice, then I receive a PDF that
  matches the order's line items and totals.

### Edge Cases

- A customer with no orders sees an empty state with a link to the storefront.
- An order still in fulfilment shows no invoice link.

## Requirements

### Functional Requirements

- FR-001: The system shall list a customer's orders newest-first, 20 per page.
- FR-002: The system shall provide a PDF invoice for every completed order.

### Key Entities

- Order: id, customer_id, placed_at, status, total.
- Invoice: id, order_id, issued_at, pdf_uri.

## Success Criteria

### Measurable Outcomes

- 95% of order-history pages render within 800 ms.
- 100% of completed orders have a downloadable invoice.
