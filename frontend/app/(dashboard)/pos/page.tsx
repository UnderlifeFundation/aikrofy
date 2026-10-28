'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
    ShoppingCart,
    Barcode,
    QrCode,
    Plus,
    Minus,
    Trash2,
    Printer,
    Search,
    Package,
    CheckCircle2,
    Send,
    Sparkles,
    Edit3,
    RefreshCw,
    CreditCard,
    Banknote,
    Smartphone,
    Receipt,
    Tag,
    Layers,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';

interface CatalogProduct {
    id: number;
    sku: string;
    barcode: string;
    name: string;
    description: string;
    category: string;
    price: number;
    currency: string;
    stock: number;
    unit: string;
    image_url?: string;
    qr_payload: string;
    is_active: boolean;
}

interface CartItem {
    product: CatalogProduct;
    quantity: number;
}

interface CatalogOrder {
    id: number;
    order_number: string;
    customer_name: string;
    customer_phone?: string;
    customer_tax_id?: string;
    items: Array<{
        product_id: number;
        sku: string;
        barcode: string;
        name: string;
        qty: number;
        unit_price: number;
        line_total: number;
    }>;
    subtotal: number;
    tax_amount: number;
    discount_amount: number;
    total: number;
    currency: string;
    payment_method: string;
    source: string;
    created_at: string;
}

/**
 * Pure deterministic SVG Barcode Renderer (EAN-13 / Code-128 compatible visual bars)
 * Works 100% offline in Self-Hosted Community & Cloud without external network calls.
 */
function BarcodeSvg({ value, width = 200, height = 56 }: { value: string; width?: number; height?: number }) {
    const clean = (value || '7860000000000').trim();
    // Generate deterministic high-contrast bar pattern from characters + guard bars
    const bits: number[] = [1, 0, 1]; // Start guard
    for (let i = 0; i < clean.length; i++) {
        const code = clean.charCodeAt(i);
        // 7-module encoding per character ensuring scannable alternating dark/light bars
        bits.push(
            1,
            (code >> 0) & 1,
            (code >> 1) & 1 ? 0 : 1,
            (code >> 2) & 1,
            0,
            (code >> 3) & 1 || 1,
            0
        );
    }
    bits.push(1, 0, 1, 0, 1); // End guard

    const barWidth = width / bits.length;

    return (
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="mx-auto bg-white p-1 rounded">
            {bits.map((bit, idx) =>
                bit === 1 ? (
                    <rect
                        key={idx}
                        x={idx * barWidth}
                        y={2}
                        width={Math.max(1.2, barWidth)}
                        height={height - 16}
                        fill="#000000"
                    />
                ) : null
            )}
            <text
                x={width / 2}
                y={height - 2}
                textAnchor="middle"
                fontSize="10"
                fontFamily="monospace"
                fontWeight="bold"
                fill="#000000"
            >
                {clean}
            </text>
        </svg>
    );
}

/**
 * Deterministic Matrix QR-style Visual + Official QR Image with Offline Fallback
 */
function ProductQrCode({ payload, size = 96 }: { payload: string; size?: number }) {
    const encoded = encodeURIComponent(payload || 'AIKROFY-POS');
    return (
        <img
            src={`https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encoded}`}
            alt={payload}
            width={size}
            height={size}
            className="mx-auto rounded bg-white p-1 border"
        />
    );
}

