from app.plugins.erpnext.fieldset_refresh import UpstreamSnapshot, reconcile_fieldset


def test_reconcile_fieldset_reports_missing_required_fields():
    snapshot = UpstreamSnapshot(
        doctype="Customer",
        source_repo="frappe/erpnext",
        source_path="erpnext/selling/doctype/customer/customer.json",
        required_fields=["customer_name", "customer_type", "territory"],
        fields=["customer_name", "customer_type", "territory", "email_id"],
    )

    result = reconcile_fieldset("Customer", snapshot)

    assert result["doctype"] == "Customer"
    assert result["missing_required"] == ["territory"]
    assert result["source_repo"] == "frappe/erpnext"


def test_reconcile_fieldset_reports_stale_and_unknown_fields():
    snapshot = UpstreamSnapshot(
        doctype="Supplier",
        source_repo="frappe/erpnext",
        source_path="erpnext/buying/doctype/supplier/supplier.json",
        required_fields=["supplier_name"],
        fields=["supplier_name", "supplier_group"],
    )

    result = reconcile_fieldset("Supplier", snapshot)

    assert "tax_id" in result["unknown_optional"]
    assert result["stale_required"] == []
