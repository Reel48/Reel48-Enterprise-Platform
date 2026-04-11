'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Breadcrumb,
  BreadcrumbItem,
  Button,
  InlineNotification,
  NumberInput,
  TextArea,
  TextInput,
  Tile,
} from '@carbon/react';
import { ShoppingCart, TrashCan } from '@carbon/react/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { useCart } from '@/lib/cart/CartContext';
import type { OrderWithItems } from '@/types/orders';
import type { Profile } from '@/types/profiles';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(price);
}

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useProfile() {
  return useQuery({
    queryKey: ['profile-me'],
    queryFn: async () => {
      const res = await api.get<Profile>('/api/v1/profiles/me');
      return res.data;
    },
  });
}

function useCreateOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      const res = await api.post<OrderWithItems>('/api/v1/orders/', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CheckoutPage() {
  const router = useRouter();
  const cart = useCart();
  const { data: profile } = useProfile();
  const createOrder = useCreateOrder();

  // Shipping address form state
  const [addressLine1, setAddressLine1] = useState('');
  const [addressLine2, setAddressLine2] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [zip, setZip] = useState('');
  const [country, setCountry] = useState('');
  const [notes, setNotes] = useState('');
  const [profileLoaded, setProfileLoaded] = useState(false);

  // Pre-fill from profile when it loads (only once)
  useEffect(() => {
    if (profile && !profileLoaded) {
      setAddressLine1(profile.deliveryAddressLine1 ?? '');
      setAddressLine2(profile.deliveryAddressLine2 ?? '');
      setCity(profile.deliveryCity ?? '');
      setState(profile.deliveryState ?? '');
      setZip(profile.deliveryZip ?? '');
      setCountry(profile.deliveryCountry ?? '');
      setProfileLoaded(true);
    }
  }, [profile, profileLoaded]);

  const resetToProfile = () => {
    if (!profile) return;
    setAddressLine1(profile.deliveryAddressLine1 ?? '');
    setAddressLine2(profile.deliveryAddressLine2 ?? '');
    setCity(profile.deliveryCity ?? '');
    setState(profile.deliveryState ?? '');
    setZip(profile.deliveryZip ?? '');
    setCountry(profile.deliveryCountry ?? '');
  };

  const subtotal = cart.state.items.reduce(
    (sum, item) => sum + item.unitPrice * item.quantity,
    0,
  );

  const handlePlaceOrder = () => {
    if (!cart.state.catalogId || cart.state.items.length === 0) return;

    const payload: Record<string, unknown> = {
      catalogId: cart.state.catalogId,
      lineItems: cart.state.items.map((item) => ({
        productId: item.productId,
        quantity: item.quantity,
        ...(item.size ? { size: item.size } : {}),
        ...(item.decoration ? { decoration: item.decoration } : {}),
      })),
    };

    if (notes.trim()) {
      payload.notes = notes.trim();
    }

    if (addressLine1.trim()) {
      payload.shippingAddressLine1 = addressLine1.trim();
      if (addressLine2.trim()) payload.shippingAddressLine2 = addressLine2.trim();
      if (city.trim()) payload.shippingCity = city.trim();
      if (state.trim()) payload.shippingState = state.trim();
      if (zip.trim()) payload.shippingZip = zip.trim();
      if (country.trim()) payload.shippingCountry = country.trim();
    }

    createOrder.mutate(payload, {
      onSuccess: (order) => {
        cart.clearCart();
        if (order) {
          router.push(`/orders/${order.id}`);
        } else {
          router.push('/orders');
        }
      },
    });
  };

  // Empty cart state
  if (cart.state.items.length === 0) {
    return (
      <div className="flex flex-col gap-6">
        <Breadcrumb>
          <BreadcrumbItem>
            <Link href="/orders">Orders</Link>
          </BreadcrumbItem>
          <BreadcrumbItem isCurrentPage>New Order</BreadcrumbItem>
        </Breadcrumb>

        <Tile className="py-12 text-center">
          <ShoppingCart size={48} className="mx-auto mb-4 text-text-secondary" />
          <p className="text-lg font-medium text-text-primary">
            Your cart is empty
          </p>
          <p className="text-sm text-text-secondary mt-1 mb-4">
            Browse catalogs to add items to your cart
          </p>
          <Button kind="primary" size="sm" href="/catalog">
            Browse Catalogs
          </Button>
        </Tile>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb>
        <BreadcrumbItem>
          <Link href="/orders">Orders</Link>
        </BreadcrumbItem>
        <BreadcrumbItem isCurrentPage>New Order</BreadcrumbItem>
      </Breadcrumb>

      <h1 className="text-2xl font-semibold text-text-primary">Checkout</h1>

      {createOrder.isError && (
        <InlineNotification
          kind="error"
          title="Order failed"
          subtitle={
            createOrder.error instanceof Error
              ? createOrder.error.message
              : 'Something went wrong. Please try again.'
          }
          hideCloseButton
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cart items — left 2 columns */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <Tile>
            <h2 className="text-base font-semibold text-text-primary mb-1">
              Cart — {cart.state.catalogName}
            </h2>
            <p className="text-xs text-text-secondary mb-4">
              {cart.state.items.length} item{cart.state.items.length !== 1 ? 's' : ''}
            </p>

            <div className="flex flex-col divide-y divide-border-subtle-01">
              {cart.state.items.map((item, index) => (
                <div key={`${item.productId}-${item.size}-${item.decoration}`} className="flex items-start gap-4 py-4 first:pt-0 last:pb-0">
                  {/* Product image placeholder */}
                  <div className="w-16 h-16 bg-layer-02 rounded flex-shrink-0 flex items-center justify-center">
                    {item.imageUrl ? (
                      <img
                        src={item.imageUrl}
                        alt={item.productName}
                        className="w-full h-full object-cover rounded"
                      />
                    ) : (
                      <ShoppingCart size={20} className="text-text-secondary" />
                    )}
                  </div>

                  {/* Details */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-text-primary truncate">
                      {item.productName}
                    </p>
                    <p className="text-xs text-text-secondary">
                      SKU: {item.sku}
                      {item.size ? ` | Size: ${item.size}` : ''}
                      {item.decoration ? ` | ${item.decoration}` : ''}
                    </p>
                    <p className="text-sm text-interactive mt-1">
                      {formatPrice(item.unitPrice)} each
                    </p>
                  </div>

                  {/* Quantity */}
                  <div className="w-28 flex-shrink-0">
                    <NumberInput
                      id={`qty-${index}`}
                      label=""
                      hideLabel
                      min={1}
                      max={100}
                      value={item.quantity}
                      onChange={(_e: unknown, { value }: { value: number | string }) => {
                        const num = typeof value === 'string' ? parseInt(value, 10) : value;
                        if (!isNaN(num) && num >= 1) cart.updateQuantity(index, num);
                      }}
                      size="sm"
                    />
                  </div>

                  {/* Line total + remove */}
                  <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    <span className="text-sm font-semibold text-text-primary">
                      {formatPrice(item.unitPrice * item.quantity)}
                    </span>
                    <button
                      onClick={() => cart.removeItem(index)}
                      className="text-support-error hover:text-support-error/80 p-1"
                      aria-label={`Remove ${item.productName}`}
                    >
                      <TrashCan size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </Tile>

          {/* Shipping address */}
          <Tile>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-text-primary">
                Shipping Address
              </h2>
              {profile && (
                <Button kind="ghost" size="sm" onClick={resetToProfile}>
                  Use profile address
                </Button>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <TextInput
                  id="address-line1"
                  labelText="Address Line 1"
                  value={addressLine1}
                  onChange={(e) => setAddressLine1(e.target.value)}
                />
              </div>
              <div className="sm:col-span-2">
                <TextInput
                  id="address-line2"
                  labelText="Address Line 2"
                  value={addressLine2}
                  onChange={(e) => setAddressLine2(e.target.value)}
                />
              </div>
              <TextInput
                id="city"
                labelText="City"
                value={city}
                onChange={(e) => setCity(e.target.value)}
              />
              <TextInput
                id="state"
                labelText="State"
                value={state}
                onChange={(e) => setState(e.target.value)}
              />
              <TextInput
                id="zip"
                labelText="ZIP Code"
                value={zip}
                onChange={(e) => setZip(e.target.value)}
              />
              <TextInput
                id="country"
                labelText="Country"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
              />
            </div>
          </Tile>

          {/* Notes */}
          <Tile>
            <h2 className="text-base font-semibold text-text-primary mb-4">
              Order Notes
            </h2>
            <TextArea
              id="notes"
              labelText="Notes (optional)"
              placeholder="Any special instructions for this order..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
            />
          </Tile>
        </div>

        {/* Order summary — right column */}
        <div>
          <Tile className="sticky top-16">
            <h2 className="text-base font-semibold text-text-primary mb-4">
              Order Summary
            </h2>

            <div className="flex flex-col gap-2 mb-4">
              {cart.state.items.map((item) => (
                <div
                  key={`${item.productId}-${item.size}-${item.decoration}`}
                  className="flex justify-between text-sm"
                >
                  <span className="text-text-secondary truncate mr-2">
                    {item.productName} x{item.quantity}
                  </span>
                  <span className="text-text-primary font-medium flex-shrink-0">
                    {formatPrice(item.unitPrice * item.quantity)}
                  </span>
                </div>
              ))}
            </div>

            <div className="border-t border-border-subtle-01 pt-3 mb-4">
              <div className="flex justify-between text-base font-semibold">
                <span className="text-text-primary">Subtotal</span>
                <span className="text-text-primary">{formatPrice(subtotal)}</span>
              </div>
              <p className="text-xs text-text-secondary mt-1">
                Final amount determined at order processing
              </p>
            </div>

            <Button
              kind="primary"
              className="w-full"
              onClick={handlePlaceOrder}
              disabled={createOrder.isPending || cart.state.items.length === 0}
            >
              {createOrder.isPending ? 'Placing Order...' : 'Place Order'}
            </Button>

            <Button
              kind="ghost"
              className="w-full mt-2"
              onClick={cart.clearCart}
              disabled={createOrder.isPending}
            >
              Clear Cart
            </Button>
          </Tile>
        </div>
      </div>
    </div>
  );
}
