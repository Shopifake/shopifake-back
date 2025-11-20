# Service API Endpoints

Summary of the REST endpoints implemented for the catalog, inventory, pricing, and orders services.

---

## Catalog Service (`services/shopifake-catalog`)

### Product API (`ProductController`)
- **DTOs**
  - `CreateProductRequest`: `siteId` (UUID), `name` (String ≤255), `description` (String), `images` (List<String> URLs), `categoryIds` (List<UUID>), `sku` (alphanumeric, ≤20), `status` (default `DRAFT`), `scheduledPublishAt` (LocalDateTime), `filters` (List<ProductFilterAssignmentRequest` avec `filterId` + payload valeur).
  - `ProductFilterAssignmentRequest`: `filterId` (UUID) + champs optionnels (`textValue`, `numericValue`, `minValue`, `maxValue`, `startAt`, `endAt`) applicables selon le type du filtre.
  - `ProductResponse`: product metadata, `List<CategoryResponse>`, status info, timestamps, filters (each filter entry echoes `filterId`, key, type, unit, and the per-product values).
  - `UpdateProductRequest`: optional `name`, `description`, `images`, `categoryIds`, `sku`, `filters`.
  - `UpdateProductStatusRequest`: `status`, optional `scheduledPublishAt`.
- **Filters & validation**: Each `ProductFilterRequest` must reference an existing filter that belongs to
  the same site *and* to one of the product's categories. The controller validates the site/category
  alignment, checks that the stored type matches the payload, and persists only the per-product values
  (text/numeric/range/date). Arbitrary keys remain disallowed.

- `POST /api/catalog/products`  
  Create a product (see `CreateProductRequest`).

- `GET /api/catalog/products/{productId}`  
  Retrieve a single product with metadata, filters, and associated categories.

- `GET /api/catalog/products?siteId={siteId}&status={status}`  
  List products. `siteId` and `status` (`DRAFT`, `PUBLISHED`, `SCHEDULED`) are optional query params.

- `GET /api/catalog/products/public?siteId={siteId}`  
  Public storefront view exposing only published products. Optional `siteId`.

- `PATCH /api/catalog/products/{productId}`  
  Partial update of product metadata (name, description, images, `categoryIds`, SKU, filters).

- `PATCH /api/catalog/products/{productId}/status`  
  Update lifecycle status (`DRAFT`, `PUBLISHED`, `SCHEDULED`) and optional `scheduledPublishAt`.

- `DELETE /api/catalog/products/{productId}`  
  Remove a product permanently.

### Filter API (`FilterController`)
- **DTOs**
  - `CreateFilterRequest`: `siteId` (UUID), `categoryId` (UUID), `key` (≤100), `type`
    (`CATEGORICAL`, `QUANTITATIVE`, `DATETIME`), optional `displayName`, and per-type metadata
    (categorical ⇒ `values` list, quantitative ⇒ `unit` plus optional `minValue` / `maxValue`).
  - `FilterResponse`: `id`, `siteId`, `categoryId`, `categoryName`, `key`, `type`, `displayName`, `unit`,
    `values`, `minValue`, `maxValue`, `createdAt`.

- `POST /api/catalog/filters`  
  Create a reusable filter bound to a specific category. Keys must be unique per `(categoryId, key)` pair.

- `GET /api/catalog/filters?siteId={siteId}`  
  List filters. `siteId` is optional; omit to fetch every filter in the catalog service.

- `DELETE /api/catalog/filters/{filterId}`  
  Delete a filter (fails if any product still references it).

### Category API (`CategoryController`)
- **DTOs**
  - `CreateCategoryRequest`: `siteId` (UUID), `name` (String ≤255).
  - `CategoryResponse`: `id`, `siteId`, `name`, `createdAt`.

- `POST /api/catalog/products/categories`  
  Create a category (see `CreateCategoryRequest`).

- `GET /api/catalog/products/categories?siteId={siteId}`  
  List categories. Optional `siteId` filter; omit to list all.

- `DELETE /api/catalog/products/categories/{categoryId}`  
  Delete a category (fails if still linked to products).

---

## Inventory Service (`services/shopifake-inventory`)

### Inventory API (`InventoryController`)
- **DTOs**
  - `CreateInventoryRequest`: `productId`, `initialQuantity`.
  - `AdjustInventoryRequest`: `quantityDelta`, `reason`.
  - `InventoryResponse`: `id`, `productId`, `availableQuantity`, `status`, `replenishmentAt`, timestamps.

- `POST /api/inventory`  
  Initialize stock for a product (`productId`, `initialQuantity`).

- `GET /api/inventory/{productId}`  
  Retrieve inventory snapshot for a product (quantity, status, timestamps).

- `GET /api/inventory?status={status}`  
  List inventory rows, optionally filtered by `status` (`IN_STOCK`, `OUT_OF_STOCK`, `BACKORDERED`).

- `PATCH /api/inventory/{productId}/adjust`  
  Apply a positive/negative `quantityDelta` with a reason. Auto-updates status.

- `DELETE /api/inventory/{productId}`  
  Remove inventory tracking for a product.

---

## Pricing Service (`services/shopifake-pricing`)

### Price API (`PriceController`)
- **DTOs**
  - `CreatePriceRequest`: `productId`, `amount`, `currency`, optional `effectiveFrom`/`effectiveTo`.
  - `UpdatePriceRequest`: optional `amount`, `currency`, `effectiveFrom`, `effectiveTo`.
  - `PriceResponse`: `id`, `productId`, `amount`, `currency`, `status`, effective window, timestamps.

- `POST /api/prices`  
  Create a new price entry (`productId`, `amount`, `currency`, optional effective window).

- `PATCH /api/prices/{priceId}`  
  Update an existing price (amount/currency/effective dates). Automatically handles active/expired state.

- `GET /api/prices/product/{productId}`  
  List full price history for a product, ordered by `effectiveFrom`.

- `GET /api/prices/product/{productId}/active`  
  Fetch the current active price. Returns 404 if none exists.

---

## Orders Service (`services/shopifake-orders`)

### Cart API (`CartController`)
- **DTOs**
  - `AddToCartRequest`: `productId` (UUID), `quantity` (Integer ≥1).
  - `UpdateCartItemRequest`: `quantity` (Integer ≥1).
  - `CartItemResponse`: `id`, `productId`, `quantity`. Contains only product identifiers and quantity. Frontend should fetch product details (name, price, etc.) from catalog and pricing services.
  - `CartResponse`: `id`, `userId`, `sessionId`, `siteId`, `items` (List<CartItemResponse>), timestamps. Contains only cart items with product identifiers. Frontend should fetch product details and calculate totals from catalog and pricing services.

- **Authentication & Session Management**
  - For logged-in users: provide `X-User-Id` header (UUID)
  - For guest users: optionally provide `X-Session-Id` header. If not provided, a sessionId will be auto-generated and returned in the response. Frontend should store this sessionId (e.g., in localStorage) and include it in subsequent requests.
  - All endpoints require `siteId` as a query parameter.

- `GET /api/orders/carts?siteId={siteId}`  
  Retrieves the cart for a user or session. Returns cart with all items. If sessionId was auto-generated, it will be included in the response.

- `POST /api/orders/carts/items?siteId={siteId}`  
  Adds a product to the cart with specified quantity. If the product already exists in the cart, the quantity will be increased. For guest users without sessionId, one will be auto-generated.

- `PATCH /api/orders/carts/items/{itemId}?siteId={siteId}`  
  Updates the quantity of a cart item. The quantity must be at least 1.

- `DELETE /api/orders/carts/items/{itemId}?siteId={siteId}`  
  Removes an item from the cart.

- `DELETE /api/orders/carts?siteId={siteId}`  
  Removes all items from the cart (clears the cart).

---

These endpoints are fully exercised via Bruno collections in `.bruno/` and covered by service/controller unit tests in each module.

