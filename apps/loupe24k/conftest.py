"""
pytest conftest — stubs out the `frappe` package so controller unit tests can
run outside a Frappe bench environment.

Only the attributes actually used by the loupe24k controllers are stubbed;
everything else is a MagicMock so any unexpected access surfaces immediately
in tests rather than silently returning a truthy value.
"""
import sys
from types import ModuleType
from unittest.mock import MagicMock


def _make_frappe_stub():
    frappe = ModuleType("frappe")

    # --- db helpers used by MetalRate and KarigarReconciliation ---
    frappe.db = MagicMock()

    # --- utils used by KarigarMetalIssue ---
    frappe.utils = MagicMock()

    # --- document loading used by KarigarReconciliation._pull_issue_data ---
    frappe.get_doc = MagicMock()

    # --- logger (used by seed_data) ---
    frappe.logger = MagicMock(return_value=MagicMock())

    # --- misc ---
    frappe._ = lambda s: s
    frappe.throw = MagicMock(side_effect=Exception)
    frappe.msgprint = MagicMock()

    return frappe


def _make_document_stub():
    """Minimal Document base class — stores nothing, does nothing."""

    class Document:
        pass

    return Document


# Register stubs before any test module is imported
if "frappe" not in sys.modules:
    frappe_stub = _make_frappe_stub()
    sys.modules["frappe"] = frappe_stub

    # frappe.model.document
    model_mod = ModuleType("frappe.model")
    doc_mod = ModuleType("frappe.model.document")
    doc_mod.Document = _make_document_stub()
    sys.modules["frappe.model"] = model_mod
    sys.modules["frappe.model.document"] = doc_mod
    frappe_stub.model = model_mod
    model_mod.document = doc_mod
