from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.plugins.erpnext.client import ErpNextClient
from app.schemas.tool_context import ToolContext


WRITE_VALIDATION_DOCTYPES: set[str] = {
    "Sales Order",
    "Sales Invoice",
    "Purchase Order",
    "Purchase Invoice",
    "Payment Entry",
    "Journal Entry",
    "Quotation",
    "Material Request",
    "Purchase Receipt",
    "Stock Entry",
    "Stock Reconciliation",
    "Work Order",
}

SYSTEM_FIELDS: set[str] = {
    "name",
    "owner",
    "creation",
    "modified",
    "modified_by",
    "docstatus",
    "idx",
    "doctype",
}


class ValidationIssue(BaseModel):
    field: str = Field(..., description="Field name that failed validation")
    reason: str = Field(..., description="Human-readable reason for the validation failure")


class WriteValidationResult(BaseModel):
    applied: bool = Field(False, description="Whether live-schema validation was executed")
    source: str = Field(
        "none",
        description="Validation source. 'live_meta' means ERPNext doctype metadata was used; 'none' means validation was skipped.",
    )
    mode: str = Field(
        "auto",
        description="Validation mode used by the handler: 'auto', 'live', or 'off'.",
    )
    missing_required_fields: list[str] = Field(
        default_factory=list,
        description="Required fields that were missing or empty in the payload.",
    )
    unknown_fields: list[str] = Field(
        default_factory=list,
        description="Payload keys not present in live doctype metadata.",
    )
    issues: list[ValidationIssue] = Field(
        default_factory=list,
        description="Detailed validation issues for fields with invalid shape or values.",
    )


def _should_run_live_validation(doctype: str, mode: Literal["auto", "live", "off"]) -> bool:
    if mode == "off":
        return False
    if mode == "live":
        return True
    return doctype in WRITE_VALIDATION_DOCTYPES


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _collect_field_definitions(meta: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fields = meta.get("fields", [])
    out: dict[str, dict[str, Any]] = {}
    for field in fields:
        if isinstance(field, dict) and field.get("fieldname"):
            out[str(field["fieldname"])] = field
    return out


def _validate_payload_against_meta(
    *,
    doctype: str,
    payload: dict[str, Any],
    meta: dict[str, Any],
    operation: Literal["create", "update"],
    mode: Literal["auto", "live", "off"],
) -> WriteValidationResult:
    result = WriteValidationResult(applied=True, source="live_meta", mode=mode)
    field_defs = _collect_field_definitions(meta)
    known_fields = set(field_defs.keys()) | SYSTEM_FIELDS

    for key, value in payload.items():
        if key not in known_fields:
            result.unknown_fields.append(key)
            continue
        definition = field_defs.get(key)
        if definition is None:
            continue
        fieldtype = str(definition.get("fieldtype") or "")
        if fieldtype == "Table" and not isinstance(value, list):
            result.issues.append(ValidationIssue(field=key, reason="Expected an array for child table field"))

    if operation == "create":
        for name, definition in field_defs.items():
            if not definition.get("reqd"):
                continue
            if definition.get("read_only"):
                continue
            if definition.get("hidden"):
                continue
            if definition.get("default"):
                continue
            if _is_missing_value(payload.get(name)):
                result.missing_required_fields.append(name)

    return result


# ── Get Document ──────────────────────────────────────────────────────

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


# ── Search Documents ──────────────────────────────────────────────────

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
    include_total_count: bool = Field(
        False,
        description="If true, also returns the total count of matching documents (uses one extra API call). Use when you need to know the total number of results beyond the current page.",
    )


class SearchDocsResponse(BaseModel):
    results: list[dict[str, Any]] = Field(
        default_factory=list, description="List of matching documents"
    )
    count: int = Field(0, description="Number of results in the current page")
    has_more: bool = Field(
        False, description="True if there are more results beyond the current page"
    )
    total_count: int | None = Field(
        None, description="Total number of matching documents (only set when include_total_count was True)"
    )
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
        items = results if isinstance(results, list) else []
        has_more = len(items) == request.limit if request.limit > 0 else False

        total_count = None
        if request.include_total_count:
            total_count = await client.count_docs(
                doctype=request.doctype,
                filters=request.filters,
                or_filters=request.or_filters,
            )

        return SearchDocsResponse(
            results=items,
            count=len(items),
            has_more=has_more,
            total_count=total_count,
        )
    except Exception as e:
        return SearchDocsResponse(error=str(e))


# ── Create Document ────────────────────────────────────────────────────

class CreateDocRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype name, e.g., 'Sales Invoice', 'Customer', 'Item'"
    )
    data: dict[str, Any] = Field(
        ..., description="Fields and values for the new document, e.g., {'customer': 'Acme Corp', 'total': 1500}"
    )
    validation_mode: Literal["auto", "live", "off"] = Field(
        "auto",
        description="Validation behavior before write. 'auto' validates common transactional doctypes using live metadata, 'live' always validates, and 'off' skips preflight validation.",
    )
    refresh_meta: bool = Field(
        False,
        description="If true, bypass metadata cache and fetch fresh doctype metadata for validation.",
    )


