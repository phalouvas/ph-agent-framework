from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.plugins.erpnext.client import ErpNextClient
from app.schemas.tool_context import ToolContext


# --- Get Document ---

class GetDocRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype name, e.g., 'Sales Invoice', 'Item', 'Customer'"
    )
    docname: str = Field(
        ..., description="Document name/ID, e.g., 'SINV-24-00001'"
    )
    fields: list[str] | None = Field(
        None, description="Specific field names to return. If omitted, all fields are returned."
    )
    expand_links: bool = Field(
        False, description="If true, link fields are expanded into full related documents"
    )


class GetDocResponse(BaseModel):
    doc: dict[str, Any] | None = Field(
        None, description="The requested document data, or None if not found"
    )
    error: str | None = Field(None, description="Error message if the document could not be retrieved")


async def get_doc_handler(request: GetDocRequest, context: ToolContext) -> GetDocResponse:
    if context.tenant is None:
        return GetDocResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        doc = await client.get_doc(request.doctype, request.docname, fields=request.fields, expand_links=request.expand_links)
        return GetDocResponse(doc=doc)
    except Exception as e:
        return GetDocResponse(error=str(e))


# --- Search Documents ---

class SearchDocsRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype name, e.g., 'Item', 'Customer', 'Sales Order'"
    )
    filters: list | None = Field(
        None,
        description=(
            "Filter conditions as an array of [field, operator, value] triples. "
            "Operators: =, !=, >, <, >=, <=, like, not like, in, not in, between, is, is not. "
            'Example: [["status", "=", "Open"], ["total", ">", 1000]]. '
            "All conditions are ANDed together."
        ),
    )
    or_filters: list | None = Field(
        None,
        description="Same format as filters, but conditions are ORed. Use when you need 'any of these conditions match'",
    )
    fields: list[str] | None = Field(
        None, description="List of field names to return. If omitted, defaults to name only."
    )
    order_by: str | None = Field(
        None, description="Field to sort results by, e.g., 'modified desc', 'creation asc'"
    )
    limit: int = Field(
        20, description="Maximum number of results to return", ge=1, le=200
    )
    limit_start: int = Field(
        0, description="Number of results to skip for pagination", ge=0
    )
    expand: list[str] | None = Field(
        None, description="List of field names to expand into full related documents"
    )


class SearchDocsResponse(BaseModel):
    results: list[dict[str, Any]] = Field(
        default_factory=list, description="List of matching documents"
    )
    count: int = Field(0, description="Number of results returned")
    error: str | None = Field(None, description="Error message if the search failed")


async def search_docs_handler(request: SearchDocsRequest, context: ToolContext) -> SearchDocsResponse:
    if context.tenant is None:
        return SearchDocsResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        results = await client.search_docs(
            doctype=request.doctype,
            filters=request.filters,
            or_filters=request.or_filters,
            fields=request.fields,
            limit_page_length=request.limit,
            limit_start=request.limit_start,
            order_by=request.order_by,
            expand=request.expand,
        )
        return SearchDocsResponse(
            results=results if isinstance(results, list) else [],
            count=len(results) if isinstance(results, list) else 0,
        )
    except Exception as e:
        return SearchDocsResponse(error=str(e))


# --- Create Document ---

class CreateDocRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype name, e.g., 'Sales Invoice', 'Customer', 'Item'"
    )
    data: dict[str, Any] = Field(
        ..., description="Fields and values for the new document, e.g., {'customer': 'Acme Corp', 'total': 1500}"
    )


class CreateDocResponse(BaseModel):
    doc: dict[str, Any] | None = Field(
        None, description="The created document with all server-populated fields"
    )
    error: str | None = Field(None, description="Error message if creation failed")


async def create_doc_handler(request: CreateDocRequest, context: ToolContext) -> CreateDocResponse:
    if context.tenant is None:
        return CreateDocResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        doc = await client.create_doc(request.doctype, request.data)
        return CreateDocResponse(doc=doc)
    except Exception as e:
        return CreateDocResponse(error=str(e))


# --- Update Document ---

class UpdateDocRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype name, e.g., 'Sales Order', 'Customer'"
    )
    docname: str = Field(
        ..., description="Document name/ID to update, e.g., 'SO-2025-00001'"
    )
    data: dict[str, Any] = Field(
        ..., description="Fields to update, e.g., {'delivery_date': '2025-03-15', 'status': 'Completed'}"
    )


class UpdateDocResponse(BaseModel):
    doc: dict[str, Any] | None = Field(
        None, description="The updated document"
    )
    error: str | None = Field(None, description="Error message if the update failed")


async def update_doc_handler(request: UpdateDocRequest, context: ToolContext) -> UpdateDocResponse:
    if context.tenant is None:
        return UpdateDocResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        doc = await client.update_doc(request.doctype, request.docname, request.data)
        return UpdateDocResponse(doc=doc)
    except Exception as e:
        return UpdateDocResponse(error=str(e))


