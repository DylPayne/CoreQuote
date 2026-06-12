from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status

from corequote_api.authorization import require_permission
from corequote_api.libraries import LibraryConflict, LibraryNotFound, LibraryStore, LibraryValidationError
from corequote_api.schemas import (
    AuthUserResponse,
    BoardTypeRequest,
    BoardTypeResponse,
    ExtraCategoryRequest,
    ExtraCategoryResponse,
    ExtraRequest,
    ExtraResponse,
    HandleRequest,
    HandleResponse,
    HingeRequest,
    HingeResponse,
    GeneratePriceListFromSupplierCostsRequest,
    GeneratePriceListFromSupplierCostsResponse,
    ItemSupplierRequest,
    ItemSupplierResponse,
    LibraryImportPreviewRequest,
    LibraryImportPreviewResponse,
    PriceListItemRequest,
    PriceListItemResponse,
    PriceListRequest,
    PriceListResponse,
    PricingSettingsRequest,
    PricingSettingsResponse,
    LibrarySetupChecklistResponse,
    SlideRequest,
    SlideResponse,
    SupplierItemCostRequest,
    SupplierItemCostResponse,
    SupplierDiscountRequest,
    SupplierDiscountResponse,
    SupplierRequest,
    SupplierResponse,
)


router = APIRouter(prefix="/libraries", tags=["libraries"])


def get_library_store() -> LibraryStore:
    return LibraryStore()


CatalogReader = Annotated[AuthUserResponse, Depends(require_permission("catalog:read"))]
CatalogWriter = Annotated[AuthUserResponse, Depends(require_permission("catalog:write"))]
PricingReader = Annotated[AuthUserResponse, Depends(require_permission("pricing:read"))]
PricingWriter = Annotated[AuthUserResponse, Depends(require_permission("pricing:update"))]
StoreDep = Annotated[LibraryStore, Depends(get_library_store)]


@router.get("/setup-checklist", response_model=LibrarySetupChecklistResponse, summary="Get library setup checklist")
def get_setup_checklist(current_user: PricingReader, store: StoreDep) -> LibrarySetupChecklistResponse:
    return LibrarySetupChecklistResponse.model_validate(store.get_setup_checklist(current_user.company_id))


@router.post(
    "/imports/preview",
    response_model=LibraryImportPreviewResponse,
    summary="Preview a library import without saving changes",
)
def preview_library_import(
    payload: LibraryImportPreviewRequest,
    current_user: PricingWriter,
    store: StoreDep,
) -> LibraryImportPreviewResponse:
    try:
        preview = store.preview_library_import(current_user.company_id, _payload(payload))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return LibraryImportPreviewResponse.model_validate(preview)


@router.get("/boards", response_model=list[BoardTypeResponse], summary="List board types")
def list_boards(current_user: CatalogReader, store: StoreDep) -> list[BoardTypeResponse]:
    return [BoardTypeResponse.model_validate(row) for row in store.list_boards(current_user.company_id)]


@router.post("/boards", response_model=BoardTypeResponse, status_code=status.HTTP_201_CREATED, summary="Create a board type")
def create_board(payload: BoardTypeRequest, current_user: CatalogWriter, store: StoreDep) -> BoardTypeResponse:
    return _create_response(BoardTypeResponse, store.create_board, current_user.company_id, payload)


@router.get("/boards/{item_id}", response_model=BoardTypeResponse, summary="Get a board type")
def get_board(item_id: str, current_user: CatalogReader, store: StoreDep) -> BoardTypeResponse:
    return _get_response(BoardTypeResponse, store.get_board, current_user.company_id, item_id)


@router.patch("/boards/{item_id}", response_model=BoardTypeResponse, summary="Update a board type")
def update_board(item_id: str, payload: BoardTypeRequest, current_user: CatalogWriter, store: StoreDep) -> BoardTypeResponse:
    return _update_response(BoardTypeResponse, store.update_board, current_user.company_id, item_id, payload)