class CreateDocResponse(BaseModel):
    success: bool = Field(False, description="True only when the create operation completed without validation or API errors")
    doc: dict[str, Any] | None = Field(
        None, description="The created document with all server-populated fields"
    )
    validation: WriteValidationResult | None = Field(
        None,
        description="Structured validation result from live schema checks before writing.",
    )
    verification_required: bool = Field(
        True,
        description="Always true for write tools. Read back the document via erpnext_get_doc or erpnext_search_docs before claiming business success.",
    )
    verification_hint: str = Field(
        "Verify the write result with erpnext_get_doc or erpnext_search_docs before making success claims.",
        description="Guidance for post-write verification.",
    )
    error: str | None = Field(None, description="Error message if creation failed")


async def create_doc_handler(request: CreateDocRequest, context: ToolContext) -> CreateDocResponse:
    if context.tenant is None:
        return CreateDocResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)

    validation_result: WriteValidationResult | None = None
    if _should_run_live_validation(request.doctype, request.validation_mode):
        try:
            meta = await client.get_doctype_meta(request.doctype, force_refresh=request.refresh_meta)
        except Exception as e:
            return CreateDocResponse(
                success=False,
                error=f"Failed to fetch live metadata for validation: {e}",
                validation=WriteValidationResult(applied=False, source="none", mode=request.validation_mode),
            )

        validation_result = _validate_payload_against_meta(
            doctype=request.doctype,
            payload=request.data,
            meta=meta,
            operation="create",
            mode=request.validation_mode,
        )
        if (
            validation_result.missing_required_fields
            or validation_result.unknown_fields
            or validation_result.issues
        ):
            return CreateDocResponse(
                success=False,
                validation=validation_result,
                error="Validation failed against live ERPNext metadata",
            )

    try:
        doc = await client.create_doc(request.doctype, request.data)
        return CreateDocResponse(success=True, doc=doc, validation=validation_result)
    except Exception as e:
        return CreateDocResponse(success=False, error=str(e), validation=validation_result)


# ── Update Document ────────────────────────────────────────────────────

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
    validation_mode: Literal["auto", "live", "off"] = Field(
        "auto",
        description="Validation behavior before write. 'auto' validates common transactional doctypes using live metadata, 'live' always validates, and 'off' skips preflight validation.",
    )
    refresh_meta: bool = Field(
        False,
        description="If true, bypass metadata cache and fetch fresh doctype metadata for validation.",
    )


class UpdateDocResponse(BaseModel):
    success: bool = Field(False, description="True only when the update operation completed without validation or API errors")
    doc: dict[str, Any] | None = Field(
        None, description="The updated document"
    )
    validation: WriteValidationResult | None = Field(
        None,
        description="Structured validation result from live schema checks before writing.",
    )
    verification_required: bool = Field(
        True,
        description="Always true for write tools. Read back the document via erpnext_get_doc or erpnext_search_docs before claiming business success.",
    )
    verification_hint: str = Field(
        "Verify the write result with erpnext_get_doc or erpnext_search_docs before making success claims.",
        description="Guidance for post-write verification.",
    )
    error: str | None = Field(None, description="Error message if the update failed")


