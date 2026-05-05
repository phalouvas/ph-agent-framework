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
        description="Search and filter documents in ERPNext by doctype. Supports complex filters (AND/OR), field selection, sorting, pagination, and expanding linked documents. Use this to find records matching specific criteria — e.g., all open sales orders over $1000, or customers in a specific territory.",
        handler=tools.search_docs_handler,
        request_model=tools.SearchDocsRequest,
        response_model=tools.SearchDocsResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_create_doc",
        description="Create a new document in ERPNext. Use this to create records like customers, sales orders, invoices, tasks, or any other doctype. Provide the doctype and a dictionary of field values. The server will populate default values and auto-generated fields.",
        handler=tools.create_doc_handler,
        request_model=tools.CreateDocRequest,
        response_model=tools.CreateDocResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_update_doc",
        description="Update fields on an existing ERPNext document. Use this to modify records — change a delivery date, update a status, correct a typo, or add notes. Only include the fields you want to change; the rest remain unchanged.",
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
        description="Get the field schema for a specific ERPNext doctype. Returns all fields with their types, labels, options, mandatory flags, and link targets. Use this BEFORE creating or searching documents of an unfamiliar doctype so you know which fields exist and what values they accept.",
        handler=tools.get_doctype_meta_handler,
        request_model=tools.GetDoctypeMetaRequest,
        response_model=tools.GetDoctypeMetaResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_list_doctypes",
        description="List available doctypes in the ERPNext system. Supports filtering by name and module/app. Use this to discover what record types are available — e.g., which doctypes belong to the Accounts or HR modules.",
        handler=tools.list_doctypes_handler,
        request_model=tools.ListDoctypesRequest,
        response_model=tools.ListDoctypesResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_upload_file",
        description="Upload a file to ERPNext. Accepts base64-encoded content. Optionally attach the file to a specific document by providing doctype and docname. Returns the file URL. Use this to attach PDFs, images, or other files to records.",
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