@router.delete("/boards/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a board type")
def delete_board(item_id: str, current_user: CatalogWriter, store: StoreDep) -> Response:
    return _delete_response(store.delete_board, current_user.company_id, item_id)


@router.get("/slides", response_model=list[SlideResponse], summary="List slides")
def list_slides(current_user: CatalogReader, store: StoreDep) -> list[SlideResponse]:
    return [SlideResponse.model_validate(row) for row in store.list_slides(current_user.company_id)]


@router.post("/slides", response_model=SlideResponse, status_code=status.HTTP_201_CREATED, summary="Create a slide")
def create_slide(payload: SlideRequest, current_user: CatalogWriter, store: StoreDep) -> SlideResponse:
    return _create_response(SlideResponse, store.create_slide, current_user.company_id, payload)


@router.get("/slides/{item_id}", response_model=SlideResponse, summary="Get a slide")
def get_slide(item_id: str, current_user: CatalogReader, store: StoreDep) -> SlideResponse:
    return _get_response(SlideResponse, store.get_slide, current_user.company_id, item_id)


@router.patch("/slides/{item_id}", response_model=SlideResponse, summary="Update a slide")
def update_slide(item_id: str, payload: SlideRequest, current_user: CatalogWriter, store: StoreDep) -> SlideResponse:
    return _update_response(SlideResponse, store.update_slide, current_user.company_id, item_id, payload)


@router.delete("/slides/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a slide")
def delete_slide(item_id: str, current_user: CatalogWriter, store: StoreDep) -> Response:
    return _delete_response(store.delete_slide, current_user.company_id, item_id)


@router.get("/hinges", response_model=list[HingeResponse], summary="List hinges")
def list_hinges(current_user: CatalogReader, store: StoreDep) -> list[HingeResponse]:
    return [HingeResponse.model_validate(row) for row in store.list_hinges(current_user.company_id)]


@router.post("/hinges", response_model=HingeResponse, status_code=status.HTTP_201_CREATED, summary="Create a hinge")
def create_hinge(payload: HingeRequest, current_user: CatalogWriter, store: StoreDep) -> HingeResponse:
    return _create_response(HingeResponse, store.create_hinge, current_user.company_id, payload)


@router.get("/hinges/{item_id}", response_model=HingeResponse, summary="Get a hinge")
def get_hinge(item_id: str, current_user: CatalogReader, store: StoreDep) -> HingeResponse:
    return _get_response(HingeResponse, store.get_hinge, current_user.company_id, item_id)


@router.patch("/hinges/{item_id}", response_model=HingeResponse, summary="Update a hinge")
def update_hinge(item_id: str, payload: HingeRequest, current_user: CatalogWriter, store: StoreDep) -> HingeResponse:
    return _update_response(HingeResponse, store.update_hinge, current_user.company_id, item_id, payload)


@router.delete("/hinges/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a hinge")
def delete_hinge(item_id: str, current_user: CatalogWriter, store: StoreDep) -> Response:
    return _delete_response(store.delete_hinge, current_user.company_id, item_id)


@router.get("/suppliers", response_model=list[SupplierResponse], summary="List suppliers")
def list_suppliers(current_user: CatalogReader, store: StoreDep) -> list[SupplierResponse]:
    return [SupplierResponse.model_validate(row) for row in store.list_suppliers(current_user.company_id)]


@router.post("/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED, summary="Create a supplier")
def create_supplier(payload: SupplierRequest, current_user: CatalogWriter, store: StoreDep) -> SupplierResponse:
    return _create_response(SupplierResponse, store.create_supplier, current_user.company_id, payload)


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse, summary="Get a supplier")
def get_supplier(supplier_id: str, current_user: CatalogReader, store: StoreDep) -> SupplierResponse:
    return _get_response(SupplierResponse, store.get_supplier, current_user.company_id, supplier_id)


@router.patch("/suppliers/{supplier_id}", response_model=SupplierResponse, summary="Update a supplier")
def update_supplier(
    supplier_id: str,
    payload: SupplierRequest,
    current_user: CatalogWriter,
    store: StoreDep,
) -> SupplierResponse:
    return _update_response(SupplierResponse, store.update_supplier, current_user.company_id, supplier_id, payload)