async def update_doc_handler(request: UpdateDocRequest, context: ToolContext) -> UpdateDocResponse:
    if context.tenant is None:
        return UpdateDocResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)

    validation_result: WriteValidationResult | None = None
    if _should_run_live_validation(request.doctype, request.validation_mode):
        try:
            meta = await client.get_doctype_meta(request.doctype, force_refresh=request.refresh_meta)
        except Exception as e:
            return UpdateDocResponse(
                success=False,
                error=f"Failed to fetch live metadata for validation: {e}",
                validation=WriteValidationResult(applied=False, source="none", mode=request.validation_mode),
            )

        validation_result = _validate_payload_against_meta(
            doctype=request.doctype,
            payload=request.data,
            meta=meta,
            operation="update",
            mode=request.validation_mode,
        )
        if validation_result.unknown_fields or validation_result.issues:
            return UpdateDocResponse(
                success=False,
                validation=validation_result,
                error="Validation failed against live ERPNext metadata",
            )

    try:
        doc = await client.update_doc(request.doctype, request.docname, request.data)
        return UpdateDocResponse(success=True, doc=doc, validation=validation_result)
    except Exception as e:
        return UpdateDocResponse(success=False, error=str(e), validation=validation_result)


# ── Delete Document ────────────────────────────────────────────────────

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


# ── Submit Document ────────────────────────────────────────────────────

class SubmitDocRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype name, e.g., 'Sales Invoice', 'Purchase Order', 'Sales Order'. Must be a submittable doctype."
    )
    docname: str = Field(
        ..., description="Document name/ID to submit, e.g., 'SINV-24-00001'. The document must be in 'Draft' status (docstatus=0)."
    )


class SubmitDocResponse(BaseModel):
    doc: dict[str, Any] | None = Field(None, description="The submitted document data")
    error: str | None = Field(None, description="Error message if submission failed")


async def submit_doc_handler(request: SubmitDocRequest, context: ToolContext) -> SubmitDocResponse:
    if context.tenant is None:
        return SubmitDocResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        doc = await client.submit_doc(request.doctype, request.docname)
        return SubmitDocResponse(doc=doc)
    except Exception as e:
        return SubmitDocResponse(error=str(e))


# ── Cancel Document ────────────────────────────────────────────────────

class CancelDocRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype name, e.g., 'Sales Invoice', 'Purchase Order'"
    )
    docname: str = Field(
        ..., description="Document name/ID to cancel, e.g., 'SINV-24-00001'. The document must be in 'Submitted' status (docstatus=1)."
    )


class CancelDocResponse(BaseModel):
    doc: dict[str, Any] | None = Field(None, description="The cancelled document data (docstatus changes to 2)")
    error: str | None = Field(None, description="Error message if cancellation failed")


async def cancel_doc_handler(request: CancelDocRequest, context: ToolContext) -> CancelDocResponse:
    if context.tenant is None:
        return CancelDocResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        doc = await client.cancel_doc(request.doctype, request.docname)
        return CancelDocResponse(doc=doc)
    except Exception as e:
        return CancelDocResponse(error=str(e))


# ── Amend Document ─────────────────────────────────────────────────────

class AmendDocRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype name, e.g., 'Sales Invoice', 'Purchase Order'"
    )
    docname: str = Field(
        ..., description="Document name/ID to amend. The document must be in 'Cancelled' status (docstatus=2). This creates a new 'Draft' document linked to the original."
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional field overrides for the amended copy, e.g., {'items': [...]} to modify line items. Only include fields you want to change.",
    )


class AmendDocResponse(BaseModel):
    doc: dict[str, Any] | None = Field(None, description="The amended document (new draft version linked to the original)")
    error: str | None = Field(None, description="Error message if amendment failed")


async def amend_doc_handler(request: AmendDocRequest, context: ToolContext) -> AmendDocResponse:
    if context.tenant is None:
        return AmendDocResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        doc = await client.amend_doc(request.doctype, request.docname, request.data)
        return AmendDocResponse(doc=doc)
    except Exception as e:
        return AmendDocResponse(error=str(e))