# --- Delete Document ---

class DeleteDocRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype name to delete from"
    )
    docname: str = Field(
        ..., description="Document name/ID to delete"
    )


class DeleteDocResponse(BaseModel):
    success: bool = Field(False, description="True if the document was deleted successfully")
    error: str | None = Field(None, description="Error message if deletion failed")


async def delete_doc_handler(request: DeleteDocRequest, context: ToolContext) -> DeleteDocResponse:
    if context.tenant is None:
        return DeleteDocResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        result = await client.delete_doc(request.doctype, request.docname)
        return DeleteDocResponse(success="message" in result)
    except Exception as e:
        return DeleteDocResponse(error=str(e))


# --- Get Doctype Meta ---

class GetDoctypeMetaRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype name to get field schema for, e.g., 'Sales Invoice', 'Item'"
    )


class GetDoctypeMetaResponse(BaseModel):
    meta: dict[str, Any] | None = Field(
        None, description="Doctype metadata including fields array with types, labels, options, and mandatory flags"
    )
    error: str | None = Field(None, description="Error message if metadata could not be retrieved")


async def get_doctype_meta_handler(request: GetDoctypeMetaRequest, context: ToolContext) -> GetDoctypeMetaResponse:
    if context.tenant is None:
        return GetDoctypeMetaResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        meta = await client.get_doctype_meta(request.doctype)
        return GetDoctypeMetaResponse(meta=meta)
    except Exception as e:
        return GetDoctypeMetaResponse(error=str(e))


# --- List Doctypes ---

class ListDoctypesRequest(BaseModel):
    query: str = Field(
        "", description="Optional search text to filter doctypes by name"
    )
    module: str | None = Field(
        None, description="Filter doctypes by module/app, e.g., 'Accounts', 'HR', 'Manufacturing'"
    )
    limit: int = Field(
        50, description="Maximum number of doctypes to return", ge=1, le=500
    )


class ListDoctypesResponse(BaseModel):
    doctypes: list[dict[str, Any]] = Field(
        default_factory=list, description="List of doctypes with name, module, and type flags"
    )
    count: int = Field(0, description="Number of doctypes returned")
    error: str | None = Field(None, description="Error message if the listing failed")


async def list_doctypes_handler(request: ListDoctypesRequest, context: ToolContext) -> ListDoctypesResponse:
    if context.tenant is None:
        return ListDoctypesResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        doctypes = await client.list_doctypes(query=request.query or None, module=request.module, limit=request.limit)
        return ListDoctypesResponse(
            doctypes=doctypes if isinstance(doctypes, list) else [],
            count=len(doctypes) if isinstance(doctypes, list) else 0,
        )
    except Exception as e:
        return ListDoctypesResponse(error=str(e))


# --- Upload File ---

class UploadFileRequest(BaseModel):
    file_name: str = Field(
        "", description="Name of the attached file including its extension. Use the exact filename the user shared, e.g., 'document.pdf', 'report.csv', 'notes.txt'"
    )
    content: str = Field(
        "", description="The full text content of the attached file. Copy the file content you see in the conversation into this parameter verbatim. Use this for text files; for binary files use content_base64 instead."
    )
    content_base64: str = Field(
        "", description="Base64-encoded file content for binary files. For text files, use the content parameter instead."
    )
    doctype: str | None = Field(
        None, description="Optional doctype to attach the file to, e.g., 'Sales Invoice'"
    )
    docname: str | None = Field(
        None, description="Optional document name to attach the file to"
    )
    is_private: bool = Field(
        True, description="If true, the file is only accessible to users with permission"
    )
    folder: str | None = Field(
        None, description="Target folder in ERPNext, e.g., 'Home/Attachments'"
    )

    @model_validator(mode="after")
    def check_content_not_empty(self):
        if not self.content.strip() and not self.content_base64.strip():
            raise ValueError("Either 'content' or 'content_base64' must contain the file's data. When a file is attached in chat, copy its content into 'content'.")
        return self


class UploadFileResponse(BaseModel):
    file_url: str | None = Field(None, description="URL of the uploaded file in ERPNext")
    file_name: str | None = Field(None, description="Name of the uploaded file as stored in ERPNext")
    success: bool = Field(False, description="True if the upload succeeded")
    error: str | None = Field(None, description="Error message if the upload failed")


async def upload_file_handler(request: UploadFileRequest, context: ToolContext) -> UploadFileResponse:
    if context.tenant is None:
        return UploadFileResponse(error="No ERPNext tenant configured for this API key")

    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        result = await client.upload_file(
            file_name=request.file_name or "uploaded_file",
            content_base64=request.content_base64 or None,
            content=request.content or None,
            doctype=request.doctype,
            docname=request.docname,
            is_private=request.is_private,
            folder=request.folder,
        )
        return UploadFileResponse(
            file_url=result.get("file_url"),
            file_name=result.get("file_name"),
            success=True,
        )
    except Exception as e:
        return UploadFileResponse(error=str(e))


