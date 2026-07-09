# Implementation Plan: Order History

## Summary

Serve order history from the existing orders store, generating invoice PDFs on
demand within the storefront's existing session-auth boundary.

## Technical Context

- Language: follows the storefront's existing stack.
- Invoice rendering: server-side PDF generation, cached per order.
- [NEEDS CLARIFICATION: retention period for cached invoice PDFs]

## Constitution Check

PASS — single service, no new projects, reuses existing auth. No violations.

## Project Structure

### Source Code

- orders/history/ — list endpoint plus pagination.
- orders/invoices/ — PDF generation plus cache.