# ── Get Doctype Meta ────────────────────────────────────────────────────

class GetDoctypeMetaRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype name to get field schema for, e.g., 'Sales Invoice', 'Item'"
    )
    refresh_cache: bool = Field(
        False,
        description="If true, invalidate any cached metadata for this tenant and fetch fresh doctype metadata from ERPNext.",
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
        if request.refresh_cache:
            ErpNextClient.invalidate_meta_cache_for_tenant(context.tenant.url, request.doctype)
        meta = await client.get_doctype_meta(request.doctype, force_refresh=request.refresh_cache)
        return GetDoctypeMetaResponse(meta=meta)
    except Exception as e:
        return GetDoctypeMetaResponse(error=str(e))


# ── List Doctypes ──────────────────────────────────────────────────────

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


# ── Count Documents ────────────────────────────────────────────────────

class CountDocsRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype to count, e.g., 'Sales Invoice', 'Customer', 'Item'. Always use the singular doctype name as it appears in the system."
    )
    filters: list | None = Field(
        None, description="Optional filter conditions as [field, operator, value] triples, e.g., [['status', '=', 'Open']]. Same format as erpnext_search_docs."
    )
    or_filters: list | None = Field(
        None, description="Optional OR filter conditions, same format as filters"
    )


class CountDocsResponse(BaseModel):
    doctype: str = Field("", description="The doctype that was counted")
    count: int = Field(0, description="Number of matching documents")
    has_filters: bool = Field(False, description="Whether filters were applied")
    error: str | None = Field(None, description="Error message if the count failed")


async def count_docs_handler(request: CountDocsRequest, context: ToolContext) -> CountDocsResponse:
    if context.tenant is None:
        return CountDocsResponse(doctype=request.doctype, error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        count = await client.count_docs(
            doctype=request.doctype,
            filters=request.filters,
            or_filters=request.or_filters,
        )
        return CountDocsResponse(
            doctype=request.doctype,
            count=count,
            has_filters=bool(request.filters or request.or_filters),
        )
    except Exception as e:
        return CountDocsResponse(doctype=request.doctype, error=str(e))


# ── Upload File ────────────────────────────────────────────────────────

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


# ── Get File ────────────────────────────────────────────────────────────

class GetFileRequest(BaseModel):
    file_url: str = Field(
        ..., description="The file_url from a document's attachment field or from erpnext_list_attachments, e.g., '/files/invoice.pdf'"
    )


class GetFileResponse(BaseModel):
    file: dict[str, Any] | None = Field(
        None, description="File metadata (file_name, file_url, file_size, content_hash, is_private, attached_to_doctype, attached_to_name)"
    )
    error: str | None = Field(None, description="Error message if the file could not be retrieved")


async def get_file_handler(request: GetFileRequest, context: ToolContext) -> GetFileResponse:
    if context.tenant is None:
        return GetFileResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        file_data = await client.get_file(request.file_url)
        return GetFileResponse(file=file_data)
    except Exception as e:
        return GetFileResponse(error=str(e))


# ── List Attachments ───────────────────────────────────────────────────

class ListAttachmentsRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype to list attachments for, e.g., 'Sales Invoice', 'Customer'"
    )
    docname: str = Field(
        ..., description="Document name to list attachments for, e.g., 'SINV-24-00001'"
    )


class ListAttachmentsResponse(BaseModel):
    files: list[dict[str, Any]] = Field(
        default_factory=list, description="List of attached files with metadata (name, file_name, file_url, file_size)"
    )
    count: int = Field(0, description="Number of attachments found")
    error: str | None = Field(None, description="Error message if listing failed")


async def list_attachments_handler(request: ListAttachmentsRequest, context: ToolContext) -> ListAttachmentsResponse:
    if context.tenant is None:
        return ListAttachmentsResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        files = await client.list_files(doctype=request.doctype, docname=request.docname)
        if not isinstance(files, list):
            files = []
        return ListAttachmentsResponse(files=files, count=len(files))
    except Exception as e:
        return ListAttachmentsResponse(error=str(e))