@router.post(
    "/suppliers/{supplier_id}/discount",
    response_model=SupplierDiscountResponse,
    summary="Apply a supplier discount",
)
def apply_supplier_discount(
    supplier_id: str,
    payload: SupplierDiscountRequest,
    current_user: PricingWriter,
    store: StoreDep,
) -> SupplierDiscountResponse:
    return _create_response(
        SupplierDiscountResponse,
        store.apply_supplier_discount,
        current_user.company_id,
        supplier_id,
        payload,
    )


@router.delete("/suppliers/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a supplier")
def delete_supplier(supplier_id: str, current_user: CatalogWriter, store: StoreDep) -> Response:
    return _delete_response(store.delete_supplier, current_user.company_id, supplier_id)


@router.get("/handles", response_model=list[HandleResponse], summary="List handles")
def list_handles(current_user: CatalogReader, store: StoreDep) -> list[HandleResponse]:
    return [HandleResponse.model_validate(row) for row in store.list_handles(current_user.company_id)]


@router.post("/handles", response_model=HandleResponse, status_code=status.HTTP_201_CREATED, summary="Create a handle")
def create_handle(payload: HandleRequest, current_user: CatalogWriter, store: StoreDep) -> HandleResponse:
    return _create_response(HandleResponse, store.create_handle, current_user.company_id, payload)


@router.get("/handles/{item_id}", response_model=HandleResponse, summary="Get a handle")
def get_handle(item_id: str, current_user: CatalogReader, store: StoreDep) -> HandleResponse:
    return _get_response(HandleResponse, store.get_handle, current_user.company_id, item_id)


@router.patch("/handles/{item_id}", response_model=HandleResponse, summary="Update a handle")
def update_handle(item_id: str, payload: HandleRequest, current_user: CatalogWriter, store: StoreDep) -> HandleResponse:
    return _update_response(HandleResponse, store.update_handle, current_user.company_id, item_id, payload)


@router.delete("/handles/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a handle")
def delete_handle(item_id: str, current_user: CatalogWriter, store: StoreDep) -> Response:
    return _delete_response(store.delete_handle, current_user.company_id, item_id)


@router.get("/extra-categories", response_model=list[ExtraCategoryResponse], summary="List extra categories")
def list_extra_categories(current_user: CatalogReader, store: StoreDep) -> list[ExtraCategoryResponse]:
    return [ExtraCategoryResponse.model_validate(row) for row in store.list_extra_categories(current_user.company_id)]


@router.post(
    "/extra-categories",
    response_model=ExtraCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an extra category",
)
def create_extra_category(
    payload: ExtraCategoryRequest,
    current_user: CatalogWriter,
    store: StoreDep,
) -> ExtraCategoryResponse:
    return _create_response(ExtraCategoryResponse, store.create_extra_category, current_user.company_id, payload)


@router.get("/extra-categories/{item_id}", response_model=ExtraCategoryResponse, summary="Get an extra category")
def get_extra_category(item_id: str, current_user: CatalogReader, store: StoreDep) -> ExtraCategoryResponse:
    return _get_response(ExtraCategoryResponse, store.get_extra_category, current_user.company_id, item_id)


@router.patch("/extra-categories/{item_id}", response_model=ExtraCategoryResponse, summary="Update an extra category")
def update_extra_category(
    item_id: str,
    payload: ExtraCategoryRequest,
    current_user: CatalogWriter,
    store: StoreDep,
) -> ExtraCategoryResponse:
    return _update_response(ExtraCategoryResponse, store.update_extra_category, current_user.company_id, item_id, payload)


@router.delete("/extra-categories/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an extra category")
def delete_extra_category(item_id: str, current_user: CatalogWriter, store: StoreDep) -> Response:
    return _delete_response(store.delete_extra_category, current_user.company_id, item_id)


