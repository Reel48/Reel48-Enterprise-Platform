'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
} from 'react';
import type { ReactNode } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CartItem {
  productId: string;
  productName: string;
  sku: string;
  unitPrice: number;
  quantity: number;
  size: string | null;
  decoration: string | null;
  imageUrl: string | null;
}

interface CartState {
  catalogId: string | null;
  catalogName: string | null;
  items: CartItem[];
}

type CartAction =
  | { type: 'ADD_ITEM'; catalogId: string; catalogName: string; item: CartItem }
  | { type: 'UPDATE_QUANTITY'; index: number; quantity: number }
  | { type: 'REMOVE_ITEM'; index: number }
  | { type: 'CLEAR' }
  | { type: 'HYDRATE'; state: CartState };

interface CartContextValue {
  state: CartState;
  addItem: (catalogId: string, catalogName: string, item: CartItem) => boolean;
  updateQuantity: (index: number, quantity: number) => void;
  removeItem: (index: number) => void;
  clearCart: () => void;
  itemCount: number;
  catalogMismatch: (catalogId: string) => boolean;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STORAGE_KEY = 'reel48_cart';

const INITIAL_STATE: CartState = {
  catalogId: null,
  catalogName: null,
  items: [],
};

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case 'ADD_ITEM': {
      // If different catalog, clear first
      if (state.catalogId && state.catalogId !== action.catalogId) {
        return {
          catalogId: action.catalogId,
          catalogName: action.catalogName,
          items: [action.item],
        };
      }

      // Check if same product+size+decoration already in cart
      const existingIndex = state.items.findIndex(
        (i) =>
          i.productId === action.item.productId &&
          i.size === action.item.size &&
          i.decoration === action.item.decoration,
      );

      if (existingIndex >= 0) {
        const updated = [...state.items];
        updated[existingIndex] = {
          ...updated[existingIndex],
          quantity: updated[existingIndex].quantity + action.item.quantity,
        };
        return {
          catalogId: action.catalogId,
          catalogName: action.catalogName,
          items: updated,
        };
      }

      return {
        catalogId: action.catalogId,
        catalogName: action.catalogName,
        items: [...state.items, action.item],
      };
    }

    case 'UPDATE_QUANTITY': {
      if (action.quantity < 1) return state;
      const updated = [...state.items];
      updated[action.index] = { ...updated[action.index], quantity: action.quantity };
      return { ...state, items: updated };
    }

    case 'REMOVE_ITEM': {
      const items = state.items.filter((_, i) => i !== action.index);
      if (items.length === 0) return INITIAL_STATE;
      return { ...state, items };
    }

    case 'CLEAR':
      return INITIAL_STATE;

    case 'HYDRATE':
      return action.state;

    default:
      return state;
  }
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const CartContext = createContext<CartContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function CartProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(cartReducer, INITIAL_STATE);

  // Hydrate from localStorage on mount (client-only)
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as CartState;
        if (parsed.items && parsed.items.length > 0) {
          dispatch({ type: 'HYDRATE', state: parsed });
        }
      }
    } catch {
      // Corrupted data — ignore
    }
  }, []);

  // Persist to localStorage on state change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // Storage full or unavailable — ignore
    }
  }, [state]);

  const catalogMismatch = useCallback(
    (catalogId: string) =>
      state.catalogId !== null && state.catalogId !== catalogId && state.items.length > 0,
    [state.catalogId, state.items.length],
  );

  const addItem = useCallback(
    (catalogId: string, catalogName: string, item: CartItem): boolean => {
      dispatch({ type: 'ADD_ITEM', catalogId, catalogName, item });
      return true;
    },
    [],
  );

  const updateQuantity = useCallback((index: number, quantity: number) => {
    dispatch({ type: 'UPDATE_QUANTITY', index, quantity });
  }, []);

  const removeItem = useCallback((index: number) => {
    dispatch({ type: 'REMOVE_ITEM', index });
  }, []);

  const clearCart = useCallback(() => {
    dispatch({ type: 'CLEAR' });
  }, []);

  const itemCount = useMemo(
    () => state.items.reduce((sum, i) => sum + i.quantity, 0),
    [state.items],
  );

  const value = useMemo<CartContextValue>(
    () => ({
      state,
      addItem,
      updateQuantity,
      removeItem,
      clearCart,
      itemCount,
      catalogMismatch,
    }),
    [state, addItem, updateQuantity, removeItem, clearCart, itemCount, catalogMismatch],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return ctx;
}

export function useCartCount(): number {
  return useCart().itemCount;
}
