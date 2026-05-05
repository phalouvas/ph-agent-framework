from app.core.registry import ToolRegistry

from . import tools


def register(registry: ToolRegistry) -> None:
    # ── Discovery & Metadata ──────────────────────────────────────────

    registry.register(
        name="erpnext_get_system_info",
        description="Get installed Frappe/ERPNext apps and their versions from the connected ERPNext instance. Use this first when connecting to an unfamiliar ERPNext system to understand what modules are available (e.g., whether HR, Manufacturing, CRM, or specific custom apps are installed). This informs which doctypes and reports exist.",
        handler=tools.get_system_info_handler,
        request_model=tools.GetSystemInfoRequest,
        response_model=tools.GetSystemInfoResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_ping",
        description="Quick health check: verify the ERPNext instance is reachable and responsive before attempting complex multi-step operations. Returns availability status and response latency. Use this at the start of a session or after a connection error to check if ERPNext is back online.",
        handler=tools.ping_handler,
        request_model=tools.PingErpNextRequest,
        response_model=tools.PingErpNextResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_list_doctypes",
        description="List available doctypes (record types) in the ERPNext system. Supports filtering by name search and module/app. This is your FIRST discovery tool — use it when you need to find what record types exist (e.g., 'what kinds of sales documents are there?'). Once you find a doctype, inspect it with erpnext_get_doctype_meta before creating or searching on it. Common modules: 'Selling', 'Buying', 'Accounts', 'Stock', 'HR', 'Manufacturing', 'CRM'.",
        handler=tools.list_doctypes_handler,
        request_model=tools.ListDoctypesRequest,
        response_model=tools.ListDoctypesResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_get_doctype_meta",
        description="Get the complete field schema for a specific ERPNext doctype. Returns all fields with their types, labels, selectable options, mandatory flags (reqd=1), and link targets. ALWAYS call this before creating, updating, or filtering on an unfamiliar doctype — without it you won't know which fields are required, what values they accept, or what you can filter on. Results are cached for 5 minutes so repeated calls for the same doctype are fast.",
        handler=tools.get_doctype_meta_handler,
        request_model=tools.GetDoctypeMetaRequest,
        response_model=tools.GetDoctypeMetaResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_get_fieldset",
        description="Get a pre-built, curated field template for common ERPNext doctypes (Sales Order, Sales Invoice, Purchase Order, Customer, Item, Supplier, Lead). Unlike erpnext_get_doctype_meta which returns the raw field list, this returns an organized template with 'required', 'optional', and 'child_tables' sections, plus example values and lifecycle information. Use this FIRST for common doctypes — it's faster and more reliable than parsing raw metadata. Falls back to recommending erpnext_get_doctype_meta for unsupported doctypes.",
        handler=tools.get_fieldset_handler,
        request_model=tools.GetFieldsetRequest,
        response_model=tools.GetFieldsetResponse,
        tags=["erpnext"],
    )

    # ── Document CRUD ─────────────────────────────────────────────────

    registry.register(
        name="erpnext_get_doc",
        description="Retrieve a single ERPNext document by its doctype and name. Call this when you need the full details of a known record (e.g., sales invoice SINV-24-00001 or customer Acme Corp). The response includes all fields and child table data (e.g., invoice items, order lines). Use 'fields' to request only specific columns and 'expand_links' to resolve foreign-key references like Customer or Item into full documents. If you don't know the document name, use erpnext_search_docs first. Common name formats: Sales Invoice (SINV-YYYY-NNNNN), Sales Order (SO-YYYY-NNNNN), Purchase Order (PO-YYYY-NNNNN), Customer (text name), Item (item code).",
        handler=tools.get_doc_handler,
        request_model=tools.GetDocRequest,
        response_model=tools.GetDocResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_search_docs",
        description="Search and filter documents in ERPNext by doctype. Supports complex filters (AND/OR logic), field selection, sorting, pagination, and expanding linked documents. Use this to find documents matching criteria (e.g., 'all open sales orders for customer X'). The response includes has_more (whether more pages exist) and count. For total count across all pages, set include_total_count=true. If you're unfamiliar with the doctype's fields, call erpnext_get_doctype_meta first to learn which fields you can filter and sort on. Operator guide: '=' exact match, 'like' partial match with % wildcards, '>' / '<' comparisons, 'between' ranges, 'in' list membership.",
        handler=tools.search_docs_handler,
        request_model=tools.SearchDocsRequest,
        response_model=tools.SearchDocsResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_count_docs",
        description="Get a quick count of documents matching optional filters in an ERPNext doctype. Use this when the user asks 'how many' of something exist (e.g., 'How many open sales orders?', 'How many customers are in Germany?'). This is much faster and cheaper than erpnext_search_docs when you only need the count, not the actual records. Uses the same filter format as erpnext_search_docs.",
        handler=tools.count_docs_handler,
        request_model=tools.CountDocsRequest,
        response_model=tools.CountDocsResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_create_doc",
        description="Create a new document in ERPNext. BEFORE calling this on an unfamiliar doctype, call erpnext_get_fieldset (for common doctypes) or erpnext_get_doctype_meta to learn which fields are required (reqd=1), what types they expect, and what values are valid. For doctypes with child tables (e.g., Sales Order 'items'), include the child rows as an array of dicts in the data field. Set 'docstatus' to 0 for Draft. After creating, the document is in Draft state — you may need to erpnext_submit_doc so the transaction takes effect.",
        handler=tools.create_doc_handler,
        request_model=tools.CreateDocRequest,
        response_model=tools.CreateDocResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_update_doc",
        description="Update fields on an existing ERPNext document. Only include the fields you want to change — the rest remain unchanged. Can only update documents in Draft status (docstatus=0). To modify a Submitted document, cancel it first with erpnext_cancel_doc, then amend with erpnext_amend_doc. If you're unsure about valid field names, call erpnext_get_doctype_meta first.",
        handler=tools.update_doc_handler,
        request_model=tools.UpdateDocRequest,
        response_model=tools.UpdateDocResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_delete_doc",
        description="Delete a document from ERPNext. Only works on documents in Draft or Cancelled status. A Submitted document must be cancelled first. ERPNext permissions are enforced — the operation fails if the user lacks delete rights on the doctype. Use with caution: this permanently removes the record and cannot be undone.",
        handler=tools.delete_doc_handler,
        request_model=tools.DeleteDocRequest,
        response_model=tools.DeleteDocResponse,
        tags=["erpnext"],
    )

    # ── Document Lifecycle ────────────────────────────────────────────

    registry.register(
        name="erpnext_submit_doc",
        description="Submit a draft document to make it permanent. After submitting: accounting entries are posted (for invoices), stock levels are updated (for stock documents), and the document status changes to 'Submitted' (docstatus=1). ONLY Draft documents (docstatus=0) can be submitted — check status with erpnext_get_doc first. After submission the document is locked — you cannot edit it directly. To make changes later: erpnext_cancel_doc → erpnext_amend_doc → edit the new draft → erpnext_submit_doc again. Not all doctypes are submittable — check the doctype meta if unsure.",
        handler=tools.submit_doc_handler,
        request_model=tools.SubmitDocRequest,
        response_model=tools.SubmitDocResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_cancel_doc",
        description="Cancel a submitted document to reverse its effects. Accounting entries are reversed, stock movements are undone, and the document status changes to 'Cancelled' (docstatus=2). Only Submitted documents (docstatus=1) can be cancelled. Some documents cannot be cancelled if linked to downstream transactions (e.g., an invoice that has a payment entry). After cancellation, use erpnext_amend_doc to create a corrected version, or erpnext_delete_doc to remove it permanently.",
        handler=tools.cancel_doc_handler,
        request_model=tools.CancelDocRequest,
        response_model=tools.CancelDocResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_amend_doc",
        description="Create an amended (corrected) copy of a cancelled document. This is how you fix errors in submitted transactions: cancel the original, amend to create a new draft, edit the draft, then submit. The new document has a link to the original via 'amended_from'. Use the 'data' parameter to specify which fields to change — only include fields that should differ from the original. The original must be in Cancelled status (docstatus=2). After amending, call erpnext_update_doc to make further changes, then erpnext_submit_doc to finalize.",
        handler=tools.amend_doc_handler,
        request_model=tools.AmendDocRequest,
        response_model=tools.AmendDocResponse,
        tags=["erpnext"],
    )

    # ── Files ─────────────────────────────────────────────────────────

    registry.register(
        name="erpnext_upload_file",
        description="Upload text content as a file to ERPNext, optionally attached to a specific doctype and document. Use this when a user provides text in the chat that should be saved (e.g., 'save these meeting notes to Customer X'). Pass the text as the 'content' parameter. IMPORTANT: This tool can ONLY handle text content provided directly in the message. When a user attaches a binary file (PDF, image, Office document) and asks to upload it, use the 'upload_file_to_erpnext' bridge tool instead — it can read chat attachments that this tool cannot access.",
        handler=tools.upload_file_handler,
        request_model=tools.UploadFileRequest,
        response_model=tools.UploadFileResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_list_attachments",
        description="List all files attached to a specific ERPNext document. Use this when a user asks 'what files are attached to invoice X?' or 'show me the attachments for customer Y'. Returns file metadata including file_name, file_url, file_size, and is_private flag. To see details of a specific file, follow up with erpnext_get_file using the file_url from the results.",
        handler=tools.list_attachments_handler,
        request_model=tools.ListAttachmentsRequest,
        response_model=tools.ListAttachmentsResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_get_file",
        description="Get metadata for a specific file in ERPNext by its file_url (e.g., '/files/invoice.pdf'). Returns file_name, file_url, file_size, content_hash, and info about which document the file is attached to. Use this to check file details or to find where a file is linked. Note: this returns metadata only, not the file's binary content.",
        handler=tools.get_file_handler,
        request_model=tools.GetFileRequest,
        response_model=tools.GetFileResponse,
        tags=["erpnext"],
    )

    # ── Reports ───────────────────────────────────────────────────────

    registry.register(
        name="erpnext_list_reports",
        description="List available reports in ERPNext. Filter by name search, report type ('Query Report', 'Script Report', 'Report Builder'), or the doctype they reference ('Sales Invoice', 'Item', etc.). Use this to discover what reports exist before running one — e.g., find all financial reports or all reports related to Sales Order. To execute a report, use erpnext_run_report with the report name from these results.",
        handler=tools.list_reports_handler,
        request_model=tools.ListReportsRequest,
        response_model=tools.ListReportsResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_run_report",
        description="Execute a report in ERPNext. Common reports: 'Trial Balance' (account balances at a date), 'General Ledger' (all account entries in a period), 'Accounts Receivable' (who owes you money), 'Accounts Payable' (who you owe), 'Sales Register' (sales invoices in a period), 'Purchase Register' (purchase invoices), 'Stock Ledger' (inventory movements), 'Item-wise Sales Register'. Provide filters as key-value pairs for the report's parameters (company, from_date, to_date, etc.). The response includes columns (header names) and row_count in addition to the raw result. Use erpnext_list_reports first if you don't know the exact report name.",
        handler=tools.run_report_handler,
        request_model=tools.RunReportRequest,
        response_model=tools.RunReportResponse,
        tags=["erpnext"],
    )

    # ── Generic & User ────────────────────────────────────────────────

    registry.register(
        name="erpnext_run_method",
        description="Call any whitelisted server-side method in the ERPNext/Frappe system. This is the escape hatch for operations not covered by dedicated tools. Common uses: run reports ('frappe.desk.query_report.run'), submit documents ('frappe.client.submit'), cancel documents ('frappe.client.cancel'), get logged user ('frappe.auth.get_logged_user'), trigger custom app logic. Use GET for read-only methods, POST for methods that mutate data. Note: submit/cancel/amend have dedicated tools (erpnext_submit_doc, etc.) which you should prefer over this raw method call.",
        handler=tools.run_method_handler,
        request_model=tools.RunMethodRequest,
        response_model=tools.RunMethodResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_get_current_user",
        description="Get the currently logged-in ERPNext user. Use this at the start of a session to understand whose credentials are being used and what permissions are available. The user's roles determine which doctypes they can read, create, submit, or delete — operations may fail with permission errors if the user lacks the required role.",
        handler=tools.get_current_user_handler,
        request_model=tools.GetCurrentUserRequest,
        response_model=tools.GetCurrentUserResponse,
        tags=["erpnext"],
    )
