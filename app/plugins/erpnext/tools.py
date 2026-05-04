from typing import Any

from pydantic import BaseModel, Field

from app.plugins.erpnext.client import ErpNextClient
from app.schemas.tool_context import ToolContext


class GetDocRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype name, e.g., 'Sales Invoice', 'Item', 'Customer'"
    )
    docname: str = Field(
        ..., description="Document name/ID, e.g., 'SINV-24-00001'"
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
        doc = await client.get_doc(request.doctype, request.docname)
        return GetDocResponse(doc=doc)
    except Exception as e:
        return GetDocResponse(error=str(e))


class SearchDocsRequest(BaseModel):
    doctype: str = Field(
        ..., description="ERPNext doctype name, e.g., 'Item', 'Customer', 'Sales Order'"
    )
    query: str = Field(
        "", description="Optional search text to filter results by name"
    )
    fields: list[str] | None = Field(
        None, description="List of field names to return. If omitted, all fields are returned."
    )
    limit: int = Field(
        20, description="Maximum number of results to return", ge=1, le=100
    )
    order_by: str | None = Field(
        None, description="Field to sort results by, e.g., 'modified desc'"
    )


class SearchDocsResponse(BaseModel):
    results: list[dict[str, Any]] = Field(
        default_factory=list, description="List of matching documents"
    )
    count: int = Field(0, description="Number of results returned")
    error: str | None = Field(None, description="Error message if the search failed")


async def search_docs_handler(
    request: SearchDocsRequest, context: ToolContext
) -> SearchDocsResponse:
    if context.tenant is None:
        return SearchDocsResponse(error="No ERPNext tenant configured for this API key")
    client = ErpNextClient(context.tenant.url, context.tenant.api_key, context.tenant.api_secret)
    try:
        filters = None
        if request.query:
            filters = [["name", "like", f"%{request.query}%"]]
        results = await client.search_docs(
            doctype=request.doctype,
            filters=filters,
            fields=request.fields,
            limit_page_length=request.limit,
            order_by=request.order_by,
        )
        return SearchDocsResponse(results=results if isinstance(results, list) else [], count=len(results) if isinstance(results, list) else 0)
    except Exception as e:
        return SearchDocsResponse(error=str(e))
