"""
E-commerce Adapter Factory
Resolves the correct adapter instance based on company configuration.
"""
from typing import Optional
from services.ecommerce.base import BaseEcommerceAdapter


def get_ecommerce_adapter(company) -> Optional[BaseEcommerceAdapter]:
    """
    Factory function: given a Company model instance, look up its
    EcommerceConfig and return the matching platform adapter ready to use.

    Returns None if the company has no e-commerce configured.
    """
    from extensions import db

    # Preventive rollback (MySQL "gone away" protection)
    try:
        db.session.rollback()
    except Exception:
        pass

    config = getattr(company, 'ecommerce_config', None)
    if not config or not config.platform:
        from .native_adapter import NativeCatalogAdapter
        return NativeCatalogAdapter(company_id=company.id, company_name=company.name)

    platform = config.platform.value  # e.g. 'shopify'
    if platform == 'native':
        from .native_adapter import NativeCatalogAdapter
        return NativeCatalogAdapter(company_id=company.id, company_name=company.name)
    store_url = config.store_url
    credentials = config.credentials or {}

    adapters = {
        'shopify': _build_shopify,
        'woocommerce': _build_woocommerce,
        'vtex': _build_vtex,
        'magento': _build_magento,
        'prestashop': _build_prestashop,
        'bigcommerce': _build_bigcommerce,
    }

    builder = adapters.get(platform)
    if not builder:
        raise ValueError(f"Unsupported e-commerce platform: {platform}")

    return builder(store_url, credentials)


# ------------------------------------------------------------------
# Builder helpers (lazy imports to avoid circular deps)
# ------------------------------------------------------------------

def _build_shopify(store_url, credentials):
    from services.ecommerce.shopify_adapter import ShopifyAdapter
    return ShopifyAdapter(store_url, credentials)


def _build_woocommerce(store_url, credentials):
    from services.ecommerce.woocommerce_adapter import WooCommerceAdapter
    return WooCommerceAdapter(store_url, credentials)


def _build_vtex(store_url, credentials):
    from services.ecommerce.vtex_adapter import VTEXAdapter
    return VTEXAdapter(store_url, credentials)


def _build_magento(store_url, credentials):
    from services.ecommerce.magento_adapter import MagentoAdapter
    return MagentoAdapter(store_url, credentials)


def _build_prestashop(store_url, credentials):
    from services.ecommerce.prestashop_adapter import PrestaShopAdapter
    return PrestaShopAdapter(store_url, credentials)


def _build_bigcommerce(store_url, credentials):
    from services.ecommerce.bigcommerce_adapter import BigCommerceAdapter
    return BigCommerceAdapter(store_url, credentials)