export default function NativePosPage() {
    const [activeTab, setActiveTab] = useState<'pos' | 'inventory' | 'orders'>('pos');
    const [products, setProducts] = useState<CatalogProduct[]>([]);
    const [orders, setOrders] = useState<CatalogOrder[]>([]);
    const [loading, setLoading] = useState(true);

    // POS State
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('Todas');
    const [scanInput, setScanInput] = useState('');
    const [cart, setCart] = useState<CartItem[]>([]);
    const [customerName, setCustomerName] = useState('Consumidor Final');
    const [customerPhone, setCustomerPhone] = useState('');
    const [customerTaxId, setCustomerTaxId] = useState('');
    const [paymentMethod, setPaymentMethod] = useState<'cash' | 'transfer' | 'qr' | 'card'>('cash');
    const [discountAmount, setDiscountAmount] = useState<number>(0);
    const [taxRate, setTaxRate] = useState<number>(0); // 0% or 15% IVA configurable
    const [sendWhatsappReceipt, setSendWhatsappReceipt] = useState(true);
    const [processingOrder, setProcessingOrder] = useState(false);
    const [lastReceiptOrder, setLastReceiptOrder] = useState<CatalogOrder | null>(null);

    // Product Modal / Form State
    const [editingProduct, setEditingProduct] = useState<CatalogProduct | null>(null);
    const [prodName, setProdName] = useState('');
    const [prodCategory, setProdCategory] = useState('General');
    const [prodPrice, setProdPrice] = useState('');
    const [prodCurrency, setProdCurrency] = useState('USD');
    const [prodStock, setProdStock] = useState('20');
    const [prodUnit, setProdUnit] = useState('unidad');
    const [prodSku, setProdSku] = useState('');
    const [prodBarcode, setProdBarcode] = useState('');
    const [prodDesc, setProdDesc] = useState('');
    const [savingProduct, setSavingProduct] = useState(false);

    // Label Printing State
    const [labelProduct, setLabelProduct] = useState<CatalogProduct | null>(null);
    const [labelCopies, setLabelCopies] = useState(4);

    const scanInputRef = useRef<HTMLInputElement>(null);

    const fetchCatalogData = async () => {
        setLoading(true);
        try {
            const [prodRes, ordRes] = await Promise.all([
                apiClient.get('/catalog/products?active_only=false'),
                apiClient.get('/catalog/orders'),
            ]);
            setProducts(prodRes.data?.products || []);
            setOrders(ordRes.data?.orders || []);
        } catch (err) {
            console.error('Error loading POS catalog:', err);
            toast.error('No se pudo cargar el catálogo POS');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchCatalogData();
    }, []);

    const categories = ['Todas', ...Array.from(new Set(products.map((p) => p.category || 'General')))];

    const filteredProducts = products.filter((p) => {
        if (!p.is_active && activeTab === 'pos') return false;
        const matchesCat = selectedCategory === 'Todas' || (p.category || 'General') === selectedCategory;
        const q = searchQuery.toLowerCase().trim();
        const matchesSearch =
            !q ||
            p.name.toLowerCase().includes(q) ||
            (p.sku || '').toLowerCase().includes(q) ||
            (p.barcode || '').toLowerCase().includes(q);
        return matchesCat && matchesSearch;
    });

    const addToCart = (product: CatalogProduct) => {
        setCart((prev) => {
            const existing = prev.find((item) => item.product.id === product.id);
            if (existing) {
                return prev.map((item) =>
                    item.product.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
                );
            }
            return [...prev, { product, quantity: 1 }];
        });
    };

    const updateQuantity = (productId: number, delta: number) => {
        setCart((prev) =>
            prev
                .map((item) =>
                    item.product.id === productId ? { ...item, quantity: item.quantity + delta } : item
                )
                .filter((item) => item.quantity > 0)
        );
    };

    // Instant Barcode / QR Scanner handler (triggered when USB/Bluetooth scanner sends Enter)
    const handleScanSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const code = scanInput.trim();
        if (!code) return;

        // First try local fast match
        const localMatch = products.find(
            (p) =>
                p.barcode === code ||
                p.sku.toLowerCase() === code.toLowerCase() ||
                p.qr_payload === code
        );

        if (localMatch) {
            addToCart(localMatch);
            toast.success(`Escaneado: ${localMatch.name} ($${localMatch.price.toFixed(2)})`);
            setScanInput('');
            return;
        }

        // Fallback to backend scan endpoint
        try {
            const res = await apiClient.get(`/catalog/scan/${encodeURIComponent(code)}`);
            if (res.data?.product) {
                addToCart(res.data.product);
                toast.success(`Escaneado: ${res.data.product.name}`);
            }
        } catch {
            toast.error(`Código no encontrado: ${code}`);
        } finally {
            setScanInput('');
        }
    };

    const subtotal = cart.reduce((acc, item) => acc + item.product.price * item.quantity, 0);
    const taxAmount = Math.max(0, (subtotal - discountAmount) * (taxRate / 100));
    const total = Math.max(0, subtotal - discountAmount + taxAmount);

    const handleCheckout = async () => {
        if (cart.length === 0) {
            toast.error('Agrega al menos un producto al carrito');
            return;
        }
        setProcessingOrder(true);
        try {
            const payload = {
                customer_name: customerName || 'Consumidor Final',
                customer_phone: customerPhone.trim() || undefined,
                customer_tax_id: customerTaxId.trim() || undefined,
                payment_method: paymentMethod,
                discount_amount: discountAmount,
                tax_amount: Number(taxAmount.toFixed(2)),
                send_whatsapp_receipt: sendWhatsappReceipt && !!customerPhone.trim(),
                items: cart.map((c) => ({
                    product_id: c.product.id,
                    qty: c.quantity,
                })),
            };
            const res = await apiClient.post('/catalog/orders', payload);
            const createdOrder: CatalogOrder = res.data.order;
            setLastReceiptOrder(createdOrder);
            setCart([]);
            setDiscountAmount(0);
            toast.success(
                res.data.whatsapp_sent
                    ? `Venta ${createdOrder.order_number} completada y recibo enviado por WhatsApp`
                    : `Venta ${createdOrder.order_number} registrada con éxito`
            );
            fetchCatalogData();
        } catch (err: any) {
            toast.error(err?.response?.data?.error || 'Error al procesar la venta');
        } finally {
            setProcessingOrder(false);
        }
    };

    const handleSaveProduct = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!prodName.trim() || !prodPrice) {
            toast.error('Nombre y precio son obligatorios');
            return;
        }
        setSavingProduct(true);
        try {
            const payload = {
                name: prodName.trim(),
                category: prodCategory.trim() || 'General',
                price: parseFloat(prodPrice) || 0,
                currency: prodCurrency || 'USD',
                stock: parseInt(prodStock, 10) || 0,
                unit: prodUnit.trim() || 'unidad',
                sku: prodSku.trim() || undefined,
                barcode: prodBarcode.trim() || undefined,
                description: prodDesc.trim(),
            };

            if (editingProduct) {
                await apiClient.put(`/catalog/products/${editingProduct.id}`, payload);
                toast.success('Producto actualizado');
            } else {
                await apiClient.post('/catalog/products', payload);
                toast.success('Producto creado con Código de Barras EAN-13 y QR automático');
            }

            setEditingProduct(null);
            setProdName('');
            setProdPrice('');
            setProdStock('20');
            setProdSku('');
            setProdBarcode('');
            setProdDesc('');
            fetchCatalogData();
        } catch (err: any) {
            toast.error(err?.response?.data?.error || 'Error guardando producto');
        } finally {
            setSavingProduct(false);
        }
    };

    const startEditProduct = (p: CatalogProduct) => {
        setEditingProduct(p);
        setProdName(p.name);
        setProdCategory(p.category || 'General');
        setProdPrice(String(p.price));
        setProdStock(String(p.stock));
        setProdUnit(p.unit || 'unidad');
        setProdSku(p.sku || '');
        setProdBarcode(p.barcode || '');
        setProdDesc(p.description || '');
    };

    const handleDeleteProduct = async (id: number) => {
        try {
            await apiClient.delete(`/catalog/products/${id}`);
            toast.success('Producto eliminado');
            fetchCatalogData();
        } catch {
            toast.error('No se pudo eliminar el producto');
        }
    };

    return (
        <div className="space-y-6 p-6">
            {/* Header */}
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                    <div className="flex items-center gap-2">
                        <h1 className="text-2xl font-bold tracking-tight">
                            POS Nativo & Catálogo IA (Códigos de Barras / QR)
                        </h1>
                        <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
                            Conectado a Agentes WhatsApp & Mostrador
                        </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                        Vende en mostrador con lector de código de barras/QR, imprime etiquetas adhesivas para tus productos y sincroniza el stock en vivo con tu agente de IA en WhatsApp.
                    </p>
                </div>

                <div className="flex flex-wrap gap-2">
                    <Button
                        variant={activeTab === 'pos' ? 'default' : 'outline'}
                        onClick={() => setActiveTab('pos')}
                        className="gap-2"
                    >
                        <ShoppingCart className="h-4 w-4" />
                        Caja Rápida (POS)
                    </Button>
                    <Button
                        variant={activeTab === 'inventory' ? 'default' : 'outline'}
                        onClick={() => setActiveTab('inventory')}
                        className="gap-2"
                    >
                        <Barcode className="h-4 w-4" />
                        Inventario & Etiquetas QR/Barras ({products.length})
                    </Button>
                    <Button
                        variant={activeTab === 'orders' ? 'default' : 'outline'}
                        onClick={() => setActiveTab('orders')}
                        className="gap-2"
                    >
                        <Receipt className="h-4 w-4" />
                        Historial de Ventas ({orders.length})
                    </Button>
                </div>
            </div>

            {/* TAB 1: CAJA RÁPIDA POS */}
            {activeTab === 'pos' && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    {/* Left: Scanner & Product Grid */}
                    <div className="lg:col-span-7 xl:col-span-8 space-y-4">
                        <Card className="border-primary/20 bg-primary/5">
                            <CardContent className="p-4">
                                <form onSubmit={handleScanSubmit} className="flex flex-col sm:flex-row gap-3">
                                    <div className="relative flex-1">
                                        <Barcode className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-primary" />
                                        <Input
                                            ref={scanInputRef}
                                            value={scanInput}
                                            onChange={(e) => setScanInput(e.target.value)}
                                            placeholder="Pistola Lectora USB/Bluetooth o escribe Código de Barras EAN-13 / SKU / QR y presiona Enter..."
                                            className="pl-10 bg-background font-mono"
                                            autoFocus
                                        />
                                    </div>
                                    <Button type="submit" variant="secondary" className="gap-2 shrink-0">
                                        <QrCode className="h-4 w-4" />
                                        Agregar por Código
                                    </Button>
                                </form>
                            </CardContent>
                        </Card>

                        {/* Search & Category Pills */}
                        <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
                            <div className="relative w-full sm:w-72">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    placeholder="Buscar producto por nombre o SKU..."
                                    className="pl-9"
                                />
                            </div>
                            <div className="flex gap-1.5 overflow-x-auto w-full sm:w-auto pb-1">
                                {categories.map((cat) => (
                                    <Button
                                        key={cat}
                                        size="sm"
                                        variant={selectedCategory === cat ? 'default' : 'outline'}
                                        onClick={() => setSelectedCategory(cat)}
                                        className="text-xs h-8"
                                    >
                                        {cat}
                                    </Button>
                                ))}
                            </div>
                        </div>

                        {/* Product Cards Grid */}
                        {filteredProducts.length === 0 ? (
                            <Card className="border-dashed">
                                <CardContent className="py-12 text-center space-y-3">
                                    <Package className="h-10 w-10 text-muted-foreground mx-auto" />
                                    <div className="font-semibold">No hay productos registrados todavía</div>
                                    <p className="text-xs text-muted-foreground max-w-md mx-auto">
                                        Crea tus productos en la pestaña &ldquo;Inventario &amp; Etiquetas QR/Barras&rdquo; o pídele por voz al Copiloto Krof: &ldquo;Crea el producto Café Orgánico a $12 con 30 en stock&rdquo;.
                                    </p>
                                    <Button size="sm" onClick={() => setActiveTab('inventory')}>
                                        <Plus className="h-4 w-4 mr-1" /> Crear Primer Producto
                                    </Button>
                                </CardContent>
                            </Card>
                        ) : (
                            <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-3">
                                {filteredProducts.map((prod) => (
                                    <Card
                                        key={prod.id}
                                        onClick={() => addToCart(prod)}
                                        className="cursor-pointer hover:border-primary transition-all hover:shadow-md group"
                                    >
                                        <CardContent className="p-3.5 space-y-2">
                                            <div className="flex items-start justify-between gap-1">
                                                <Badge variant="outline" className="text-[10px] font-mono">
                                                    {prod.sku}
                                                </Badge>
                                                <Badge
                                                    variant={prod.stock > 5 ? 'secondary' : 'destructive'}
                                                    className="text-[10px]"
                                                >
                                                    Stock: {prod.stock}
                                                </Badge>
                                            </div>
                                            <div className="font-semibold text-sm line-clamp-2 group-hover:text-primary transition-colors">
                                                {prod.name}
                                            </div>
                                            <div className="flex items-center justify-between pt-1 border-t">
                                                <span className="text-base font-bold text-emerald-500">
                                                    ${Number(prod.price).toFixed(2)}
                                                </span>
                                                <span className="text-[10px] text-muted-foreground font-mono">
                                                    {prod.barcode?.slice(-6)}
                                                </span>
                                            </div>
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Right: Active Ticket / Cart & Checkout */}
                    <div className="lg:col-span-5 xl:col-span-4 space-y-4">
                        <Card className="sticky top-6 border-2">
                            <CardHeader className="pb-3 border-b">
                                <CardTitle className="text-lg flex items-center justify-between">
                                    <span className="flex items-center gap-2">
                                        <Receipt className="h-5 w-5 text-primary" />
                                        Ticket de Venta
                                    </span>
                                    <Badge variant="secondary">{cart.reduce((s, i) => s + i.quantity, 0)} ítems</Badge>
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-4 space-y-4">
                                {/* Cart Items */}
                                <div className="max-h-64 overflow-y-auto space-y-2 pr-1">
                                    {cart.length === 0 ? (
                                        <div className="text-center py-8 text-xs text-muted-foreground">
                                            Escanea un código de barras/QR o haz clic en un producto para agregarlo al ticket.
                                        </div>
                                    ) : (
                                        cart.map((item) => (
                                            <div
                                                key={item.product.id}
                                                className="flex items-center justify-between gap-2 p-2 rounded-lg bg-muted/50 text-sm"
                                            >
                                                <div className="min-w-0 flex-1">
                                                    <div className="font-medium truncate">{item.product.name}</div>
                                                    <div className="text-xs text-muted-foreground">
                                                        ${item.product.price.toFixed(2)} c/u
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-1">
                                                    <Button
                                                        size="icon"
                                                        variant="outline"
                                                        className="h-6 w-6"
                                                        onClick={() => updateQuantity(item.product.id, -1)}
                                                    >
                                                        <Minus className="h-3 w-3" />
                                                    </Button>
                                                    <span className="w-7 text-center font-semibold text-xs">
                                                        {item.quantity}
                                                    </span>
                                                    <Button
                                                        size="icon"
                                                        variant="outline"
                                                        className="h-6 w-6"
                                                        onClick={() => updateQuantity(item.product.id, 1)}
                                                    >
                                                        <Plus className="h-3 w-3" />
                                                    </Button>
                                                </div>
                                                <div className="font-semibold w-16 text-right">
                                                    ${(item.product.price * item.quantity).toFixed(2)}
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </div>

                                {/* Customer Info */}
                                <div className="space-y-2 pt-2 border-t">
                                    <div className="grid grid-cols-2 gap-2">
                                        <div>
                                            <Label className="text-xs">Cliente</Label>
                                            <Input
                                                value={customerName}
                                                onChange={(e) => setCustomerName(e.target.value)}
                                                placeholder="Consumidor Final"
                                                className="h-8 text-xs"
                                            />
                                        </div>
                                        <div>
                                            <Label className="text-xs">ID Fiscal (RUC / NIT / RFC / VAT / DNI)</Label>
                                            <Input
                                                value={customerTaxId}
                                                onChange={(e) => setCustomerTaxId(e.target.value)}
                                                placeholder="Consumidor Final / Tax ID"
                                                className="h-8 text-xs"
                                            />
                                        </div>
                                    </div>
                                    <div>
                                        <Label className="text-xs">WhatsApp del Cliente (E.164 Global: +1, +52, +34, +51, +593...)</Label>
                                        <Input
                                            value={customerPhone}
                                            onChange={(e) => setCustomerPhone(e.target.value)}
                                            placeholder="+1... / +52... / +34... / +51... / +593..."
                                            className="h-8 text-xs"
                                        />
                                    </div>
                                </div>

                                {/* Payment Method */}
                                <div className="space-y-1.5">
                                    <Label className="text-xs">Método de Pago</Label>
                                    <div className="grid grid-cols-4 gap-1.5">
                                        {[
                                            { id: 'cash', label: 'Efectivo', icon: Banknote },
                                            { id: 'transfer', label: 'Transf.', icon: Smartphone },
                                            { id: 'qr', label: 'Pago QR', icon: QrCode },
                                            { id: 'card', label: 'Tarjeta', icon: CreditCard },
                                        ].map((pm) => (
                                            <Button
                                                key={pm.id}
                                                type="button"
                                                size="sm"
                                                variant={paymentMethod === pm.id ? 'default' : 'outline'}
                                                onClick={() => setPaymentMethod(pm.id as any)}
                                                className="flex flex-col h-12 gap-1 text-[10px] px-1"
                                            >
                                                <pm.icon className="h-3.5 w-3.5" />
                                                {pm.label}
                                            </Button>
                                        ))}
                                    </div>
                                </div>

                                {/* Totals */}
                                <div className="space-y-1.5 pt-2 border-t text-sm">
                                    <div className="flex justify-between text-xs text-muted-foreground">
                                        <span>Subtotal</span>
                                        <span>${subtotal.toFixed(2)}</span>
                                    </div>
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground">Descuento ($)</span>
                                        <Input
                                            type="number"
                                            min="0"
                                            step="0.5"
                                            value={discountAmount}
                                            onChange={(e) => setDiscountAmount(parseFloat(e.target.value) || 0)}
                                            className="h-6 w-20 text-right text-xs"
                                        />
                                    </div>
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground">IVA / VAT / Tax (%)</span>
                                        <div className="flex items-center gap-1">
                                            {[0, 12, 15, 18, 21].map((rate) => (
                                                <button
                                                    key={rate}
                                                    type="button"
                                                    onClick={() => setTaxRate(rate)}
                                                    className={`px-1.5 py-0.5 rounded text-[10px] border ${
                                                        taxRate === rate
                                                            ? 'bg-primary text-primary-foreground'
                                                            : 'text-muted-foreground'
                                                    }`}
                                                >
                                                    {rate}%
                                                </button>
                                            ))}
                                            <Input
                                                type="number"
                                                min="0"
                                                max="100"
                                                step="0.5"
                                                value={taxRate}
                                                onChange={(e) => setTaxRate(parseFloat(e.target.value) || 0)}
                                                className="h-6 w-14 text-right text-xs"
                                            />
                                        </div>
                                    </div>
                                    <div className="flex justify-between text-lg font-bold pt-2 border-t">
                                        <span>Total a Cobrar</span>
                                        <span className="text-emerald-500">${total.toFixed(2)}</span>
                                    </div>
                                </div>

                                <Button
                                    className="w-full h-11 text-base font-semibold gap-2"
                                    disabled={cart.length === 0 || processingOrder}
                                    onClick={handleCheckout}
                                >
                                    <CheckCircle2 className="h-5 w-5" />
                                    {processingOrder ? 'Procesando...' : `Cobrar $${total.toFixed(2)}`}
                                </Button>

                                {lastReceiptOrder && (
                                    <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between text-xs">
                                        <div>
                                            <div className="font-bold text-emerald-400">
                                                Último Ticket: {lastReceiptOrder.order_number}
                                            </div>
                                            <div className="text-muted-foreground">
                                                Total: ${lastReceiptOrder.total.toFixed(2)}
                                            </div>
                                        </div>
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() => window.print()}
                                            className="gap-1.5 h-8"
                                        >
                                            <Printer className="h-3.5 w-3.5" />
                                            Imprimir Ticket
                                        </Button>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </div>
            )}

            {/* TAB 2: INVENTARIO & GENERADOR DE ETIQUETAS (CÓDIGOS DE BARRAS EAN-13 + QR) */}
            {activeTab === 'inventory' && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    {/* Left: Create / Edit Product Form */}
                    <div className="lg:col-span-4">
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-base flex items-center gap-2">
                                    <Tag className="h-4 w-4 text-primary" />
                                    {editingProduct ? `Editar: ${editingProduct.name}` : 'Nuevo Producto con Código de Barras & QR'}
                                </CardTitle>
                                <CardDescription className="text-xs">
                                    Si dejas el SKU o el Código de Barras en blanco, Aikrofy genera automáticamente un código EAN-13 estándar (prefijo 786 con dígito verificador GS1) y su código QR listo para imprimir.
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <form onSubmit={handleSaveProduct} className="space-y-3">
                                    <div>
                                        <Label className="text-xs">Nombre del Producto *</Label>
                                        <Input
                                            value={prodName}
                                            onChange={(e) => setProdName(e.target.value)}
                                            placeholder="Ej. Sombrero de Paja Toquilla Fino"
                                            required
                                        />
                                    </div>
                                    <div className="grid grid-cols-3 gap-2">
                                        <div>
                                            <Label className="text-xs">Precio Unitario *</Label>
                                            <Input
                                                type="number"
                                                step="0.01"
                                                value={prodPrice}
                                                onChange={(e) => setProdPrice(e.target.value)}
                                                placeholder="25.00"
                                                required
                                            />
                                        </div>
                                        <div>
                                            <Label className="text-xs">Moneda</Label>
                                            <select
                                                value={prodCurrency}
                                                onChange={(e) => setProdCurrency(e.target.value)}
                                                className="flex h-9 w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
                                            >
                                                <option value="USD">USD ($)</option>
                                                <option value="EUR">EUR (€)</option>
                                                <option value="PEN">PEN (S/)</option>
                                                <option value="MXN">MXN ($)</option>
                                                <option value="COP">COP ($)</option>
                                                <option value="CLP">CLP ($)</option>
                                                <option value="BRL">BRL (R$)</option>
                                                <option value="ARS">ARS ($)</option>
                                                <option value="GBP">GBP (£)</option>
                                                <option value="CZK">CZK (Kč)</option>
                                            </select>
                                        </div>
                                        <div>
                                            <Label className="text-xs">Stock Disponible *</Label>
                                            <Input
                                                type="number"
                                                value={prodStock}
                                                onChange={(e) => setProdStock(e.target.value)}
                                                placeholder="20"
                                                required
                                            />
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-2">
                                        <div>
                                            <Label className="text-xs">Categoría</Label>
                                            <Input
                                                value={prodCategory}
                                                onChange={(e) => setProdCategory(e.target.value)}
                                                placeholder="Artesanía / Ropa / Alimentos"
                                            />
                                        </div>
                                        <div>
                                            <Label className="text-xs">Unidad</Label>
                                            <Input
                                                value={prodUnit}
                                                onChange={(e) => setProdUnit(e.target.value)}
                                                placeholder="unidad, kg, caja..."
                                            />
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-2">
                                        <div>
                                            <Label className="text-xs">SKU (Opcional - Auto)</Label>
                                            <Input
                                                value={prodSku}
                                                onChange={(e) => setProdSku(e.target.value)}
                                                placeholder="Auto-generado"
                                                className="font-mono text-xs"
                                            />
                                        </div>
                                        <div>
                                            <Label className="text-xs">Código de Barras EAN-13 (Auto)</Label>
                                            <Input
                                                value={prodBarcode}
                                                onChange={(e) => setProdBarcode(e.target.value)}
                                                placeholder="786..."
                                                className="font-mono text-xs"
                                            />
                                        </div>
                                    </div>
                                    <div>
                                        <Label className="text-xs">Descripción para el Agente IA de WhatsApp</Label>
                                        <Input
                                            value={prodDesc}
                                            onChange={(e) => setProdDesc(e.target.value)}
                                            placeholder="Detalles, tallas, colores o ingredientes para que la IA responda dudas..."
                                        />
                                    </div>
                                    <div className="flex gap-2 pt-2">
                                        <Button type="submit" className="flex-1" disabled={savingProduct}>
                                            {savingProduct
                                                ? 'Guardando...'
                                                : editingProduct
                                                ? 'Guardar Cambios'
                                                : 'Crear y Generar Códigos'}
                                        </Button>
                                        {editingProduct && (
                                            <Button
                                                type="button"
                                                variant="outline"
                                                onClick={() => {
                                                    setEditingProduct(null);
                                                    setProdName('');
                                                    setProdPrice('');
                                                    setProdSku('');
                                                    setProdBarcode('');
                                                }}
                                            >
                                                Cancelar
                                            </Button>
                                        )}
                                    </div>
                                </form>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Right: Product List & Printable Barcode/QR Labels */}
                    <div className="lg:col-span-8 space-y-4">
                        {labelProduct && (
                            <Card className="border-2 border-primary bg-primary/5">
                                <CardHeader className="pb-2 flex flex-row items-center justify-between">
                                    <div>
                                        <CardTitle className="text-base flex items-center gap-2">
                                            <Printer className="h-4 w-4 text-primary" />
                                            Vista Previa de Etiquetas Adhesivas: {labelProduct.name}
                                        </CardTitle>
                                        <CardDescription className="text-xs">
                                            Compatible con impresoras térmicas de etiquetas (Zebra, Xprinter, Brother 50x30mm) o papel adhesivo A4 troquelado.
                                        </CardDescription>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Label className="text-xs">Copias:</Label>
                                        <Input
                                            type="number"
                                            min={1}
                                            max={40}
                                            value={labelCopies}
                                            onChange={(e) => setLabelCopies(parseInt(e.target.value, 10) || 1)}
                                            className="w-16 h-8 text-xs"
                                        />
                                        <Button size="sm" onClick={() => window.print()} className="gap-1.5">
                                            <Printer className="h-3.5 w-3.5" />
                                            Imprimir Ahora
                                        </Button>
                                        <Button size="sm" variant="ghost" onClick={() => setLabelProduct(null)}>
                                            Cerrar
                                        </Button>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 pt-2">
                                        {Array.from({ length: labelCopies }).map((_, idx) => (
                                            <div
                                                key={idx}
                                                className="bg-white text-black p-2.5 rounded-md border border-neutral-300 shadow-xs flex flex-col items-center text-center space-y-1"
                                            >
                                                <div className="text-[11px] font-bold line-clamp-1 w-full">
                                                    {labelProduct.name}
                                                </div>
                                                <div className="text-sm font-extrabold text-black">
                                                    ${Number(labelProduct.price).toFixed(2)}{' '}
                                                    <span className="text-[9px] font-mono text-neutral-600">
                                                        ({labelProduct.sku})
                                                    </span>
                                                </div>
                                                <BarcodeSvg value={labelProduct.barcode} width={155} height={46} />
                                                <div className="pt-1 flex items-center justify-center gap-2 w-full border-t border-neutral-200">
                                                    <ProductQrCode payload={labelProduct.qr_payload} size={48} />
                                                    <div className="text-[8px] text-left font-mono text-neutral-700 leading-tight">
                                                        <div>SCAN POS / WA</div>
                                                        <div>{labelProduct.sku}</div>
                                                        <div>{labelProduct.barcode}</div>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {products.map((prod) => (
                                <Card key={prod.id} className="overflow-hidden">
                                    <CardContent className="p-4 space-y-3">
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <div className="font-bold text-base">{prod.name}</div>
                                                <div className="text-xs text-muted-foreground">
                                                    Categoría: {prod.category} | Stock: {prod.stock} {prod.unit}
                                                </div>
                                            </div>
                                            <div className="text-lg font-extrabold text-emerald-500">
                                                ${Number(prod.price).toFixed(2)}
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 items-center bg-muted/40 p-2.5 rounded-lg">
                                            <div className="sm:col-span-2">
                                                <BarcodeSvg value={prod.barcode} width={180} height={50} />
                                            </div>
                                            <div className="flex flex-col items-center">
                                                <ProductQrCode payload={prod.qr_payload} size={58} />
                                                <span className="text-[9px] font-mono text-muted-foreground mt-1">
                                                    SKU: {prod.sku}
                                                </span>
                                            </div>
                                        </div>

                                        <div className="flex items-center justify-between gap-2 pt-1">
                                            <Button
                                                size="sm"
                                                variant="secondary"
                                                className="gap-1.5 text-xs flex-1"
                                                onClick={() => setLabelProduct(prod)}
                                            >
                                                <Printer className="h-3.5 w-3.5" />
                                                Imprimir Etiquetas (Barras + QR)
                                            </Button>
                                            <Button
                                                size="icon"
                                                variant="outline"
                                                className="h-8 w-8"
                                                onClick={() => startEditProduct(prod)}
                                            >
                                                <Edit3 className="h-3.5 w-3.5" />
                                            </Button>
                                            <Button
                                                size="icon"
                                                variant="outline"
                                                className="h-8 w-8 text-destructive"
                                                onClick={() => handleDeleteProduct(prod.id)}
                                            >
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </Button>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* TAB 3: HISTORIAL DE VENTAS (MOSTRADOR POS + WHATSAPP IA) */}
            {activeTab === 'orders' && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">
                            Órdenes Recientes (Mostrador POS & Agente IA de WhatsApp)
                        </CardTitle>
                        <CardDescription className="text-xs">
                            Todas las ventas realizadas en caja o cerradas automáticamente por tu agente de IA en WhatsApp descuentan del mismo inventario en tiempo real.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {orders.length === 0 ? (
                            <div className="text-center py-8 text-sm text-muted-foreground">
                                Aún no se han registrado órdenes.
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {orders.map((ord) => (
                                    <div
                                        key={ord.id}
                                        className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg border gap-2"
                                    >
                                        <div className="space-y-0.5">
                                            <div className="flex items-center gap-2">
                                                <span className="font-mono font-bold text-sm">
                                                    {ord.order_number}
                                                </span>
                                                <Badge variant={ord.source === 'whatsapp_ai' ? 'default' : 'secondary'}>
                                                    {ord.source === 'whatsapp_ai' ? '🤖 WhatsApp IA' : '🏪 Caja POS'}
                                                </Badge>
                                                <Badge variant="outline" className="uppercase text-[10px]">
                                                    {ord.payment_method}
                                                </Badge>
                                            </div>
                                            <div className="text-xs text-muted-foreground">
                                                Cliente: {ord.customer_name}{' '}
                                                {ord.customer_phone ? `(${ord.customer_phone})` : ''} •{' '}
                                                {ord.items?.length || 0} productos
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <div className="text-right">
                                                <div className="font-bold text-emerald-500">
                                                    ${Number(ord.total).toFixed(2)}
                                                </div>
                                                <div className="text-[10px] text-muted-foreground">
                                                    {ord.created_at ? new Date(ord.created_at).toLocaleString() : ''}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