@router.get("/extras", response_model=list[ExtraResponse], summary="List extras")
def list_extras(current_user: CatalogReader, store: StoreDep) -> list[ExtraResponse]:
    return [ExtraResponse.model_validate(row) for row in store.list_extras(current_user.company_id)]


@router.post("/extras", response_model=ExtraResponse, status_code=status.HTTP_201_CREATED, summary="Create an extra")
def create_extra(payload: ExtraRequest, current_user: CatalogWriter, store: StoreDep) -> ExtraResponse:
    return _create_response(ExtraResponse, store.create_extra, current_user.company_id, payload)


@router.get("/extras/{item_id}", response_model=ExtraResponse, summary="Get an extra")
def get_extra(item_id: str, current_user: CatalogReader, store: StoreDep) -> ExtraResponse:
    return _get_response(ExtraResponse, store.get_extra, current_user.company_id, item_id)


@router.patch("/extras/{item_id}", response_model=ExtraResponse, summary="Update an extra")
def update_extra(item_id: str, payload: ExtraRequest, current_user: CatalogWriter, store: StoreDep) -> ExtraResponse:
    return _update_response(ExtraResponse, store.update_extra, current_user.company_id, item_id, payload)


@router.delete("/extras/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an extra")
def delete_extra(item_id: str, current_user: CatalogWriter, store: StoreDep) -> Response:
    return _delete_response(store.delete_extra, current_user.company_id, item_id)


@router.get("/item-suppliers", response_model=list[ItemSupplierResponse], summary="List item supplier links")
def list_item_suppliers(
    current_user: PricingReader,
    store: StoreDep,
    item_type: str | None = None,
    item_ref_id: str | None = None,
) -> list[ItemSupplierResponse]:
    return [
        ItemSupplierResponse.model_validate(row)
        for row in store.list_item_suppliers(current_user.company_id, item_type=item_type, item_ref_id=item_ref_id)
    ]


@router.post(
    "/item-suppliers",
    response_model=ItemSupplierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an item supplier link",
)
def create_item_supplier(
    payload: ItemSupplierRequest,
    current_user: PricingWriter,
    store: StoreDep,
) -> ItemSupplierResponse:
    return _create_response(ItemSupplierResponse, store.create_item_supplier, current_user.company_id, payload)


@router.get("/item-suppliers/{item_supplier_id}", response_model=ItemSupplierResponse, summary="Get an item supplier link")
def get_item_supplier(
    item_supplier_id: str,
    current_user: PricingReader,
    store: StoreDep,
) -> ItemSupplierResponse:
    return _get_response(ItemSupplierResponse, store.get_item_supplier, current_user.company_id, item_supplier_id)


@router.patch("/item-suppliers/{item_supplier_id}", response_model=ItemSupplierResponse, summary="Update an item supplier link")
def update_item_supplier(
    item_supplier_id: str,
    payload: ItemSupplierRequest,
    current_user: PricingWriter,
    store: StoreDep,
) -> ItemSupplierResponse:
    return _update_response(ItemSupplierResponse, store.update_item_supplier, current_user.company_id, item_supplier_id, payload)


@router.delete("/item-suppliers/{item_supplier_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an item supplier link")
def delete_item_supplier(
    item_supplier_id: str,
    current_user: PricingWriter,
    store: StoreDep,
) -> Response:
    return _delete_response(store.delete_item_supplier, current_user.company_id, item_supplier_id)


@router.get(
    "/item-suppliers/{item_supplier_id}/costs",
    response_model=list[SupplierItemCostResponse],
    summary="List supplier item costs",
)
def list_supplier_item_costs(
    item_supplier_id: str,
    current_user: PricingReader,
    store: StoreDep,
    include_history: bool = False,
) -> list[SupplierItemCostResponse]:
    return [
        SupplierItemCostResponse.model_validate(row)
        for row in store.list_supplier_item_costs(
            current_user.company_id,
            item_supplier_id,
            include_history=include_history,
        )
    ]


