# Open WebUI Tools Guide

This guide is for Open WebUI users who interact with the PH Agent Framework tools in chat.

## Who this is for

Use this guide if you are:
- Chatting in Open WebUI and want to know what tools are available
- Trying to ask better prompts so the assistant picks the right tool
- Working with ERPNext records, reports, or attachments

## How tool use works in Open WebUI

1. You ask a normal question in chat.
2. The assistant decides whether a tool call is needed.
3. The tool runs against PH Agent Framework.
4. The assistant returns the result in plain language.

You usually do not call the tool manually. Your job is to provide a clear intent, doctype names, IDs, dates, and filters.

## Prompting tips

- Include the exact doctype when possible (for example: `Sales Invoice`, `Customer`, `Item`).
- Include document IDs when you know them (for example: `SINV-24-00001`).
- For searches, include filter conditions (status, date range, customer, amount).
- For reports, include report name and date/company filters.
- For updates, state exactly which fields should change.

## Write safety rule

- Treat `erpnext_get_fieldset` as guidance for common patterns.
- Treat `erpnext_get_doctype_meta` as authoritative when writing data.
- After `erpnext_create_doc` or `erpnext_update_doc`, always ask for a verification read (`erpnext_get_doc` or `erpnext_search_docs`) before declaring success.

## Available tools

### System

- `system_ping`
  - Purpose: Check if the tool server is responsive.
  - Ask like: "Check if the system is up."

### Utility

- `server_datetime`
  - Purpose: Get current server date/time (supports timezone input).
  - Ask like: "What is the current server time in Europe/Athens?"

### ERPNext Discovery and Metadata

- `erpnext_ping`
  - Purpose: Verify ERPNext is reachable.
  - Ask like: "Check ERPNext connectivity."

- `erpnext_get_system_info`
  - Purpose: Show installed ERPNext/Frappe apps and versions.
  - Ask like: "Show ERPNext system info and installed apps."

- `erpnext_list_doctypes`
  - Purpose: Discover available doctypes.
  - Ask like: "List sales-related doctypes."

- `erpnext_get_doctype_meta`
  - Purpose: Show full doctype schema and field definitions.
  - Ask like: "Show field metadata for Sales Invoice."

- `erpnext_get_fieldset`
  - Purpose: Get curated field templates for common doctypes.
  - Ask like: "Show me the required fields for creating a Sales Order."

### ERPNext Document Operations

- `erpnext_get_doc`
  - Purpose: Retrieve one document by doctype and docname.
  - Ask like: "Get Sales Invoice SINV-24-00001."

- `erpnext_search_docs`
  - Purpose: Search documents using filters, sorting, pagination.
  - Ask like: "Find open Sales Orders for customer Test Corp from last month."

- `erpnext_count_docs`
  - Purpose: Count matching documents quickly.
  - Ask like: "How many overdue Sales Invoices do we have?"

- `erpnext_create_doc`
  - Purpose: Create a new document.
  - Ask like: "Create a new Customer named Test Corp in Greece."

- `erpnext_update_doc`
  - Purpose: Update fields on an existing draft document.
  - Ask like: "Update Sales Order SO-2025-00012 delivery date to 2026-05-10."

- `erpnext_delete_doc`
  - Purpose: Delete a draft/cancelled document.
  - Ask like: "Delete draft quotation QTN-2026-00003."

### ERPNext Document Lifecycle

- `erpnext_submit_doc`
  - Purpose: Submit a draft document (docstatus 0 -> 1).
  - Ask like: "Submit Sales Invoice SINV-24-00001."

- `erpnext_cancel_doc`
  - Purpose: Cancel a submitted document (docstatus 1 -> 2).
  - Ask like: "Cancel Sales Invoice SINV-24-00001."

- `erpnext_amend_doc`
  - Purpose: Create corrected draft from a cancelled document.
  - Ask like: "Amend cancelled Sales Invoice SINV-24-00001 and change due date."

### ERPNext Files and Attachments

- `erpnext_upload_file`
  - Purpose: Upload text content as a file, optionally attached to a document.
  - Ask like: "Save these notes as a text attachment to Customer Test Corp."
  - Note: This is for text content. For binary chat attachments (PDF/images), use the `upload_file_to_erpnext` bridge tool in Open WebUI.

- `erpnext_list_attachments`
  - Purpose: List files attached to a document.
  - Ask like: "List attachments on Sales Invoice SINV-24-00001."

- `erpnext_get_file`
  - Purpose: Get metadata for a file URL.
  - Ask like: "Show file details for /files/invoice.pdf."

### ERPNext Reports

- `erpnext_list_reports`
  - Purpose: Discover available reports.
  - Ask like: "List reports related to Accounts Receivable."

- `erpnext_run_report`
  - Purpose: Execute an ERPNext report with filters.
  - Ask like: "Run Trial Balance for company ACME from 2026-01-01 to 2026-03-31."

### ERPNext Generic and User Context

- `erpnext_run_method`
  - Purpose: Call whitelisted ERPNext/Frappe server methods.
  - Ask like: "Run method frappe.auth.get_logged_user."

- `erpnext_get_current_user`
  - Purpose: Show ERPNext user behind current API key.
  - Ask like: "Who am I authenticated as in ERPNext?"

## Common user workflows

### 1. Explore an unfamiliar ERPNext instance

1. Ask for connectivity check (`erpnext_ping`).
2. Ask for installed apps (`erpnext_get_system_info`).
3. Ask to list doctypes (`erpnext_list_doctypes`).
4. Ask for field schema (`erpnext_get_doctype_meta` or `erpnext_get_fieldset`).

### 2. Find and inspect records

1. Search (`erpnext_search_docs`).
2. Open one record (`erpnext_get_doc`).
3. Count total matches if needed (`erpnext_count_docs`).

### 3. Correct a submitted transactional document

1. Cancel submitted doc (`erpnext_cancel_doc`).
2. Amend to new draft (`erpnext_amend_doc`).
3. Update fields (`erpnext_update_doc`).
4. Submit again (`erpnext_submit_doc`).

## Troubleshooting

- "No ERPNext tenant configured for this API key"
  - Your API key is not mapped to an ERPNext tenant in server config.

- Permission errors
  - The mapped ERPNext user lacks required roles/permissions.

- Report not found
  - First list reports with `erpnext_list_reports`, then run exact name.

- Binary file upload from chat fails
  - Use Open WebUI bridge tool `upload_file_to_erpnext` for chat attachments.
