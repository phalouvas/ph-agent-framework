"""
Curated field knowledge for common ERPNext doctypes.

Each entry is organized as:
- required: fields that MUST be provided when creating a document
- optional: commonly used optional fields with their defaults/behavior
- child_tables: nested table fields with their own field schemas

This gives the LLM pre-digested schema knowledge so it doesn't need to
call get_doctype_meta and parse the raw field array for common doctypes.
"""

FIELDSETS: dict[str, dict] = {
    "Sales Order": {
        "description": "A sales order is a confirmed order from a customer. It tracks items, quantities, rates, and delivery dates before fulfillment.",
        "naming": "SO-YYYY-NNNNN (auto-generated)",
        "lifecycle": "Draft → (optional: On Hold) → Submitted → (partial: delivered) → Completed / Cancelled",
        "required": [
            {"field": "customer", "type": "Link/Customer", "description": "The customer placing the order. Must exist in the system."},
            {"field": "company", "type": "Link/Company", "description": "Your company making the sale. Usually auto-set from defaults."},
            {"field": "delivery_date", "type": "Date", "description": "Expected delivery date, e.g. '2025-04-01'"},
            {"field": "items", "type": "Table/Sales Order Item", "description": "Line items — see child_tables below"},
        ],
        "optional": [
            {"field": "transaction_date", "type": "Date", "description": "Defaults to today."},
            {"field": "po_no", "type": "Data", "description": "Customer's purchase order reference number."},
            {"field": "currency", "type": "Link/Currency", "description": "Defaults to company currency."},
            {"field": "selling_price_list", "type": "Link/Price List", "description": "Defaults to customer's price list or 'Standard Selling'."},
            {"field": "status", "type": "Select", "description": "Auto-set. Don't provide when creating."},
            {"field": "taxes_and_charges", "type": "Link/Sales Taxes and Charges Template", "description": "Tax template to apply."},
            {"field": "terms", "type": "Text Editor", "description": "Payment/delivery terms."},
        ],
        "child_tables": {
            "items": {
                "description": "Line items for the sales order. Each item is one row in the items array.",
                "fields": [
                    {"field": "item_code", "type": "Link/Item", "required": True, "description": "Item identifier. Must exist in the system."},
                    {"field": "qty", "type": "Float", "required": True, "description": "Quantity to order."},
                    {"field": "rate", "type": "Currency", "required": True, "description": "Unit price. Auto-fetched from price list if empty."},
                    {"field": "uom", "type": "Link/UOM", "required": False, "description": "Unit of measure. Defaults to item's stock UOM."},
                    {"field": "delivery_date", "type": "Date", "required": False, "description": "Per-line delivery date. Defaults to header delivery_date."},
                    {"field": "warehouse", "type": "Link/Warehouse", "required": False, "description": "Warehouse to deliver from."},
                    {"field": "amount", "type": "Currency", "required": False, "description": "Auto-calculated as qty * rate."},
                ],
            }
        },
    },
    "Sales Invoice": {
        "description": "A sales invoice bills a customer for goods or services. It creates an accounts receivable entry.",
        "naming": "SINV-YYYY-NNNNN (auto-generated)",
        "lifecycle": "Draft → Submitted → (partial: paid via Payment Entry) → Cancelled / (amend → new Draft)",
        "required": [
            {"field": "customer", "type": "Link/Customer", "description": "The customer being billed."},
            {"field": "company", "type": "Link/Company", "description": "Your company."},
            {"field": "items", "type": "Table/Sales Invoice Item", "description": "Line items — see child_tables below"},
        ],
        "optional": [
            {"field": "posting_date", "type": "Date", "description": "Accounting date. Defaults to today."},
            {"field": "due_date", "type": "Date", "description": "Payment due date. Auto-calculated from payment terms if not set."},
            {"field": "is_pos", "type": "Check", "description": "Set to 1 for point-of-sale invoices."},
            {"field": "update_stock", "type": "Check", "description": "Set to 1 to reduce inventory on submit."},
            {"field": "taxes_and_charges", "type": "Link/Sales Taxes and Charges Template", "description": "Tax template."},
            {"field": "selling_price_list", "type": "Link/Price List", "description": "Defaults to customer's price list."},
        ],
        "child_tables": {
            "items": {
                "description": "Line items for the invoice.",
                "fields": [
                    {"field": "item_code", "type": "Link/Item", "required": True, "description": "Item identifier."},
                    {"field": "qty", "type": "Float", "required": True, "description": "Quantity."},
                    {"field": "rate", "type": "Currency", "required": True, "description": "Unit price."},
                    {"field": "income_account", "type": "Link/Account", "required": False, "description": "Revenue account. Auto-set from item or company defaults."},
                ],
            }
        },
    },
    "Purchase Order": {
        "description": "A purchase order is a confirmed order to a supplier for goods or services.",
        "naming": "PO-YYYY-NNNNN (auto-generated)",
        "lifecycle": "Draft → Submitted → (partial: received via Purchase Receipt) → Completed / Cancelled",
        "required": [
            {"field": "supplier", "type": "Link/Supplier", "description": "The supplier to order from."},
            {"field": "company", "type": "Link/Company", "description": "Your company."},
            {"field": "schedule_date", "type": "Date", "description": "Expected receipt date."},
            {"field": "items", "type": "Table/Purchase Order Item", "description": "Line items."},
        ],
        "optional": [
            {"field": "transaction_date", "type": "Date", "description": "Defaults to today."},
            {"field": "buying_price_list", "type": "Link/Price List", "description": "Defaults to supplier's price list."},
        ],
        "child_tables": {
            "items": {
                "fields": [
                    {"field": "item_code", "type": "Link/Item", "required": True, "description": "Item identifier."},
                    {"field": "qty", "type": "Float", "required": True, "description": "Quantity."},
                    {"field": "rate", "type": "Currency", "required": True, "description": "Unit price."},
                    {"field": "schedule_date", "type": "Date", "required": False, "description": "Per-line expected date."},
                    {"field": "warehouse", "type": "Link/Warehouse", "required": False, "description": "Receiving warehouse."},
                ],
            }
        },
    },
    "Customer": {
        "description": "A customer record. Customers are linked to sales transactions.",
        "naming": "Customer name (text, user-provided)",
        "required": [
            {"field": "customer_name", "type": "Data", "description": "Full display name of the customer."},
            {"field": "customer_type", "type": "Select", "description": "'Company' or 'Individual'."},
        ],
        "optional": [
            {"field": "customer_group", "type": "Link/Customer Group", "description": "Defaults to 'All Customer Groups' or 'Commercial'."},
            {"field": "territory", "type": "Link/Territory", "description": "Defaults to 'All Territories'."},
            {"field": "email_id", "type": "Data", "description": "Primary email address."},
            {"field": "mobile_no", "type": "Data", "description": "Primary phone number."},
            {"field": "tax_id", "type": "Data", "description": "Tax identification number (VAT/GST)."},
        ],
    },
    "Item": {
        "description": "An item (product or service) that can be sold or purchased.",
        "naming": "Item code (text, user-provided)",
        "required": [
            {"field": "item_code", "type": "Data", "description": "Unique item identifier/code."},
            {"field": "item_name", "type": "Data", "description": "Display name."},
            {"field": "item_group", "type": "Link/Item Group", "description": "Category. Must exist in the system, e.g. 'Raw Material', 'Products', 'Services'."},
            {"field": "stock_uom", "type": "Link/UOM", "description": "Default unit of measure, e.g. 'Nos', 'Kg', 'Meter', 'Hour'."},
        ],
        "optional": [
            {"field": "description", "type": "Text Editor", "description": "Long description."},
            {"field": "standard_rate", "type": "Currency", "description": "Default selling price."},
            {"field": "is_stock_item", "type": "Check", "description": "Set to 1 for physical inventory items. 0 for services."},
            {"field": "is_sales_item", "type": "Check", "description": "Defaults to 1. Set to 0 if not for sale."},
            {"field": "is_purchase_item", "type": "Check", "description": "Defaults to 1. Set to 0 if not for purchase."},
            {"field": "default_warehouse", "type": "Link/Warehouse", "description": "Default storage warehouse."},
        ],
    },
    "Supplier": {
        "description": "A supplier record. Suppliers are linked to purchase transactions.",
        "naming": "Supplier name (text, user-provided)",
        "required": [
            {"field": "supplier_name", "type": "Data", "description": "Display name of the supplier."},
            {"field": "supplier_group", "type": "Link/Supplier Group", "description": "Category, e.g. 'Local', 'Services', 'Raw Material'."},
        ],
        "optional": [
            {"field": "email_id", "type": "Data", "description": "Primary email."},
            {"field": "mobile_no", "type": "Data", "description": "Primary phone."},
            {"field": "tax_id", "type": "Data", "description": "Tax ID."},
        ],
    },
    "Lead": {
        "description": "A sales lead or prospect that may convert to a Customer or Opportunity.",
        "naming": "LEAD-YYYY-NNNNN (auto-generated)",
        "required": [
            {"field": "lead_name", "type": "Data", "description": "Full name or company name of the lead."},
        ],
        "optional": [
            {"field": "email_id", "type": "Data", "description": "Email address."},
            {"field": "mobile_no", "type": "Data", "description": "Phone number."},
            {"field": "source", "type": "Link/Lead Source", "description": "How the lead was acquired, e.g. 'Website', 'Referral', 'Campaign'."},
            {"field": "status", "type": "Select", "description": "Auto-set. Don't provide when creating. Values: 'Lead', 'Open', 'Replied', 'Opportunity', 'Converted', 'Do Not Contact'."},
        ],
    },
}


def get_fieldset(doctype: str) -> dict | None:
    """Return the curated fieldset for a doctype, or None if not known."""
    return FIELDSETS.get(doctype)
