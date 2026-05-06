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
            {"field": "supplier_type", "type": "Select", "description": "Supplier classification, e.g. 'Company', 'Individual'."},
        ],
        "optional": [
            {"field": "supplier_group", "type": "Link/Supplier Group", "description": "Category, e.g. 'Local', 'Services', 'Raw Material'."},
            {"field": "email_id", "type": "Data", "description": "Primary email."},
            {"field": "mobile_no", "type": "Data", "description": "Primary phone."},
            {"field": "tax_id", "type": "Data", "description": "Tax ID."},
        ],
    },
    "Purchase Invoice": {
        "description": "Supplier billing document. Advisory template only; live doctype metadata remains authoritative for write safety.",
        "naming": "PINV-YYYY-NNNNN (auto-generated)",
        "required": [
            {"field": "supplier", "type": "Link/Supplier", "description": "Supplier being billed."},
            {"field": "company", "type": "Link/Company", "description": "Your company."},
            {"field": "items", "type": "Table/Purchase Invoice Item", "description": "Line items for the invoice."},
        ],
        "optional": [
            {"field": "posting_date", "type": "Date", "description": "Accounting date. Defaults to today."},
            {"field": "due_date", "type": "Date", "description": "Supplier payment due date."},
            {"field": "bill_no", "type": "Data", "description": "Supplier invoice number."},
            {"field": "update_stock", "type": "Check", "description": "Set to 1 when invoice should also update stock."},
        ],
        "child_tables": {
            "items": {
                "fields": [
                    {"field": "item_code", "type": "Link/Item", "required": True, "description": "Item identifier."},
                    {"field": "qty", "type": "Float", "required": True, "description": "Quantity."},
                    {"field": "rate", "type": "Currency", "required": True, "description": "Unit purchase rate."},
                    {"field": "expense_account", "type": "Link/Account", "required": False, "description": "Expense account, often defaulted from item/company."},
                ]
            }
        },
    },
    "Payment Entry": {
        "description": "Represents money received or paid. Tenant setups vary; treat optional fields as non-authoritative hints.",
        "naming": "ACC-PAY-YYYY-NNNNN (auto-generated)",
        "required": [
            {"field": "payment_type", "type": "Select", "description": "Receive or Pay."},
            {"field": "party_type", "type": "Select", "description": "Customer or Supplier."},
            {"field": "party", "type": "Dynamic Link", "description": "Party value matching party_type."},
            {"field": "paid_amount", "type": "Currency", "description": "Amount paid or received."},
        ],
        "optional": [
            {"field": "posting_date", "type": "Date", "description": "Transaction posting date."},
            {"field": "paid_from", "type": "Link/Account", "description": "Source account."},
            {"field": "paid_to", "type": "Link/Account", "description": "Destination account."},
            {"field": "references", "type": "Table/Payment Entry Reference", "description": "Allocate payment to invoices/orders."},
        ],
    },
    "Journal Entry": {
        "description": "Manual accounting entry. Child rows drive debits/credits and must balance.",
        "naming": "ACC-JV-YYYY-NNNNN (auto-generated)",
        "required": [
            {"field": "voucher_type", "type": "Select", "description": "Entry type, e.g. Journal Entry, Bank Entry."},
            {"field": "posting_date", "type": "Date", "description": "Accounting date."},
            {"field": "accounts", "type": "Table/Journal Entry Account", "description": "Debit/credit lines; totals must balance."},
            {"field": "company", "type": "Link/Company", "description": "Company ledger context."},
        ],
        "optional": [
            {"field": "user_remark", "type": "Data", "description": "Narrative for the entry."},
            {"field": "cheque_no", "type": "Data", "description": "Reference instrument number."},
        ],
    },
    "Purchase Receipt": {
        "description": "Goods receipt from supplier. Usually linked to Purchase Order.",
        "naming": "MAT-PRE-YYYY-NNNNN (auto-generated)",
        "required": [
            {"field": "supplier", "type": "Link/Supplier", "description": "Supplier delivering goods."},
            {"field": "company", "type": "Link/Company", "description": "Receiving company."},
            {"field": "posting_date", "type": "Date", "description": "Receipt date."},
            {"field": "items", "type": "Table/Purchase Receipt Item", "description": "Received item rows."},
        ],
        "optional": [
            {"field": "set_warehouse", "type": "Link/Warehouse", "description": "Default target warehouse for lines."},
            {"field": "bill_no", "type": "Data", "description": "Supplier bill number reference."},
        ],
    },
    "Material Request": {
        "description": "Internal request for material movement, procurement, or transfer.",
        "naming": "MAT-MR-YYYY-NNNNN (auto-generated)",
        "required": [
            {"field": "material_request_type", "type": "Select", "description": "Purchase, Material Transfer, Material Issue, etc."},
            {"field": "schedule_date", "type": "Date", "description": "Required-by date."},
            {"field": "company", "type": "Link/Company", "description": "Requesting company."},
            {"field": "items", "type": "Table/Material Request Item", "description": "Requested item rows."},
        ],
        "optional": [
            {"field": "set_from_warehouse", "type": "Link/Warehouse", "description": "Default source warehouse."},
            {"field": "set_warehouse", "type": "Link/Warehouse", "description": "Default target warehouse."},
        ],
    },
    "Stock Entry": {
        "description": "Inventory movement transaction (transfer, receipt, manufacture, repack, issue).",
        "naming": "MAT-STE-YYYY-NNNNN (auto-generated)",
        "required": [
            {"field": "stock_entry_type", "type": "Select", "description": "Purpose of stock movement."},
            {"field": "company", "type": "Link/Company", "description": "Company context."},
            {"field": "items", "type": "Table/Stock Entry Detail", "description": "Stock rows with source/target warehouses."},
        ],
        "optional": [
            {"field": "posting_date", "type": "Date", "description": "Posting date."},
            {"field": "from_warehouse", "type": "Link/Warehouse", "description": "Default source warehouse."},
            {"field": "to_warehouse", "type": "Link/Warehouse", "description": "Default target warehouse."},
        ],
    },
    "Stock Reconciliation": {
        "description": "Adjust stock quantities and valuation to match physical inventory.",
        "naming": "MAT-RECO-YYYY-NNNNN (auto-generated)",
        "required": [
            {"field": "company", "type": "Link/Company", "description": "Company context."},
            {"field": "posting_date", "type": "Date", "description": "Date of reconciliation."},
            {"field": "items", "type": "Table/Stock Reconciliation Item", "description": "Rows defining reconciled qty/rate by warehouse."},
        ],
        "optional": [
            {"field": "set_warehouse", "type": "Link/Warehouse", "description": "Default warehouse for rows."},
            {"field": "purpose", "type": "Small Text", "description": "Reason for adjustment."},
        ],
    },
    "Employee": {
        "description": "HR master record for an employee. Tenant-specific HR custom fields are common.",
        "naming": "HR-EMP-YYYY-NNNNN (auto-generated or series)",
        "required": [
            {"field": "first_name", "type": "Data", "description": "Employee first name."},
            {"field": "company", "type": "Link/Company", "description": "Employing company."},
            {"field": "date_of_joining", "type": "Date", "description": "Join date."},
            {"field": "date_of_birth", "type": "Date", "description": "Date of birth."},
            {"field": "gender", "type": "Select", "description": "Gender."},
            {"field": "status", "type": "Select", "description": "Employment status (Active, Left, On Leave)."},
        ],
        "optional": [
            {"field": "last_name", "type": "Data", "description": "Employee last name."},
            {"field": "department", "type": "Link/Department", "description": "Department link."},
            {"field": "designation", "type": "Link/Designation", "description": "Job title."},
        ],
    },
    "Expense Claim": {
        "description": "Employee expense reimbursement request.",
        "naming": "EXP-CLM-YYYY-NNNNN (auto-generated)",
        "required": [
            {"field": "employee", "type": "Link/Employee", "description": "Claiming employee."},
            {"field": "company", "type": "Link/Company", "description": "Company that reimburses."},
            {"field": "expenses", "type": "Table/Expense Claim Detail", "description": "Expense rows with type/date/amount."},
        ],
        "optional": [
            {"field": "posting_date", "type": "Date", "description": "Claim creation accounting date."},
            {"field": "payable_account", "type": "Link/Account", "description": "Liability account for reimbursement."},
        ],
    },
    "Opportunity": {
        "description": "CRM opportunity linked to a lead/customer and potential revenue.",
        "naming": "OPTY-YYYY-NNNNN (auto-generated)",
        "required": [
            {"field": "opportunity_from", "type": "Select", "description": "Source entity type (Lead or Customer)."},
            {"field": "party_name", "type": "Dynamic Link", "description": "Lead/Customer value matching opportunity_from."},
            {"field": "opportunity_type", "type": "Link/Opportunity Type", "description": "Opportunity classification."},
        ],
        "optional": [
            {"field": "expected_closing", "type": "Date", "description": "Expected close date."},
            {"field": "sales_stage", "type": "Link/Sales Stage", "description": "Current sales stage."},
            {"field": "items", "type": "Table/Opportunity Item", "description": "Potential item lines and values."},
        ],
    },
    "Quotation": {
        "description": "Selling quotation for a lead/customer before order confirmation.",
        "naming": "QTN-YYYY-NNNNN (auto-generated)",
        "required": [
            {"field": "quotation_to", "type": "Select", "description": "Lead, Customer, or Prospect."},
            {"field": "party_name", "type": "Dynamic Link", "description": "Party matching quotation_to."},
            {"field": "company", "type": "Link/Company", "description": "Selling company."},
            {"field": "items", "type": "Table/Quotation Item", "description": "Quoted line items."},
        ],
        "optional": [
            {"field": "transaction_date", "type": "Date", "description": "Quotation date."},
            {"field": "valid_till", "type": "Date", "description": "Quotation validity date."},
            {"field": "order_type", "type": "Select", "description": "Sales or Maintenance."},
        ],
    },
    "BOM": {
        "description": "Bill of materials for manufacturing finished goods.",
        "naming": "BOM-ITEM-### (auto-generated)",
        "required": [
            {"field": "company", "type": "Link/Company", "description": "Manufacturing company context."},
            {"field": "item", "type": "Link/Item", "description": "Finished good item code."},
            {"field": "quantity", "type": "Float", "description": "Output quantity for the BOM."},
            {"field": "items", "type": "Table/BOM Item", "description": "Raw materials/components."},
            {"field": "conversion_rate", "type": "Float", "description": "Conversion rate for currency."},
            {"field": "currency", "type": "Link/Currency", "description": "BOM currency."},
        ],
        "optional": [
            {"field": "is_active", "type": "Check", "description": "Active BOM flag."},
            {"field": "is_default", "type": "Check", "description": "Default BOM for item."},
            {"field": "with_operations", "type": "Check", "description": "Enable operation routing/workstations."},
        ],
    },
    "Work Order": {
        "description": "Production order generated for a BOM and manufacturing quantity.",
        "naming": "MFG-WO-YYYY-NNNNN (auto-generated)",
        "required": [
            {"field": "production_item", "type": "Link/Item", "description": "Finished good item."},
            {"field": "bom_no", "type": "Link/BOM", "description": "BOM used for production."},
            {"field": "qty", "type": "Float", "description": "Production quantity."},
            {"field": "company", "type": "Link/Company", "description": "Manufacturing company."},
        ],
        "optional": [
            {"field": "fg_warehouse", "type": "Link/Warehouse", "description": "Finished goods warehouse."},
            {"field": "wip_warehouse", "type": "Link/Warehouse", "description": "Work-in-progress warehouse."},
            {"field": "planned_start_date", "type": "Date", "description": "Planned production start date."},
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
