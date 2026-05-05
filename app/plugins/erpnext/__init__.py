from app.core.registry import ToolRegistry

from . import tools


def register(registry: ToolRegistry) -> None:
    registry.register(
        name="erpnext_get_doc",
        description="Retrieve a specific document from ERPNext by doctype and document name. Use this to fetch any single record such as an invoice, customer, item, order, or task. Supports selecting specific fields and expanding linked documents.",
        handler=tools.get_doc_handler,
        request_model=tools.GetDocRequest,
        response_model=tools.GetDocResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_search_docs",
        description="Search and filter documents in ERPNext by doctype. Supports complex filters (AND/OR), field selection, sorting, pagination, and expanding linked documents. If you're unfamiliar with the doctype's fields, call erpnext_get_doctype_meta first to learn which fields you can filter and sort on.",
        handler=tools.search_docs_handler,
        request_model=tools.SearchDocsRequest,
        response_model=tools.SearchDocsResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_create_doc",
        description="Create a new document in ERPNext. BEFORE calling this on an unfamiliar doctype, call erpnext_get_doctype_meta to learn which fields are required (reqd=1), what types they expect, and what options they accept. The server will reject missing required fields. Provide the doctype and a dictionary of field values; the server fills in defaults and auto-generated fields.",
        handler=tools.create_doc_handler,
        request_model=tools.CreateDocRequest,
        response_model=tools.CreateDocResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_update_doc",
        description="Update fields on an existing ERPNext document. If you're unsure about valid field names, call erpnext_get_doctype_meta first to see the available fields and their types. Only include the fields you want to change; the rest remain unchanged.",
        handler=tools.update_doc_handler,
        request_model=tools.UpdateDocRequest,
        response_model=tools.UpdateDocResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_delete_doc",
        description="Delete a document from ERPNext. Use with caution — this permanently removes the record. ERPNext permissions are enforced: the operation will fail if the user does not have delete rights on the doctype.",
        handler=tools.delete_doc_handler,
        request_model=tools.DeleteDocRequest,
        response_model=tools.DeleteDocResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_get_doctype_meta",
        description="Get the field schema for a specific ERPNext doctype. Returns all fields with their types, labels, options, mandatory flags (reqd=1), and link targets. ALWAYS call this first before creating, updating, or filtering on an unfamiliar doctype — without it you won't know which fields are required, what values they accept, or what you can filter on.",
        handler=tools.get_doctype_meta_handler,
        request_model=tools.GetDoctypeMetaRequest,
        response_model=tools.GetDoctypeMetaResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_list_doctypes",
        description="List available doctypes in the ERPNext system. Supports filtering by name and module/app. This is your discovery tool — use it first when you need to find what record types exist, then inspect a specific one with erpnext_get_doctype_meta before acting on it.",
        handler=tools.list_doctypes_handler,
        request_model=tools.ListDoctypesRequest,
        response_model=tools.ListDoctypesResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_upload_file",
        description="Upload a file to ERPNext and attach it to a document. CRITICAL: When a user says 'upload the attached file', 'attach this file to X', 'save this document', or shares any file for uploading — use this tool immediately. Pass the file's text content directly as the 'content' parameter. Set doctype and docname to attach it to a specific record (e.g., doctype='Customer', docname='Test Corp'). When a user mentions attaching or uploading a file they shared, this is ALWAYS the tool to call.",
        handler=tools.upload_file_handler,
        request_model=tools.UploadFileRequest,
        response_model=tools.UploadFileResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_run_method",
        description="Call any whitelisted server-side method in the ERPNext/Frappe system. Use this to run reports, trigger workflows, submit/cancel documents, send emails, or execute custom app logic. Use GET for read-only methods, POST for methods that modify data.",
        handler=tools.run_method_handler,
        request_model=tools.RunMethodRequest,
        response_model=tools.RunMethodResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_run_report",
        description="Run a report in ERPNext/Frappe. The report_name parameter is REQUIRED — specify it as the report's title, e.g., 'Trial Balance', 'General Ledger', 'Accounts Receivable'. Optionally provide filters (dict of column filter values) and file_format ('HTML', 'CSV', or 'PDF'). Use this for any report request — financial statements, sales registers, audit trails, etc.",
        handler=tools.run_report_handler,
        request_model=tools.RunReportRequest,
        response_model=tools.RunReportResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_list_reports",
        description="List available reports in ERPNext. Filter by name, report type, or the doctype the report references. Use this to discover what reports exist before running one — e.g., find all financial reports or all reports related to Sales Invoice.",
        handler=tools.list_reports_handler,
        request_model=tools.ListReportsRequest,
        response_model=tools.ListReportsResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_get_current_user",
        description="Get the currently logged-in ERPNext user via the tenant credentials. Use this to understand who is making the request — helpful for context-aware operations.",
        handler=tools.get_current_user_handler,
        request_model=tools.GetCurrentUserRequest,
        response_model=tools.GetCurrentUserResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_get_system_info",
        description="Get installed Frappe/ERPNext apps and their versions from the system. Use this to understand what modules and capabilities are available — e.g., whether HR, Manufacturing, or specific custom apps are installed.",
        handler=tools.get_system_info_handler,
        request_model=tools.GetSystemInfoRequest,
        response_model=tools.GetSystemInfoResponse,
        tags=["erpnext"],
    )
