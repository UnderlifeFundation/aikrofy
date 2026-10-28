"""
ERP Driver Factory
Resolves the correct driver instance based on company ERP configuration.
"""
from typing import Optional
from services.erp.driver_interface import BaseERPDriver


def get_erp_driver(company) -> Optional[BaseERPDriver]:
    """
    Factory function: given a Company model instance, look up its
    ERPConfig and return the matching platform driver ready to use.

    Returns None if the company has no ERP configured.
    """
    from extensions import db

    # Preventive rollback (MySQL "gone away" protection)
    try:
        db.session.rollback()
    except Exception:
        pass

    config = getattr(company, 'erp_config', None)
    if not config or not config.platform:
        return None

    platform = config.platform.value  # e.g. 'sap_b1'
    erp_url = config.erp_url
    credentials = config.credentials or {}

    drivers = {
        'sap_b1': _build_sap_b1,
        'netsuite': _build_netsuite,
        'odoo': _build_odoo,
        'dynamics_bc': _build_dynamics_bc,
        'contifico': _build_contifico,
        'mysql': _build_mysql,
    }

    builder = drivers.get(platform)
    if not builder:
        raise ValueError(f"Unsupported ERP platform: {platform}")

    return builder(erp_url, credentials)


# ------------------------------------------------------------------
# Builder helpers (lazy imports to avoid circular deps)
# ------------------------------------------------------------------

def _build_sap_b1(erp_url, credentials):
    from services.erp.drivers.sap_b1 import SAPBusinessOneDriver
    return SAPBusinessOneDriver(erp_url, credentials)


def _build_netsuite(erp_url, credentials):
    from services.erp.drivers.netsuite import NetSuiteDriver
    return NetSuiteDriver(erp_url, credentials)


def _build_odoo(erp_url, credentials):
    from services.erp.drivers.odoo import OdooRPCDriver
    return OdooRPCDriver(erp_url, credentials)


def _build_dynamics_bc(erp_url, credentials):
    from services.erp.drivers.dynamics_bc import DynamicsBCDriver
    return DynamicsBCDriver(erp_url, credentials)


def _build_contifico(erp_url, credentials):
    from services.erp.drivers.contifico import ContificoDriver
    return ContificoDriver(erp_url, credentials)


def _build_mysql(erp_url, credentials):
    from services.erp.drivers.mysql import MySQLDriver
    return MySQLDriver(erp_url, credentials)