# --- Run Method ---

class RunMethodRequest(BaseModel):
    method_path: str = Field(
        ..., description="Dotted path to a whitelisted Frappe method, e.g., 'frappe.auth.get_logged_user', 'frappe.desk.query_report.run'"
    )
    args: dict[str, Any] | None = Field(
        None, description="Optional arguments to pass to the method"
    )
    http_method: str = Field(
        "POST", description="HTTP method: 'POST' for mutating methods, 'GET' for read-only methods"
    )


class RunMethodResponse(BaseModel):
    result: Any = Field(None, description="The method's return value")
    error: str | None = Field(None, description="Error message if the method call failed")


async def run_method_handler(request: RunMethodRequest, context: ToolContext) -> RunMethodResponse:
    if context.tenant is None:
        return RunMethodResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        result = await client.run_method(
            method_path=request.method_path,
            args=request.args,
            http_method=request.http_method,
        )
        return RunMethodResponse(result=result)
    except Exception as e:
        return RunMethodResponse(error=str(e))


# --- Run Report ---

class RunReportRequest(BaseModel):
    report_name: str = Field(
        ..., description="Name of the report, e.g., 'Trial Balance', 'General Ledger', 'Accounts Receivable', 'Sales Register'"
    )
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Report filters as key-value pairs, e.g., {'company': 'Test Company', 'from_date': '2025-01-01', 'to_date': '2025-12-31', 'as_on_date': '2025-03-31'}",
    )
    file_format: str = Field(
        "HTML", description="Output format: 'HTML' for web view, 'CSV' for spreadsheet, 'PDF' for print"
    )


class RunReportResponse(BaseModel):
    result: Any = Field(None, description="Report data including columns and result rows")
    error: str | None = Field(None, description="Error message if the report failed")


async def run_report_handler(request: RunReportRequest, context: ToolContext) -> RunReportResponse:
    if context.tenant is None:
        return RunReportResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        result = await client.run_report(
            report_name=request.report_name,
            filters=request.filters,
            file_format=request.file_format,
        )
        return RunReportResponse(result=result)
    except Exception as e:
        return RunReportResponse(error=str(e))


# --- List Reports ---

class ListReportsRequest(BaseModel):
    query: str = Field(
        "", description="Optional search text to filter reports by name, e.g., 'Balance', 'Ledger', 'Sales'"
    )
    report_type: str | None = Field(
        None, description="Filter by report type: 'Query Report', 'Script Report', or 'Report Builder'"
    )
    ref_doctype: str | None = Field(
        None, description="Filter reports that reference a specific doctype, e.g., 'Sales Invoice'"
    )
    limit: int = Field(
        50, description="Maximum number of reports to return", ge=1, le=200
    )


class ListReportsResponse(BaseModel):
    reports: list[dict[str, Any]] = Field(
        default_factory=list, description="List of reports with name, report_type, module, and ref_doctype"
    )
    count: int = Field(0, description="Number of reports returned")
    error: str | None = Field(None, description="Error message if the listing failed")


async def list_reports_handler(request: ListReportsRequest, context: ToolContext) -> ListReportsResponse:
    if context.tenant is None:
        return ListReportsResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        reports = await client.list_reports(
            query=request.query or None,
            report_type=request.report_type,
            limit=request.limit,
        )
        return ListReportsResponse(
            reports=reports if isinstance(reports, list) else [],
            count=len(reports) if isinstance(reports, list) else 0,
        )
    except Exception as e:
        return ListReportsResponse(error=str(e))


# --- Get Current User ---

class GetCurrentUserRequest(BaseModel):
    """No parameters needed — identity is resolved from the API key's tenant credentials."""


class GetCurrentUserResponse(BaseModel):
    user: str | None = Field(None, description="The logged-in user's email or username")
    error: str | None = Field(None, description="Error message if the call failed")


async def get_current_user_handler(_request: GetCurrentUserRequest, context: ToolContext) -> GetCurrentUserResponse:
    if context.tenant is None:
        return GetCurrentUserResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        user = await client.get_current_user()
        return GetCurrentUserResponse(user=user)
    except Exception as e:
        return GetCurrentUserResponse(error=str(e))


# --- Get System Info ---

class GetSystemInfoRequest(BaseModel):
    """No parameters needed."""


class GetSystemInfoResponse(BaseModel):
    info: dict[str, Any] | None = Field(None, description="Installed apps and their versions")
    error: str | None = Field(None, description="Error message if the call failed")


async def get_system_info_handler(_request: GetSystemInfoRequest, context: ToolContext) -> GetSystemInfoResponse:
    if context.tenant is None:
        return GetSystemInfoResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        info = await client.get_system_info()
        return GetSystemInfoResponse(info=info)
    except Exception as e:
        return GetSystemInfoResponse(error=str(e))