# ── Ping / Health Check ────────────────────────────────────────────────

class PingErpNextRequest(BaseModel):
    """No parameters needed — the tenant is resolved from the API key."""


class PingErpNextResponse(BaseModel):
    available: bool = Field(False, description="Whether the ERPNext instance is reachable and responsive")
    url: str = Field("", description="The ERPNext instance URL that was checked")
    latency_ms: float | None = Field(None, description="Response time in milliseconds")
    version: str | None = Field(None, description="Frappe version string if available")
    error: str | None = Field(None, description="Error message if the check failed")


async def ping_handler(_request: PingErpNextRequest, context: ToolContext) -> PingErpNextResponse:
    if context.tenant is None:
        return PingErpNextResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        result = await client.ping()
        return PingErpNextResponse(
            available=result.get("available", False),
            url=context.tenant.url,
            latency_ms=result.get("latency_ms"),
            version=result.get("message") if result.get("available") else None,
        )
    except Exception as e:
        return PingErpNextResponse(error=str(e), url=context.tenant.url)


# ── Get Fieldset ────────────────────────────────────────────────────────

class GetFieldsetRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype name to get the curated field template for, e.g., 'Sales Order', 'Sales Invoice', 'Customer', 'Item', 'Supplier', 'Purchase Order'"
    )


class GetFieldsetResponse(BaseModel):
    doctype: str = Field("", description="The doctype this fieldset is for")
    fieldset: dict[str, Any] | None = Field(
        None, description="Organized field template with 'required', 'optional', and 'child_tables' sections. Each section lists field names, types, descriptions, and example values."
    )
    is_known: bool = Field(False, description="Whether this doctype has a curated fieldset. If false, use erpnext_get_doctype_meta instead.")
    error: str | None = Field(None, description="Error message if the lookup failed")


async def get_fieldset_handler(request: GetFieldsetRequest, context: ToolContext) -> GetFieldsetResponse:
    if context.tenant is None:
        return GetFieldsetResponse(error="No ERPNext tenant configured for this API key")
    try:
        from app.plugins.erpnext.fieldsets import get_fieldset
    except ImportError:
        return GetFieldsetResponse(
            doctype=request.doctype,
            is_known=False,
            error="Fieldsets module not available. Use erpnext_get_doctype_meta to discover the schema.",
        )
    try:
        fieldset = get_fieldset(request.doctype)
        if fieldset is None:
            return GetFieldsetResponse(
                doctype=request.doctype,
                is_known=False,
                error=f"No curated fieldset for '{request.doctype}'. Use erpnext_get_doctype_meta to discover the schema.",
            )
        return GetFieldsetResponse(doctype=request.doctype, fieldset=fieldset, is_known=True)
    except Exception as e:
        return GetFieldsetResponse(doctype=request.doctype, error=str(e))


# ── Run Method ──────────────────────────────────────────────────────────

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


# ── Run Report ──────────────────────────────────────────────────────────

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
    result: Any = Field(None, description="Raw report data including columns and result rows")
    columns: list[str] = Field(
        default_factory=list, description="Column names extracted from the report for easier reading"
    )
    row_count: int = Field(0, description="Number of data rows in the report")
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
        # Extract structured metadata from the report result
        columns: list[str] = []
        row_count = 0
        if isinstance(result, dict):
            cols = result.get("columns", [])
            rows = result.get("result", [])
            if isinstance(cols, list):
                columns = [
                    c.get("label", str(c)) if isinstance(c, dict) else str(c)
                    for c in cols
                ]
            if isinstance(rows, list):
                row_count = len(rows)

        return RunReportResponse(
            result=result,
            columns=columns,
            row_count=row_count,
        )
    except Exception as e:
        return RunReportResponse(error=str(e))


# ── List Reports ────────────────────────────────────────────────────────

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


# ── Get Current User ────────────────────────────────────────────────────

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


# ── Get System Info ─────────────────────────────────────────────────────

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