@router.post(
    "/item-suppliers/{item_supplier_id}/costs",
    response_model=SupplierItemCostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a supplier item cost",
)
def create_supplier_item_cost(
    item_supplier_id: str,
    payload: SupplierItemCostRequest,
    current_user: PricingWriter,
    store: StoreDep,
) -> SupplierItemCostResponse:
    return _create_response(
        SupplierItemCostResponse,
        store.create_supplier_item_cost,
        current_user.company_id,
        item_supplier_id,
        payload,
    )


@router.post(
    "/item-suppliers/{item_supplier_id}/costs/upsert",
    response_model=SupplierItemCostResponse,
    summary="Upsert a supplier item cost",
)
def upsert_supplier_item_cost(
    item_supplier_id: str,
    payload: SupplierItemCostRequest,
    current_user: PricingWriter,
    store: StoreDep,
) -> SupplierItemCostResponse:
    return _create_response(
        SupplierItemCostResponse,
        store.upsert_supplier_item_cost,
        current_user.company_id,
        item_supplier_id,
        payload,
    )


@router.get(
    "/item-suppliers/{item_supplier_id}/costs/{cost_id}",
    response_model=SupplierItemCostResponse,
    summary="Get a supplier item cost",
)
def get_supplier_item_cost(
    item_supplier_id: str,
    cost_id: str,
    current_user: PricingReader,
    store: StoreDep,
) -> SupplierItemCostResponse:
    return _get_response(SupplierItemCostResponse, store.get_supplier_item_cost, current_user.company_id, item_supplier_id, cost_id)


@router.get("/pricing-settings", response_model=PricingSettingsResponse, summary="Get pricing settings")
def get_pricing_settings(current_user: PricingReader, store: StoreDep) -> PricingSettingsResponse:
    return _get_response(PricingSettingsResponse, store.get_pricing_settings, current_user.company_id)


@router.patch("/pricing-settings", response_model=PricingSettingsResponse, summary="Update pricing settings")
def update_pricing_settings(
    payload: PricingSettingsRequest,
    current_user: PricingWriter,
    store: StoreDep,
) -> PricingSettingsResponse:
    return _update_response(PricingSettingsResponse, store.update_pricing_settings, current_user.company_id, payload)


@router.get("/price-lists", response_model=list[PriceListResponse], summary="List price lists")
def list_price_lists(current_user: PricingReader, store: StoreDep) -> list[PriceListResponse]:
    return [PriceListResponse.model_validate(row) for row in store.list_price_lists(current_user.company_id)]


@router.post(
    "/price-lists",
    response_model=PriceListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a price list",
)
def create_price_list(payload: PriceListRequest, current_user: PricingWriter, store: StoreDep) -> PriceListResponse:
    return _create_response(PriceListResponse, store.create_price_list, current_user.company_id, payload)


@router.get("/price-lists/active", response_model=PriceListResponse, summary="Get the active price list")
def get_active_price_list(current_user: PricingReader, store: StoreDep) -> PriceListResponse:
    return _get_response(PriceListResponse, store.get_active_price_list, current_user.company_id)


@router.get("/price-lists/{price_list_id}", response_model=PriceListResponse, summary="Get a price list")
def get_price_list(price_list_id: str, current_user: PricingReader, store: StoreDep) -> PriceListResponse:
    return _get_response(PriceListResponse, store.get_price_list, current_user.company_id, price_list_id)


@router.patch("/price-lists/{price_list_id}", response_model=PriceListResponse, summary="Update a price list")
def update_price_list(
    price_list_id: str,
    payload: PriceListRequest,
    current_user: PricingWriter,
    store: StoreDep,
) -> PriceListResponse:
    return _update_response(PriceListResponse, store.update_price_list, current_user.company_id, price_list_id, payload)


@router.delete("/price-lists/{price_list_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a price list")
def delete_price_list(price_list_id: str, current_user: PricingWriter, store: StoreDep) -> Response:
    return _delete_response(store.delete_price_list, current_user.company_id, price_list_id)


