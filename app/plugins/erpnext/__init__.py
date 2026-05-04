from app.core.registry import ToolRegistry

from . import tools


def register(registry: ToolRegistry) -> None:
    registry.register(
        name="erpnext_get_doc",
        description="Retrieve a document from ERPNext by doctype and document name. Use this to fetch any ERPNext record such as invoices, customers, items, or orders.",
        handler=tools.get_doc_handler,
        request_model=tools.GetDocRequest,
        response_model=tools.GetDocResponse,
        tags=["erpnext"],
    )
    registry.register(
        name="erpnext_search_docs",
        description="Search for documents in ERPNext by doctype with optional text search, field filtering, and sorting. Use this to find items, customers, sales orders, or any other ERPNext record type.",
        handler=tools.search_docs_handler,
        request_model=tools.SearchDocsRequest,
        response_model=tools.SearchDocsResponse,
        tags=["erpnext"],
    )