@router.post(
    "/price-lists/{price_list_id}/generate-from-supplier-costs",
    response_model=GeneratePriceListFromSupplierCostsResponse,
    summary="Generate price list items from supplier costs",
)
def generate_price_list_from_supplier_costs(
    price_list_id: str,
    payload: GeneratePriceListFromSupplierCostsRequest,
    current_user: PricingWriter,
    store: StoreDep,
) -> GeneratePriceListFromSupplierCostsResponse:
    return _create_response(
        GeneratePriceListFromSupplierCostsResponse,
        store.generate_price_list_from_supplier_costs,
        current_user.company_id,
        price_list_id,
        payload,
    )


@router.get(
    "/price-lists/{price_list_id}/items",
    response_model=list[PriceListItemResponse],
    summary="List price list items",
)
def list_price_list_items(
    price_list_id: str,
    current_user: PricingReader,
    store: StoreDep,
    include_history: bool = False,
) -> list[PriceListItemResponse]:
    return [
        PriceListItemResponse.model_validate(row)
        for row in store.list_price_list_items(current_user.company_id, price_list_id, include_history=include_history)
    ]


@router.post(
    "/price-lists/{price_list_id}/items",
    response_model=PriceListItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a price list item",
)
def create_price_list_item(
    price_list_id: str,
    payload: PriceListItemRequest,
    current_user: PricingWriter,
    store: StoreDep,
) -> PriceListItemResponse:
    return _create_response(
        PriceListItemResponse,
        store.create_price_list_item,
        current_user.company_id,
        price_list_id,
        payload,
    )


@router.post(
    "/price-lists/{price_list_id}/items/upsert",
    response_model=PriceListItemResponse,
    summary="Upsert a price list item",
)
def upsert_price_list_item(
    price_list_id: str,
    payload: PriceListItemRequest,
    current_user: PricingWriter,
    store: StoreDep,
) -> PriceListItemResponse:
    return _create_response(
        PriceListItemResponse,
        store.upsert_price_list_item,
        current_user.company_id,
        price_list_id,
        payload,
    )


@router.get(
    "/price-lists/{price_list_id}/items/{item_id}",
    response_model=PriceListItemResponse,
    summary="Get a price list item",
)
def get_price_list_item(
    price_list_id: str,
    item_id: str,
    current_user: PricingReader,
    store: StoreDep,
) -> PriceListItemResponse:
    return _get_response(PriceListItemResponse, store.get_price_list_item, current_user.company_id, price_list_id, item_id)


@router.patch(
    "/price-lists/{price_list_id}/items/{item_id}",
    response_model=PriceListItemResponse,
    summary="Update a price list item",
)
def update_price_list_item(
    price_list_id: str,
    item_id: str,
    payload: PriceListItemRequest,
    current_user: PricingWriter,
    store: StoreDep,
) -> PriceListItemResponse:
    return _update_response(
        PriceListItemResponse,
        store.update_price_list_item,
        current_user.company_id,
        price_list_id,
        item_id,
        payload,
    )


@router.delete(
    "/price-lists/{price_list_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a price list item",
)
def delete_price_list_item(
    price_list_id: str,
    item_id: str,
    current_user: PricingWriter,
    store: StoreDep,
) -> Response:
    return _delete_response(store.delete_price_list_item, current_user.company_id, price_list_id, item_id)


def _payload(payload: Any) -> dict[str, Any]:
    return payload.model_dump()


def _create_response(response_model, callback, *args):
    try:
        row = callback(*args[:-1], _payload(args[-1]))
    except LibraryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except LibraryConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except LibraryNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library row not found") from exc
    return response_model.model_validate(row)


def _get_response(response_model, callback, *args):
    try:
        row = callback(*args)
    except LibraryNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library row not found") from exc
    return response_model.model_validate(row)


def _update_response(response_model, callback, *args):
    try:
        row = callback(*args[:-1], _payload(args[-1]))
    except LibraryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except LibraryConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except LibraryNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library row not found") from exc
    return response_model.model_validate(row)


def _delete_response(callback, *args) -> Response:
    try:
        callback(*args)
    except LibraryConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except LibraryNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library row not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
